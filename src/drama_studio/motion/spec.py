"""Typed motion plan and camera resolution.

A plan is content, not style: it names the still, its duration, the free-text
motion hint from the storyboard, and (optionally) explicit local-motion regions.
The style preset supplies the mechanical policy. ``resolve_camera`` turns the
free-text hint into an exact camera spec so the render is reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..style_presets import CameraMove, Easing, LocalMotionType, StylePreset

W, H, FPS = 1080, 1920, 24


class Box(BaseModel):
    """Normalized rectangle (0..1) used as an exclusion mask."""

    model_config = ConfigDict(extra="forbid")

    x0: float = Field(ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "Box":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("box must satisfy x1 > x0 and y1 > y0")
        return self


class MaskSpec(BaseModel):
    """Region of the still a local motion may touch.

    There is no segmentation model: regions are authored per shot. A luma range
    is applied to a blurred copy so thin highlights are not dragged along.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["band", "box"] = "band"
    x0: float = Field(default=0.0, ge=0.0, le=1.0)
    x1: float = Field(default=1.0, ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    luma_min: int | None = Field(default=None, ge=0, le=255)
    luma_max: int | None = Field(default=None, ge=0, le=255)
    feather_px: float = Field(default=40.0, ge=0.0, le=200.0)
    exclude_boxes: list[Box] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "MaskSpec":
        if self.y1 <= self.y0 or self.x1 <= self.x0:
            raise ValueError("mask must satisfy y1 > y0 and x1 > x0")
        if (self.luma_min is None) != (self.luma_max is None):
            raise ValueError("luma_min and luma_max must be given together")
        if self.luma_min is not None and self.luma_max is not None:
            if self.luma_max <= self.luma_min:
                raise ValueError("luma_max must be > luma_min")
        return self


RegionRole = Literal[
    "rigid_object",
    "fluid_surface",
    "reflection",
    "vegetation",
    "atmosphere",
    "background",
    "independent_overlay",
]

RegionPermission = Literal["locked", "hard_excluded", "controlled", "allowed"]

# A controlled region may only run the motion types that fit its role. The
# mapping is explicit so a water region cannot silently receive a cloud drift.
ROLE_MOTION_TYPES: dict[str, tuple[str, ...]] = {
    "rigid_object": (),
    "fluid_surface": ("water_ripple",),
    "reflection": ("reflection_distortion",),
    "vegetation": ("leaf_sway", "reed_sway"),
    "atmosphere": ("cloud_drift", "ink_diffusion"),
    "background": ("cloud_drift", "ink_diffusion"),
    "independent_overlay": ("petal_drift", "bird_motion"),
}


def boxes_intersect(a: Box, b: Box) -> bool:
    return not (a.x1 <= b.x0 or b.x1 <= a.x0 or a.y1 <= b.y0 or b.y1 <= a.y0)


def box_area(box: Box) -> float:
    return round((box.x1 - box.x0) * (box.y1 - box.y0), 6)


def box_intersection_area(a: Box, b: Box) -> float:
    width = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    height = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    return round(width * height, 6)


class RegionSpec(BaseModel):
    """An authored semantic region with an explicit motion permission.

    There is no segmentation model: the rectangle is the author's statement of
    where the region is. A region that is ``locked`` or ``hard_excluded`` is
    subtracted from every local-motion layer that touches it; a ``controlled``
    region only accepts the motion types and caps declared here.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    role: RegionRole
    permission: RegionPermission
    box: Box
    feather_px: float = Field(default=25.0, ge=0.0, le=200.0)
    reason: str | None = Field(default=None, max_length=300)
    follows: str | None = Field(
        default=None,
        description="reflection only: id of the rigid_object region it belongs to",
    )
    allow_motion_types: list[LocalMotionType] = Field(default_factory=list)
    max_amplitude_px: float | None = Field(default=None, gt=0.0, le=120.0)
    max_frequency_hz: float | None = Field(default=None, gt=0.0, le=2.0)
    exclude_regions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _permission_is_consistent(self) -> "RegionSpec":
        if self.role == "rigid_object" and self.permission not in ("locked", "hard_excluded"):
            raise ValueError(
                f"{self.id}: rigid_object 必须是 locked 或 hard_excluded，"
                f"不能是 {self.permission}"
            )
        if self.permission in ("locked", "hard_excluded") and self.allow_motion_types:
            raise ValueError(f"{self.id}: locked/hard_excluded 区域不能声明 allow_motion_types")
        if self.role == "reflection" and self.permission in ("controlled", "allowed"):
            if not self.follows:
                raise ValueError(
                    f"{self.id}: reflection 区域必须 follows 一个 rigid_object 区域，"
                    "否则无法保持与主体的空间对应关系"
                )
        if self.follows is not None and self.follows == self.id:
            raise ValueError(f"{self.id}: region 不能 follows 自己")
        if self.role != "reflection" and self.follows is not None:
            raise ValueError(f"{self.id}: 只有 reflection 区域可以 follows")
        if self.id in self.exclude_regions:
            raise ValueError(f"{self.id}: region 不能 exclude 自己")
        if self.permission == "controlled" and not self.allow_motion_types:
            self.allow_motion_types = list(ROLE_MOTION_TYPES[self.role])
            if not self.allow_motion_types:
                raise ValueError(
                    f"{self.id}: {self.role} 没有可用的运动类型，不能声明 controlled"
                )
        return self

    @property
    def allowed_motion_types(self) -> tuple[str, ...]:
        if self.permission in ("locked", "hard_excluded"):
            return ()
        if self.permission == "allowed":
            return tuple(ROLE_MOTION_TYPES[self.role])
        return tuple(self.allow_motion_types)


class LocalMotionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    motion_type: LocalMotionType
    mask: MaskSpec
    amplitude: float | None = Field(default=None, ge=0.0, le=120.0,
                                    description="None -> style local_policy amplitude_px")
    frequency: float | None = Field(default=None, gt=0.0, le=2.0,
                                    description="Hz; None -> 1 / style period_s")
    direction: Literal["ltr", "rtl", "up", "down"] = "ltr"
    easing: Easing = "ease_in_out"
    feather: float = Field(default=30.0, ge=0.0, le=200.0)
    phase: float = Field(default=0.0, ge=0.0, le=1.0)
    asset: str | None = Field(default=None, max_length=300)
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    region_id: str | None = Field(
        default=None,
        description="region this layer animates; None keeps the legacy box-only layer",
    )
    exclude_regions: list[str] = Field(
        default_factory=list,
        description="additional region ids to subtract from this layer's mask",
    )

    @model_validator(mode="after")
    def _asset_required(self) -> "LocalMotionSpec":
        if self.motion_type in ("petal_drift", "bird_motion") and not self.asset:
            raise ValueError(
                f"{self.motion_type} needs an independent RGBA asset; it is never "
                "re-painted from the flat still"
            )
        return self


class TransitionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["crossfade", "ink_dissolve", "ink_reveal", "ink_spread"]
    duration_s: float = Field(ge=0.3, le=3.0)
    feather: float = Field(ge=0.02, le=0.6)
    direction: Literal["ltr", "rtl", "up", "down", "radial"] = "ltr"
    seed: int = Field(default=13, ge=0, le=99999)


class CameraOverride(BaseModel):
    """Optional per-shot camera tightening; unset fields come from the style."""

    model_config = ConfigDict(extra="forbid")

    move: CameraMove | None = None
    scale_start: float | None = Field(default=None, ge=1.0, le=1.25)
    scale_end: float | None = Field(default=None, ge=1.0, le=1.25)
    focus: tuple[float, float] | None = None
    easing: Easing | None = None
    direction: Literal["ltr", "rtl"] | None = None

    @model_validator(mode="after")
    def _focus_range(self) -> "CameraOverride":
        if self.focus is not None:
            for name, value in zip(("focus_x", "focus_y"), self.focus):
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"{name} must be within 0..1")
        return self


class CameraSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move: CameraMove
    requested_move: CameraMove
    fallback_reason: str | None = None
    duration_seconds: float = Field(gt=0.0, le=120.0)
    easing: Easing
    focus: tuple[float, float]
    direction: Literal["ltr", "rtl"] = "ltr"
    scale_start: float = Field(ge=1.0, le=1.25)
    scale_end: float = Field(ge=1.0, le=1.25)
    pan_start_px: float = 0.0
    pan_end_px: float = 0.0
    pan_range_px: float = 0.0
    push_pan_fraction: float = 0.0
    source_size: tuple[int, int]


class ShotSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z0-9_\-]{1,40}$")
    source: str = Field(min_length=1, max_length=400)
    duration_seconds: float = Field(gt=0.0, le=120.0)
    motion: str = Field(default="", max_length=120)
    camera: CameraOverride | None = None
    local_motion: list[LocalMotionSpec] = Field(default_factory=list)
    regions: list[RegionSpec] = Field(default_factory=list)
    transition_in: TransitionSpec | None = None
    handle_seconds: float = Field(default=0.0, ge=0.0, le=6.0)
    static_quality: str | None = Field(default=None, max_length=400)
    text: dict[str, str] = Field(default_factory=dict, description="line_ids / visual_prompt audit copy")

    @model_validator(mode="after")
    def _unique_layers(self) -> "ShotSpec":
        ids = [layer.layer_id for layer in self.local_motion]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.id}: duplicate layer_id")
        return self

    @model_validator(mode="after")
    def _region_contract(self) -> "ShotSpec":
        ids = [region.id for region in self.regions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.id}: duplicate region id")
        by_id = {region.id: region for region in self.regions}
        for region in self.regions:
            for other in region.exclude_regions:
                if other not in by_id:
                    raise ValueError(f"{self.id}/{region.id}: exclude_regions 引用了未知区域 {other}")
            if region.role == "reflection" and region.permission in ("controlled", "allowed"):
                subject = by_id.get(region.follows or "")
                if subject is None or subject.role != "rigid_object":
                    raise ValueError(
                        f"{self.id}/{region.id}: follows 必须是本镜头已声明的 rigid_object 区域"
                    )
        for layer in self.local_motion:
            if layer.region_id is not None and layer.region_id not in by_id:
                raise ValueError(
                    f"{self.id}/{layer.layer_id}: region_id 引用了未知区域 {layer.region_id}"
                )
            for other in layer.exclude_regions:
                if other not in by_id:
                    raise ValueError(
                        f"{self.id}/{layer.layer_id}: exclude_regions 引用了未知区域 {other}"
                    )
            region = by_id.get(layer.region_id) if layer.region_id else None
            if region is not None:
                if region.permission in ("locked", "hard_excluded"):
                    raise ValueError(
                        f"{self.id}/{layer.layer_id}: 区域 {region.id} 是 {region.permission}，"
                        "禁止在其上运行动画"
                    )
                if layer.motion_type not in region.allowed_motion_types:
                    raise ValueError(
                        f"{self.id}/{layer.layer_id}: {layer.motion_type} 不在区域 {region.id} "
                        f"允许的类型 {region.allowed_motion_types} 中"
                    )
                if region.role == "reflection" and layer.motion_type != "reflection_distortion":
                    raise ValueError(
                        f"{self.id}/{layer.layer_id}: reflection 区域只能使用 "
                        "reflection_distortion"
                    )
            if layer.motion_type == "reflection_distortion":
                if region is None or region.role != "reflection":
                    raise ValueError(
                        f"{self.id}/{layer.layer_id}: reflection_distortion 必须绑定 "
                        "一个 reflection 区域"
                    )
            if layer.motion_type == "water_ripple" and region is not None and region.role == "reflection":
                raise ValueError(
                    f"{self.id}/{layer.layer_id}: 水面层不能直接驱动倒影区域"
                )
        return self


class MotionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    style_id: str
    fps: int = Field(default=FPS, ge=12, le=30)
    width: int = Field(default=W, ge=256, le=2160)
    height: int = Field(default=H, ge=256, le=3840)
    shots: list[ShotSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _integrity(self) -> "MotionPlan":
        ids = [shot.id for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate shot id")
        if self.shots[0].transition_in is not None:
            raise ValueError("the first shot cannot have a transition_in")
        if (self.width, self.height) != (W, H):
            raise ValueError(f"motion renders are fixed at {W}x{H}, got {self.width}x{self.height}")
        return self

    @property
    def total_seconds(self) -> float:
        """Sequence length is the sum of planned durations.

        A transition overlaps the previous shot's tail handle; it does not add
        or remove time. That is what keeps the audio timeline unchanged.
        """
        return round(sum(shot.duration_seconds for shot in self.shots), 3)


def load_plan(path: Path) -> MotionPlan:
    return MotionPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))


def scaled_width(width: int, height: int, out_height: int = H) -> int:
    value = width * out_height / height
    return max(2, int(round(value / 2.0)) * 2)


def _ease(easing: Easing, p: str) -> str:
    if easing == "linear":
        return p
    if easing == "ease_in":
        return f"({p})*({p})"
    if easing == "ease_out":
        return f"1-(1-({p}))*(1-({p}))"
    return f"(3*pow({p},2)-2*pow({p},3))"


def progress_expr(easing: Easing, duration: float) -> str:
    """Eased progress over a clip, as an FFmpeg expression in ``t``."""
    return _ease(easing, f"min(1,max(0,t/{duration:.6f}))")


def zoom_progress_expr(easing: Easing) -> str:
    """Eased progress inside zoompan, using its own output-frame counter."""
    return _ease(easing, "on/max(1,duration-1)")


def _classify_motion(text: str) -> CameraMove | None:
    value = (text or "").lower()
    if not value:
        return None
    if any(token in value for token in ("static", "still", "固定", "静止")):
        return "static"
    if "parallax" in value or "视差" in value:
        return "layered_parallax"
    push = any(token in value for token in ("push", "zoom in", "推近", "推镜"))
    pull = any(token in value for token in ("pull", "zoom out", "拉远", "拉镜"))
    pan = any(token in value for token in ("pan", "scroll", "track", "横移", "长卷", "平移", "摇"))
    if push and pan:
        return "push_in_with_pan"
    if push:
        return "slow_push_in"
    if pull:
        return "slow_pull_out"
    if "lateral" in value or "track" in value:
        return "slow_lateral_track"
    if pan:
        return "scroll_pan"
    return None


def _classify_direction(text: str) -> Literal["ltr", "rtl"] | None:
    value = (text or "").lower()
    if any(token in value for token in ("rtl", "right to left", "right-to-left", "从右向左", "右到左")):
        return "rtl"
    if any(token in value for token in ("ltr", "left to right", "left-to-right", "从左向右", "左到右")):
        return "ltr"
    return None


def resolve_camera(
    shot: ShotSpec,
    preset: StylePreset,
    source_size: tuple[int, int],
) -> CameraSpec:
    """Resolve a shot's camera into exact, reproducible parameters.

    Priority: explicit ``shot.camera.move`` > free-text ``motion`` hint > style
    default. A move the style does not allow, or a pan on a still with no
    horizontal room, falls back (to push-in if pan cannot work) and records why.
    """
    policy = preset.motion.camera
    width, height = source_size
    span = max(0, scaled_width(width, height) - W)
    override = shot.camera
    requested: CameraMove | None = None
    if override is not None and override.move is not None:
        requested = override.move
    else:
        requested = _classify_motion(shot.motion)
    if requested is None:
        requested = policy.default

    fallback: str | None = None
    move = requested
    lowered = (shot.motion or "").lower().replace("_", " ")
    for token in preset.motion.forbidden:
        if token.lower().replace("_", " ") in lowered:
            fallback = f"motion 文本包含风格禁止项 {token!r}"
            move = policy.default
            break
    if move not in policy.allowed:
        fallback = f"{move} 不在风格允许列表 {policy.allowed} 中"
        move = policy.default
    if move in ("scroll_pan", "slow_lateral_track") and span <= 0:
        fallback = f"源图 {width}x{height} 无横移空间"
        move = "slow_push_in" if "slow_push_in" in policy.allowed else "static"

    duration = shot.duration_seconds
    focus: tuple[float, float] = policy.focus
    easing: Easing = policy.easing
    direction: Literal["ltr", "rtl"] = _classify_direction(shot.motion) or "ltr"
    scale_start, scale_end = 1.0, 1.0
    pan = 0.0

    if override is not None:
        if override.focus is not None:
            focus = override.focus
        if override.easing is not None:
            easing = override.easing
        if override.direction is not None:
            direction = override.direction

    if move in ("slow_push_in", "push_in_with_pan", "slow_pull_out"):
        rate = policy.push_rate_per_s
        scale = min(policy.push_scale_max, max(policy.push_scale_min, 1.0 + rate * duration))
        if override is not None and override.scale_end is not None:
            scale = override.scale_end
        if move == "slow_pull_out":
            scale_start, scale_end = scale, 1.0
        else:
            scale_start, scale_end = 1.0, scale
        if override is not None and override.scale_start is not None:
            scale_start = override.scale_start
    elif move in ("scroll_pan", "slow_lateral_track"):
        speed = policy.scroll_speed_px_s
        if move == "slow_lateral_track":
            speed *= policy.slow_track_speed_factor
        pan = min(float(span), max(1.0, speed * duration))
        first = round((span - pan) / 2.0)
        if direction == "rtl":
            first = round((span + pan) / 2.0)
        pan_start = max(0.0, min(float(span), float(first)))
        pan_end = max(0.0, min(float(span), float(first + (pan if direction == "ltr" else -pan))))
        return CameraSpec(
            move=move,
            requested_move=requested,
            fallback_reason=fallback,
            duration_seconds=duration,
            easing=easing,
            focus=(float(focus[0]), float(focus[1])),
            direction=direction,
            scale_start=1.0,
            scale_end=1.0,
            pan_start_px=pan_start,
            pan_end_px=pan_end,
            pan_range_px=float(span),
            push_pan_fraction=0.0,
            source_size=(width, height),
        )

    return CameraSpec(
        move=move,
        requested_move=requested,
        fallback_reason=fallback,
        duration_seconds=duration,
        easing=easing,
        focus=(float(focus[0]), float(focus[1])),
        direction=direction,
        scale_start=round(scale_start, 6),
        scale_end=round(scale_end, 6),
        pan_start_px=0.0,
        pan_end_px=0.0,
        pan_range_px=float(span),
        push_pan_fraction=(policy.push_pan_fraction if move == "push_in_with_pan" else 0.0),
        source_size=(width, height),
    )
