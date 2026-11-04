"""Two core visual style presets.

``config/styles.yaml`` is the canonical definition of the product's two core
aesthetics (see ``docs/VISUAL_STYLE_SPEC.md``). Works choose a style by id; the
pipeline never branches on a style name in code.

This module validates the presets and exposes them as plain data. It never
writes to ``projects/workspace.db``: that database contains user-created facts
only, so presets are not auto-seeded. Use ``preset.as_style_entity()`` when a
caller explicitly wants to create a workspace style from a preset.

Only ``visual_language`` and ``positive_prompt`` are consumed by the current
generation path (``script_engine.compose_visual_prompt``). The structured
material/line/detail fields are audit data, and motion/compositing describe the
S2 animation work that is not wired into production yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import find_project_root

# Same rule as cli.py: a piped MSYS/PowerShell stdout defaults to the ANSI code
# page and Chinese preset names become mojibake.
if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Keep in sync with drama_studio.workspace.store.STYLE_FIELDS; a test asserts
# equality so a preset can always be handed to the workspace style API.
STYLE_ENTITY_FIELDS = (
    "name",
    "description",
    "visual_language",
    "color_palette",
    "lighting",
    "camera_language",
    "composition",
    "character_design",
    "environment_design",
    "positive_prompt",
    "negative_prompt",
    "reference_assets",
    "aspect_ratio",
    "applicable_content_types",
    "source_files",
    "preset_id",
)

AbilityStatus = Literal[
    "PASS_VERIFIED",
    "PASS_STATIC",
    "PARTIAL",
    "NOT_RUN",
    "BLOCKED",
    "DEPRECATED",
]
Primitive = Literal[
    "scroll_pan",
    "ink_matte",
    "ink_diffusion",
    "paper_texture",
    "line_reveal",
    "local_motion",
    "parallax_2_5d",
]
PrimaryMotion = Literal[
    "static",
    "scroll_pan",
    "slow_push_in",
    "slow_lateral_track",
    "ink_diffusion",
]
LocalMotion = Literal["clouds", "mist", "water", "birds", "petals", "foliage", "ink_diffusion"]

# Mechanical vocabulary consumed by drama_studio.motion. These are deliberately
# separate from the narrative ``local`` list above: that list says *what* moves,
# these models say *how* it is rendered.
CameraMove = Literal[
    "static",
    "slow_push_in",
    "slow_pull_out",
    "scroll_pan",
    "push_in_with_pan",
    "slow_lateral_track",
    "layered_parallax",
]
Easing = Literal["linear", "ease_in", "ease_out", "ease_in_out"]
LocalMotionType = Literal[
    "water_ripple",
    "leaf_sway",
    "reed_sway",
    "cloud_drift",
    "petal_drift",
    "bird_motion",
    "reflection_distortion",
    "ink_diffusion",
]

CompositionStrategy = Literal[
    "rule_of_thirds",
    "center",
    "symmetry",
    "frame_in_frame",
    "diagonal",
    "negative_space",
    "vertical_depth",
    "monumental_scale",
    "corner_placement",
    "high_distance",
    "deep_distance",
    "level_distance",
    "scattered_perspective",
    "void_solid",
]
SubjectPosition = Literal[
    "center", "left_third", "right_third", "lower_left", "lower_right", "upper_center"
]
ShotSize = Literal["extreme_wide", "wide", "medium", "close", "detail"]
LightingKey = Literal["moon", "sun_low", "sun_high", "overcast", "candle", "none"]
LightingScenario = Literal[
    "moon_diffuse", "morning_side", "sunset_warm", "cloud_gap",
    "backlight", "soft_ambient", "overcast", "mist_scatter",
]
ColorTemperature = Literal["warm", "cool", "neutral", "split"]
ValueRange = Literal["high_key", "middle", "low_key", "full"]

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class MaterialSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["silk", "paper", "raw_paper", "sized_paper"]
    prompt: str = Field(min_length=4, max_length=300)


class LineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: Literal["fine_line", "freehand", "outline"]
    prompt: str = Field(min_length=4, max_length=300)


class DetailSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["high", "moderate"]
    prompt: str = Field(min_length=4, max_length=300)


class WanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    usage: Literal["none", "local_supplement", "limited"]
    note: str = ""


class CameraPolicy(BaseModel):
    """How the camera may move for one style; consumed by ``motion.camera``."""

    model_config = ConfigDict(extra="forbid")

    default: CameraMove
    allowed: list[CameraMove] = Field(min_length=1)
    scroll_speed_px_s: float = Field(ge=4.0, le=80.0)
    slow_track_speed_factor: float = Field(default=0.6, ge=0.1, le=1.0)
    push_rate_per_s: float = Field(default=0.008, gt=0.0, le=0.03)
    push_pan_fraction: float = Field(default=0.02, ge=0.0, le=0.1)
    push_scale_min: float = Field(default=1.03, ge=1.01, le=1.2)
    push_scale_max: float = Field(default=1.06, ge=1.01, le=1.2)
    easing: Easing = "ease_in_out"
    focus: tuple[float, float] = (0.5, 0.5)

    @model_validator(mode="after")
    def _consistent(self) -> "CameraPolicy":
        if self.push_scale_max < self.push_scale_min:
            raise ValueError("push_scale_max must be >= push_scale_min")
        if self.default not in self.allowed:
            raise ValueError(f"default camera {self.default!r} is not in allowed")
        for name, value in zip(("focus_x", "focus_y"), self.focus):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within 0..1")
        return self


class LocalPolicy(BaseModel):
    """Per-style amplitude/period/opacity for one local motion type."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    amplitude_px: float = Field(default=0.0, ge=0.0, le=120.0)
    period_s: float = Field(default=8.0, ge=0.5, le=120.0)
    opacity: float = Field(default=0.0, ge=0.0, le=1.0)
    opacity_min: float = Field(default=0.8, ge=0.0, le=1.0)
    opacity_max: float = Field(default=1.0, ge=0.0, le=1.0)
    feather_px: float = Field(default=30.0, ge=0.0, le=200.0)
    drift: Literal["sine", "one_way"] = "sine"
    # M2 motion model. Defaults are deliberately quiet: long wavelength, low
    # vertical ratio, strong perspective falloff.
    wavelength_px: float = Field(default=280.0, ge=20.0, le=2000.0)
    vertical_ratio: float = Field(default=0.28, ge=0.0, le=1.0)
    perspective_far_scale: float = Field(default=0.14, ge=0.0, le=1.0)
    reflection_ratio: float = Field(default=0.55, ge=0.0, le=1.0)
    reflection_lag_s: float = Field(default=0.18, ge=0.0, le=2.0)
    smear_px: float = Field(default=3.0, ge=0.0, le=20.0)
    sway_exponent: float = Field(default=1.4, ge=0.5, le=4.0)
    top_decay: float = Field(default=0.2, ge=0.0, le=0.8)

    @model_validator(mode="after")
    def _opacity_order(self) -> "LocalPolicy":
        if self.opacity_max < self.opacity_min:
            raise ValueError("opacity_max must be >= opacity_min")
        return self


class TransitionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["crossfade", "ink_dissolve", "ink_reveal", "ink_spread"]
    duration_s: float = Field(ge=0.3, le=3.0)
    max_fraction: float = Field(default=0.35, ge=0.1, le=0.5)
    feather: float = Field(ge=0.02, le=0.6)
    direction: Literal["ltr", "rtl", "up", "down", "radial"] = "ltr"
    seed: int = Field(default=13, ge=0, le=99999)


class MotionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: list[PrimaryMotion] = Field(min_length=1)
    local: list[LocalMotion] = Field(default_factory=list)
    wan: WanSpec
    forbidden: list[str] = Field(default_factory=list)
    camera: CameraPolicy
    local_policy: dict[LocalMotionType, LocalPolicy] = Field(default_factory=dict)
    transition: TransitionPolicy


class TextureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["silk", "paper", "raw_paper", "none"]
    asset: str | None = None
    opacity: float = Field(default=0.0, ge=0.0, le=0.3)
    note: str = ""


class ParallaxSpec(BaseModel):
    """What a style permits for layered 2.5D shots.

    These are policy, not description: the renderer refuses a layered shot that
    violates them, so every field here has a consumer. Values are calibrated on
    the M8 experiments, not invented.
    """

    model_config = ConfigDict(extra="forbid")

    allowed: bool = False
    requires: str = ""
    camera_moves: list[CameraMove] = Field(default_factory=list)
    max_plates: int = Field(default=3, ge=1, le=6)
    depth_alpha_min: float = Field(default=0.45, gt=0.0, le=1.0)
    depth_alpha_max: float = Field(default=0.85, gt=0.0, le=1.0)
    background_margin: float = Field(
        default=0.0, ge=0.0, le=0.25,
        description="fraction of the plate the background window must leave free on each side")

    @model_validator(mode="after")
    def _consistent(self) -> "ParallaxSpec":
        if self.depth_alpha_min >= self.depth_alpha_max:
            raise ValueError("depth_alpha_min must be < depth_alpha_max")
        if self.allowed and not self.camera_moves:
            raise ValueError("允许 2.5D 必须声明 camera_moves（否则没有可用的分层镜头类型）")
        return self


class CompositingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primitives: list[Primitive] = Field(min_length=1)
    texture: TextureSpec
    parallax: ParallaxSpec = Field(default_factory=ParallaxSpec)
    note: str = ""


class AestheticCompositionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_strategies: list[CompositionStrategy] = Field(min_length=1)
    default_subject_position: SubjectPosition
    whitespace_range: tuple[float, float]
    shot_sizes: list[ShotSize] = Field(min_length=1)

    @model_validator(mode="after")
    def _range(self) -> "AestheticCompositionProfile":
        lo, hi = self.whitespace_range
        if not (0.0 <= lo < hi <= 0.9):
            raise ValueError("whitespace_range must satisfy 0 <= lo < hi <= 0.9")
        return self


class AestheticLightingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred: list[LightingScenario] = Field(min_length=1)
    default_key: LightingKey
    default_quality: Literal["soft", "hard", "mixed"] = "soft"
    default_direction: Literal["front", "side_left", "side_right", "back", "top", "diffuse"] = "diffuse"
    default_contrast: Literal["low", "medium", "high"] = "low"
    rim_light: Literal["rare", "allowed", "avoid"] = "rare"


class AestheticColorProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity_group: str = Field(min_length=1, max_length=40)
    dominant_keys: list[str] = Field(min_length=1)
    secondary_keys: list[str] = Field(default_factory=list)
    accent_keys: list[str] = Field(default_factory=list)
    default_temperature: ColorTemperature
    saturation_range: tuple[float, float]
    value_range: ValueRange

    @model_validator(mode="after")
    def _range(self) -> "AestheticColorProfile":
        lo, hi = self.saturation_range
        if not (0.0 <= lo < hi <= 1.0):
            raise ValueError("saturation_range must satisfy 0 <= lo < hi <= 1")
        return self


class AestheticDepthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_layers: int = Field(ge=1, le=3)
    aerial_perspective: bool
    sharpness_falloff: Literal["shallow", "medium", "deep"]


class AestheticMiseProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(min_length=1, max_length=40)
    architecture_positive: str = Field(min_length=2, max_length=200)
    positive_constraints: list[str] = Field(default_factory=list, max_length=8)


class AestheticStorytellingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_rhythm: str = Field(min_length=1, max_length=40)
    emotion_vocabulary: list[str] = Field(min_length=1, max_length=12)


class AestheticProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    composition: AestheticCompositionProfile
    lighting: AestheticLightingProfile
    color: AestheticColorProfile
    depth: AestheticDepthProfile
    mise_en_scene: AestheticMiseProfile
    storytelling: AestheticStorytellingProfile


class StylePreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    name: str = Field(min_length=1, max_length=80)
    name_en: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=400)
    validation_status: AbilityStatus = "NOT_RUN"

    # Shared with the workspace style entity.
    visual_language: str = Field(min_length=4, max_length=600)
    color_palette: dict[str, str]
    lighting: str = Field(min_length=4, max_length=400)
    camera_language: str = Field(min_length=4, max_length=400)
    composition: str = Field(min_length=4, max_length=600)
    character_design: str = Field(min_length=4, max_length=400)
    environment_design: str = Field(min_length=4, max_length=400)
    positive_prompt: str = Field(min_length=4, max_length=1500)
    negative_prompt: str = Field(min_length=4, max_length=1000)
    reference_assets: list[str] = Field(default_factory=list)
    aspect_ratio: str = Field(pattern=r"^[0-9]{1,2}:[0-9]{1,2}$")
    applicable_content_types: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)

    # Config-layer only: not stored in workspace.db.
    material: MaterialSpec
    line: LineSpec
    detail: DetailSpec
    motion: MotionSpec
    compositing: CompositingSpec
    aesthetic_profile: AestheticProfile

    @field_validator("color_palette")
    @classmethod
    def _palette_is_hex(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("color_palette must not be empty")
        for name, color in value.items():
            if not _HEX.match(color):
                raise ValueError(f"color_palette[{name!r}] is not a #RRGGBB value: {color!r}")
        return value

    @model_validator(mode="after")
    def _aesthetic_palette(self) -> "StylePreset":
        palette = set(self.color_palette)
        color = self.aesthetic_profile.color
        keys = color.dominant_keys + color.secondary_keys + color.accent_keys
        missing = sorted(set(keys) - palette)
        if missing:
            raise ValueError(f"{self.id}: aesthetic_profile color keys missing from palette: {missing}")
        return self

    def as_style_entity(self) -> dict[str, object]:
        """Return exactly the fields accepted by ``WorkspaceStore.create_style``."""

        entity = {field: getattr(self, field) for field in STYLE_ENTITY_FIELDS if field != "preset_id"}
        entity["preset_id"] = self.id
        return entity


class StylePresetRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    styles: dict[str, StylePreset] = Field(min_length=1)

    @model_validator(mode="after")
    def _keys_match_ids(self) -> "StylePresetRegistry":
        for key, preset in self.styles.items():
            if key != preset.id:
                raise ValueError(f"styles key {key!r} does not match preset id {preset.id!r}")
        return self

    def get(self, style_id: str) -> StylePreset:
        try:
            return self.styles[style_id]
        except KeyError as exc:
            raise KeyError(f"unknown style preset: {style_id}") from exc

    def ids(self) -> list[str]:
        return list(self.styles)


def load_style_presets(root: Path | None = None) -> StylePresetRegistry:
    root = (root or find_project_root()).resolve()
    path = root / "config" / "styles.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    registry = StylePresetRegistry.model_validate(data)
    for preset in registry.styles.values():
        for rel in preset.reference_assets:
            if not (root / rel).is_file():
                raise ValueError(f"{preset.id}: reference asset does not exist: {rel}")
        for rel in preset.source_files:
            if not (root / rel).is_file():
                raise ValueError(f"{preset.id}: source file does not exist: {rel}")
        texture_asset = preset.compositing.texture.asset
        if texture_asset and not (root / texture_asset).is_file():
            raise ValueError(f"{preset.id}: texture asset does not exist: {texture_asset}")
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List or export the two core style presets")
    parser.add_argument("--json", action="store_true", help="dump the full registry as JSON")
    parser.add_argument("--id", help="preset id to export")
    parser.add_argument("--entity", action="store_true", help="with --id: emit workspace style entity JSON")
    args = parser.parse_args(argv)

    registry = load_style_presets()
    if args.id:
        try:
            preset = registry.get(args.id)
        except KeyError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        payload = preset.as_style_entity() if args.entity else preset.model_dump()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.json:
        print(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2))
        return 0
    for preset in registry.styles.values():
        print(f"{preset.id}\t{preset.name}\t{preset.validation_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
