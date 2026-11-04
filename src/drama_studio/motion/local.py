"""Local micro-motion layers built with Pillow.

Every layer has an explicit, authored region; there is no segmentation model.
The layer generators return stills or short image sequences plus the FFmpeg
overlay expressions, so the final composition stays one deterministic graph.

Implemented types: water_ripple, reflection_distortion, cloud_drift,
leaf_sway, reed_sway, ink_diffusion, and external petal/bird assets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from ..style_presets import LocalPolicy
from .noise import noise_image
from .spec import (
    H,
    W,
    LocalMotionSpec,
    MaskSpec,
    RegionSpec,
    box_area,
    boxes_intersect,
)

HALF = (W // 2, H // 2)


@dataclass
class InputSpec:
    path: str
    sequence: bool


@dataclass
class LayerRender:
    layer_id: str
    motion_type: str
    inputs: list[InputSpec]
    graph: str  # consumes [i:v]...[j:v] and emits [label]
    label: str
    overlay_x: str
    overlay_y: str
    info: dict = field(default_factory=dict)


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _span(y: int, y0: int, y1: int, feather: int) -> float:
    if y < y0 or y > y1:
        return 0.0
    if feather <= 0:
        return 1.0
    return min(1.0, (y - y0) / feather, (y1 - y) / feather)


MIN_MASK_COVERAGE = 0.002


class LayerRefused(ValueError):
    """A local-motion layer refused before rendering, with a machine-readable reason."""

    def __init__(self, layer_id: str, reason: str, details: dict | None = None):
        self.layer_id = layer_id
        self.reason = reason
        self.details = details or {}
        super().__init__(f"{layer_id}: {reason} ({self.details})")


def effective_exclusions(
    layer: LocalMotionSpec,
    regions: list[RegionSpec],
) -> list[RegionSpec]:
    """Regions subtracted from this layer's alpha.

    Hard rules, independent of author input:

    * locked/hard_excluded regions that intersect the layer's mask are removed;
    * reflection regions are removed from every layer that is not the reflection
      layer, so water can never drive the reflection;
    * explicit ``exclude_regions`` on the layer and on its own region are added.

    The layer's own region is never subtracted from itself.
    """
    own = layer.region_id
    by_id = {region.id: region for region in regions}
    mask_box = layer.mask
    chosen: dict[str, RegionSpec] = {}

    def add(region: RegionSpec | None) -> None:
        if region is None or region.id == own:
            return
        chosen[region.id] = region

    for region in regions:
        if region.id == own:
            continue
        if region.permission in ("locked", "hard_excluded"):
            if boxes_intersect(region.box, mask_box):
                add(region)
        elif region.role == "reflection" and layer.motion_type != "reflection_distortion":
            if boxes_intersect(region.box, mask_box):
                add(region)

    for region_id in layer.exclude_regions:
        add(by_id.get(region_id))
    own_region = by_id.get(own) if own else None
    if own_region is not None:
        for region_id in own_region.exclude_regions:
            add(by_id.get(region_id))

    return list(chosen.values())


def _apply_region_exclusions(
    alpha: Image.Image,
    exclusions: list[RegionSpec],
    feather_scale: float,
) -> Image.Image:
    width, height = alpha.size
    for region in exclusions:
        box = (
            int(region.box.x0 * (width - 1)),
            int(region.box.y0 * (height - 1)),
            int(region.box.x1 * (width - 1)),
            int(region.box.y1 * (height - 1)),
        )
        alpha = subtract_box(alpha, box, max(1, int(round(region.feather_px * feather_scale))))
    return alpha


def mask_coverage(alpha: Image.Image) -> float:
    return round(ImageStat.Stat(alpha).mean[0] / 255.0, 5)


def _check_region_caps(
    layer: LocalMotionSpec,
    region: RegionSpec | None,
    amplitude: float,
    frequency: float,
) -> None:
    if box_area(layer.mask) < 0.0005:
        raise LayerRefused(layer.layer_id, "mask_area_too_small",
                           {"box_area": box_area(layer.mask)})
    if region is None:
        return
    if region.permission in ("locked", "hard_excluded"):
        raise LayerRefused(layer.layer_id, "region_locked",
                           {"region": region.id, "permission": region.permission})
    if layer.motion_type not in region.allowed_motion_types:
        raise LayerRefused(layer.layer_id, "motion_not_allowed_for_region",
                           {"region": region.id, "motion_type": layer.motion_type,
                            "allowed": list(region.allowed_motion_types)})
    if region.max_amplitude_px is not None and amplitude > region.max_amplitude_px:
        raise LayerRefused(layer.layer_id, "amplitude_exceeds_region_cap",
                           {"region": region.id, "amplitude": amplitude,
                            "cap": region.max_amplitude_px})
    if region.max_frequency_hz is not None and frequency > region.max_frequency_hz:
        raise LayerRefused(layer.layer_id, "frequency_exceeds_region_cap",
                           {"region": region.id, "frequency": frequency,
                            "cap": region.max_frequency_hz})


def _check_mask_coverage(layer: LocalMotionSpec, coverage: float) -> None:
    if coverage < MIN_MASK_COVERAGE:
        raise LayerRefused(layer.layer_id, "mask_fully_excluded",
                           {"coverage": coverage, "min": MIN_MASK_COVERAGE})


def build_mask(
    gray: Image.Image,
    mask: MaskSpec,
    *,
    feather_scale: float = 1.0,
    extra_edge_px: int = 0,
    exclusions: list[RegionSpec] | None = None,
) -> Image.Image:
    """Soft alpha for one authored region, with optional luma gating.

    ``exclusions`` are semantic regions (locked subjects, independently driven
    reflections) subtracted after the luma gate. They are applied here so every
    layer type inherits the same protection.
    """
    width, height = gray.size
    x0 = int(mask.x0 * (width - 1))
    x1 = int(mask.x1 * (width - 1))
    y0 = int(mask.y0 * (height - 1))
    y1 = int(mask.y1 * (height - 1))
    feather = max(1, int(round(mask.feather_px * feather_scale)))
    extra = int(round(extra_edge_px * feather_scale))
    blurred = gray.filter(ImageFilter.GaussianBlur(4)) if mask.luma_min is not None else gray
    src = blurred.load()
    alpha = Image.new("L", gray.size, 0)
    dst = alpha.load()
    lo = float(mask.luma_min if mask.luma_min is not None else 0)
    hi = float(mask.luma_max if mask.luma_max is not None else 255)
    span = max(1.0, hi - lo)
    for y in range(max(0, y0), min(height - 1, y1) + 1):
        vy = _span(y, y0, y1, feather)
        if vy <= 0:
            continue
        for x in range(max(0, x0), min(width - 1, x1) + 1):
            vx = _span(x, x0, x1, feather)
            if vx <= 0:
                continue
            value = vy * vx
            if mask.luma_min is not None:
                value *= smoothstep((src[x, y] - lo) / span)
            if extra > 0:
                value *= min(1.0, x / extra if extra else 1.0)
                value *= min(1.0, (width - 1 - x) / extra if extra else 1.0)
            if value > 0:
                dst[x, y] = int(round(value * 255))
    for box in mask.exclude_boxes:
        alpha = subtract_box(
            alpha,
            (
                int(box.x0 * (width - 1)),
                int(box.y0 * (height - 1)),
                int(box.x1 * (width - 1)),
                int(box.y1 * (height - 1)),
            ),
            feather,
        )
    if exclusions:
        alpha = _apply_region_exclusions(alpha, exclusions, feather_scale)
    return alpha


def subtract_box(alpha: Image.Image, box: tuple[int, int, int, int], feather: int) -> Image.Image:
    hole = Image.new("L", alpha.size, 255)
    draw = ImageDraw.Draw(hole)
    draw.rectangle(list(box), fill=0)
    hole = hole.filter(ImageFilter.GaussianBlur(max(1, feather)))
    return Image.composite(alpha, Image.new("L", alpha.size, 0), hole)


def edge_feather_x(alpha: Image.Image, px: int) -> Image.Image:
    if px <= 0:
        return alpha
    width, height = alpha.size
    ramp = Image.new("L", (width, 1), 0)
    for x in range(width):
        ramp.putpixel((x, 0), int(round(min(1.0, x / px, (width - 1 - x) / px) * 255)))
    return ImageChops.multiply(alpha, ramp.resize((width, height)))


def _direction_sign(spec: LocalMotionSpec) -> int:
    return -1 if spec.direction == "rtl" else 1


def _save_rgba(image: Image.Image, alpha: Image.Image, path: Path) -> dict:
    rgba = image.convert("RGB").copy()
    rgba.putalpha(alpha)
    rgba.save(path)
    return {"path": str(path), "size": list(rgba.size)}


# ---------------------------------------------------------------------------
# M2: deterministic local-motion algorithms
#
# The previous implementation moved a full-frame texture as one rigid layer.
# These algorithms build a per-pixel displacement field instead, so the motion
# is local, smooth, and can be checked numerically:
#
#   water      -> travelling low-frequency wave, amplitude decays with distance
#   reflection -> vertical only, phase-lagged copy of the water wave, <= water
#   vegetation -> non-linear height weight, exactly zero at the base
#   cloud      -> smooth procedural flow, no rigid translation, no flicker
# ---------------------------------------------------------------------------

def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def perspective_weight(yn: float, bounds: tuple[float, float], far_scale: float) -> float:
    """Displacement weight across the water band.

    Image coordinates grow downward, so the far edge is the smaller y (toward
    the horizon) and the near edge is the larger y. The weight rises
    monotonically from ``far_scale`` at the far edge to 1.0 at the near edge.
    """
    y0, y1 = bounds
    if y1 <= y0:
        return 1.0
    progress = _clamp01((yn - y0) / (y1 - y0))
    return far_scale + (1.0 - far_scale) * smoothstep(progress)


def water_vertical_displacement(
    xn: float,
    yn: float,
    t: float,
    *,
    amplitude: float,
    frequency: float,
    wavelength_px: float,
    vertical_ratio: float,
    far_scale: float,
    bounds: tuple[float, float],
    phase: float = 0.0,
    width: int = W,
) -> float:
    wavelength = max(20.0, wavelength_px) / width
    angle = (
        2.0 * math.pi * frequency * t
        - 2.0 * math.pi * (xn / wavelength + yn / (wavelength * 2.2))
        + 2.0 * math.pi * phase
    )
    weight = perspective_weight(yn, bounds, far_scale)
    return amplitude * vertical_ratio * weight * math.sin(angle + 0.9)


def water_displacement(
    xn: float,
    yn: float,
    t: float,
    *,
    amplitude: float,
    frequency: float,
    wavelength_px: float,
    vertical_ratio: float,
    far_scale: float,
    bounds: tuple[float, float],
    phase: float = 0.0,
    width: int = W,
) -> tuple[float, float]:
    """Low-frequency travelling wave with perspective attenuation.

    Two incommensurate sines avoid a visible repeat without adding high
    frequencies. There is no random pixel noise, so the field is smooth and
    reproducible.
    """
    wavelength = max(20.0, wavelength_px) / width
    angle = (
        2.0 * math.pi * frequency * t
        - 2.0 * math.pi * (xn / wavelength + yn / (wavelength * 2.2))
        + 2.0 * math.pi * phase
    )
    weight = perspective_weight(yn, bounds, far_scale)
    dx = amplitude * weight * (
        0.70 * math.sin(angle) + 0.30 * math.sin(0.61 * angle + 1.7)
    )
    dy = water_vertical_displacement(
        xn, yn, t, amplitude=amplitude, frequency=frequency,
        wavelength_px=wavelength_px, vertical_ratio=vertical_ratio,
        far_scale=far_scale, bounds=bounds, phase=phase, width=width,
    )
    return dx, dy


def reflection_displacement(
    xn: float,
    yn: float,
    t: float,
    *,
    water_amplitude: float,
    water_frequency: float,
    wavelength_px: float,
    vertical_ratio: float,
    far_scale: float,
    bounds: tuple[float, float],
    ratio: float,
    lag_s: float,
    phase: float = 0.0,
    width: int = W,
) -> tuple[float, float]:
    """Vertical-only displacement bound to the water phase and amplitude.

    The reflection never moves horizontally, so it cannot detach from the
    water column. Its instantaneous displacement is clamped to the water's
    current vertical displacement, which guarantees ``|reflection| <= |water|``.
    """
    kwargs = dict(
        amplitude=water_amplitude, frequency=water_frequency,
        wavelength_px=wavelength_px, vertical_ratio=vertical_ratio,
        far_scale=far_scale, bounds=bounds, phase=phase, width=width,
    )
    current = water_vertical_displacement(xn, yn, t, **kwargs)
    lagged = water_vertical_displacement(xn, yn, t - lag_s, **kwargs)
    dy = ratio * lagged
    if abs(dy) > abs(current):
        dy = math.copysign(abs(current), dy if dy != 0.0 else current)
    return 0.0, dy


def sway_weight(
    yn: float,
    y0: float,
    y1: float,
    *,
    exponent: float = 1.4,
    top_decay: float = 0.2,
) -> float:
    """Height weight for a plant: exactly 0 at the base, eased near the tip.

    The base is anchored; the maximum is in the upper-middle; the very tip
    carries a little less displacement, which reads as a natural bend rather
    than a rigid lever.
    """
    if y1 <= y0:
        return 0.0
    progress = _clamp01((y1 - yn) / (y1 - y0))
    if progress <= 0.0:
        return 0.0
    weight = smoothstep(progress) ** exponent
    if progress > 0.75:
        weight *= 1.0 - top_decay * smoothstep((progress - 0.75) / 0.25)
    return weight


def sway_offset(
    yn: float,
    t: float,
    *,
    y0: float,
    y1: float,
    amplitude: float,
    frequency: float,
    exponent: float = 1.4,
    top_decay: float = 0.2,
    phase: float = 0.0,
) -> float:
    weight = sway_weight(yn, y0, y1, exponent=exponent, top_decay=top_decay)
    angle = 2.0 * math.pi * frequency * t + 2.0 * math.pi * phase + yn * 14.4
    return amplitude * weight * math.sin(angle)


def cloud_displacement(
    xn: float,
    yn: float,
    t: float,
    *,
    amplitude: float,
    period_s: float,
    phase: float = 0.0,
) -> tuple[float, float]:
    """Smooth procedural flow for mist and cloud.

    The spatial phase is modulated by two low-frequency sines; there is no
    rigid layer translation and no per-frame random noise, so no hard edge can
    appear and the brightness stays constant.
    """
    flow = math.sin(
        2.0 * math.pi * (1.15 * xn + 0.55 * yn)
        + 0.65 * math.sin(2.0 * math.pi * (0.45 * xn - 0.35 * yn) + 1.1)
    )
    angle = 2.0 * math.pi * (t / max(0.1, period_s)) + 2.0 * math.pi * phase
    dx = amplitude * math.sin(angle + 1.9 * flow)
    dy = 0.32 * amplitude * math.sin(0.83 * angle + 1.4 * flow + 0.9)
    return dx, dy


def mesh_warp(
    image: Image.Image,
    displacement,
    *,
    grid: tuple[int, int] = (20, 28),
) -> Image.Image:
    """Warp an image with a smooth per-pixel displacement field.

    Pillow's MESH transform runs in C; the Python cost is only the grid
    (``grid[0] * grid[1]`` quads), not the pixels.
    """
    width, height = image.size
    cols, rows = grid
    xs = [width * i / cols for i in range(cols + 1)]
    ys = [height * j / rows for j in range(rows + 1)]
    offsets = [[displacement(x / width, y / height) for x in xs] for y in ys]

    def point(x: float, y: float, offset: tuple[float, float]) -> tuple[float, float]:
        return (max(0.0, min(width - 1.0, x + offset[0])),
                max(0.0, min(height - 1.0, y + offset[1])))

    mesh = []
    for j in range(rows):
        for i in range(cols):
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[j], ys[j + 1]
            nw = offsets[j][i]
            sw = offsets[j + 1][i]
            se = offsets[j + 1][i + 1]
            ne = offsets[j][i + 1]
            # Pillow's MESH data is a flat 12-tuple per quad:
            # x0, y0, x1, y1, nw, sw, se, ne (each point as x, y).
            p_nw = point(x0, y0, nw)
            p_sw = point(x0, y1, sw)
            p_se = point(x1, y1, se)
            p_ne = point(x1, y0, ne)
            mesh.append((
                (int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))),
                (p_nw[0], p_nw[1], p_sw[0], p_sw[1],
                 p_se[0], p_se[1], p_ne[0], p_ne[1]),
            ))
    return image.transform((width, height), Image.MESH, mesh, resample=Image.BILINEAR)


def vertical_smear(image: Image.Image, radius: float) -> Image.Image:
    """Cheap vertical motion blur used only by the reflection layer."""
    pixels = max(0, int(round(radius)))
    if pixels <= 0:
        return image
    offsets = [-pixels, -pixels // 2, 0, pixels // 2, pixels]
    weights = [0.12, 0.20, 0.36, 0.20, 0.12]
    accumulator = ImageChops.offset(image, 0, offsets[0])
    total = weights[0]
    for offset, weight in zip(offsets[1:], weights[1:]):
        shifted = ImageChops.offset(image, 0, offset)
        accumulator = Image.blend(accumulator, shifted, weight / (total + weight))
        total += weight
    return accumulator


def _warp_sequence(
    *,
    source: Image.Image,
    alpha: Image.Image,
    displacement,
    out_dir: Path,
    name: str,
    duration: float,
    fps: int,
    grid: tuple[int, int],
) -> tuple[Path, int]:
    frame_dir = out_dir / f"frames_{name}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("f_*.png"):
        old.unlink()
    frames = max(1, int(round(duration * fps)))
    for index in range(frames):
        t = index / fps
        warped = mesh_warp(source, lambda xn, yn: displacement(xn, yn, t), grid=grid)
        rgba = warped.convert("RGB").copy()
        rgba.putalpha(alpha)
        rgba.save(frame_dir / f"f_{index:04d}.png")
    return frame_dir, frames


def _water_ripple(
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    exclusions: list[RegionSpec],
    duration: float,
    fps: int,
) -> LayerRender:
    width, height = base_half.size
    scale = width / W
    alpha = build_mask(gray_half, spec.mask, feather_scale=0.5, exclusions=exclusions)
    alpha = edge_feather_x(alpha, int(max(spec.feather, policy.feather_px) * scale))
    opacity = spec.opacity if spec.opacity is not None else policy.opacity
    alpha = alpha.point(lambda v: max(0, min(255, int(round(v * opacity)))))
    bounds = (spec.mask.y0, spec.mask.y1)
    amplitude = float(spec.amplitude) * scale

    def displacement(xn: float, yn: float, t: float) -> tuple[float, float]:
        return water_displacement(
            xn, yn, t,
            amplitude=amplitude,
            frequency=float(spec.frequency),
            wavelength_px=policy.wavelength_px,
            vertical_ratio=policy.vertical_ratio,
            far_scale=policy.perspective_far_scale,
            bounds=bounds,
            phase=spec.phase,
        )

    frame_dir, frames = _warp_sequence(
        source=base_half, alpha=alpha, displacement=displacement,
        out_dir=out_dir, name=spec.layer_id, duration=duration, fps=fps,
        grid=(20, 28),
    )
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(frame_dir / "f_%04d.png"), sequence=True)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x="0",
        overlay_y="0",
        info={
            "algorithm": "water_ripple_v2",
            "frames_dir": str(frame_dir), "frames": frames, "grid": [20, 28],
            "amplitude_px": spec.amplitude, "frequency_hz": spec.frequency,
            "wavelength_px": policy.wavelength_px,
            "vertical_ratio": policy.vertical_ratio,
            "perspective_far_scale": policy.perspective_far_scale,
            "opacity": opacity, "alpha_coverage": mask_coverage(alpha),
        },
    )


def _reflection_distortion(
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    exclusions: list[RegionSpec],
    duration: float,
    fps: int,
) -> LayerRender:
    width, height = base_half.size
    scale = width / W
    alpha = build_mask(gray_half, spec.mask, feather_scale=0.5, exclusions=exclusions)
    alpha = edge_feather_x(alpha, int(max(spec.feather, policy.feather_px) * scale))
    opacity = spec.opacity if spec.opacity is not None else policy.opacity
    alpha = alpha.point(lambda v: max(0, min(255, int(round(v * opacity)))))
    bounds = (spec.mask.y0, spec.mask.y1)
    amplitude = float(spec.amplitude) * scale
    smeared = vertical_smear(base_half, policy.smear_px * scale)

    def displacement(xn: float, yn: float, t: float) -> tuple[float, float]:
        return reflection_displacement(
            xn, yn, t,
            water_amplitude=amplitude,
            water_frequency=float(spec.frequency),
            wavelength_px=policy.wavelength_px,
            vertical_ratio=policy.vertical_ratio,
            far_scale=policy.perspective_far_scale,
            bounds=bounds,
            ratio=policy.reflection_ratio,
            lag_s=policy.reflection_lag_s,
            phase=spec.phase,
        )

    frame_dir, frames = _warp_sequence(
        source=smeared, alpha=alpha, displacement=displacement,
        out_dir=out_dir, name=spec.layer_id, duration=duration, fps=fps,
        grid=(20, 28),
    )
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(frame_dir / "f_%04d.png"), sequence=True)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x="0",
        overlay_y="0",
        info={
            "algorithm": "reflection_distortion_v2",
            "frames_dir": str(frame_dir), "frames": frames, "grid": [20, 28],
            "amplitude_px": spec.amplitude, "frequency_hz": spec.frequency,
            "wavelength_px": policy.wavelength_px,
            "reflection_ratio": policy.reflection_ratio,
            "reflection_lag_s": policy.reflection_lag_s,
            "smear_px": policy.smear_px,
            "horizontal_displacement": 0.0,
            "opacity": opacity, "alpha_coverage": mask_coverage(alpha),
        },
    )


def _cloud_drift(
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    exclusions: list[RegionSpec],
    duration: float,
    fps: int,
) -> LayerRender:
    width, height = base_half.size
    scale = width / W
    alpha = build_mask(gray_half, spec.mask, feather_scale=0.5, exclusions=exclusions)
    alpha = edge_feather_x(alpha, int(max(spec.feather, policy.feather_px) * (width / W)))
    opacity = spec.opacity if spec.opacity is not None else policy.opacity
    alpha = alpha.point(lambda v: max(0, min(255, int(round(v * opacity)))))
    amplitude = float(spec.amplitude) * scale

    def displacement(xn: float, yn: float, t: float) -> tuple[float, float]:
        return cloud_displacement(
            xn, yn, t,
            amplitude=amplitude,
            period_s=policy.period_s,
            phase=spec.phase,
        )

    frame_dir, frames = _warp_sequence(
        source=base_half, alpha=alpha, displacement=displacement,
        out_dir=out_dir, name=spec.layer_id, duration=duration, fps=fps,
        grid=(18, 24),
    )
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(frame_dir / "f_%04d.png"), sequence=True)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x="0",
        overlay_y="0",
        info={
            "algorithm": "cloud_drift_v2",
            "frames_dir": str(frame_dir), "frames": frames, "grid": [18, 24],
            "amplitude_px": spec.amplitude, "period_s": policy.period_s,
            "opacity": opacity, "alpha_coverage": mask_coverage(alpha),
        },
    )


def _sway_frames(
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    exclusions: list[RegionSpec],
    duration: float,
    fps: int,
) -> LayerRender:
    """Row-wise horizontal shear with a non-linear, base-anchored weight."""
    width, height = base_half.size
    scale = width / W
    alpha = build_mask(gray_half, spec.mask, feather_scale=0.5,
                       extra_edge_px=int(spec.amplitude), exclusions=exclusions)
    opacity = spec.opacity if spec.opacity is not None else policy.opacity
    alpha = alpha.point(lambda v: max(0, min(255, int(round(v * opacity)))))
    alpha = edge_feather_x(alpha, int(max(spec.feather, policy.feather_px) * scale)
                           + int(spec.amplitude * scale))

    y0 = int(spec.mask.y0 * (height - 1))
    y1 = int(spec.mask.y1 * (height - 1))
    amp = spec.amplitude * scale
    sign = _direction_sign(spec)
    frames = max(1, int(round(duration * fps)))
    frame_dir = out_dir / f"frames_{spec.layer_id}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("f_*.png"):
        old.unlink()
    y0_norm = spec.mask.y0
    y1_norm = spec.mask.y1
    for index in range(frames):
        t = index / fps
        shifted = Image.new("RGB", (width, height), (0, 0, 0))
        for y in range(max(0, y0), min(height - 1, y1) + 1):
            weight = sway_weight(
                y / (height - 1), y0_norm, y1_norm,
                exponent=policy.sway_exponent, top_decay=policy.top_decay,
            )
            if weight <= 0.0:
                row = base_half.crop((0, y, width, y + 1))
            else:
                offset = amp * weight * math.sin(
                    2.0 * math.pi * float(spec.frequency) * t
                    + 2.0 * math.pi * spec.phase + (y / (height - 1)) * 14.4
                ) * sign
                if abs(offset) < 0.25:
                    row = base_half.crop((0, y, width, y + 1))
                else:
                    row = base_half.crop((0, y, width, y + 1)).transform(
                        (width, 1), Image.AFFINE, (1, 0, -offset, 0, 1, 0),
                        resample=Image.BILINEAR,
                    )
            shifted.paste(row, (0, y))
        _save_rgba(shifted, alpha, frame_dir / f"f_{index:04d}.png")
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(frame_dir / "f_%04d.png"), sequence=True)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x="0",
        overlay_y="0",
        info={
            "algorithm": "sway_v2",
            "frames_dir": str(frame_dir), "frames": frames,
            "amplitude_px": spec.amplitude, "frequency_hz": spec.frequency,
            "anchor": "region_bottom", "bottom_displacement_px": 0.0,
            "sway_exponent": policy.sway_exponent, "top_decay": policy.top_decay,
            "opacity": opacity, "alpha_coverage": mask_coverage(alpha),
        },
    )


def _ink_diffusion(
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    duration: float,
    fps: int,
    exclusions: list[RegionSpec],
) -> LayerRender:
    """Soft ink wash growing inside an authored void region.

    This is a procedural wash layer, not a re-paint of the still: the source
    pixels underneath are unchanged and the alpha edge is always feathered.
    """
    width, height = base_half.size
    scale = width / W
    mask = build_mask(gray_half, spec.mask, feather_scale=0.5, exclusions=exclusions)
    mask = edge_feather_x(mask, int(spec.feather * scale))
    opacity = spec.opacity if spec.opacity is not None else policy.opacity
    x0 = int(spec.mask.x0 * (width - 1))
    x1 = int(spec.mask.x1 * (width - 1))
    y0 = int(spec.mask.y0 * (height - 1))
    y1 = int(spec.mask.y1 * (height - 1))
    seeds = [(x0 + (x1 - x0) * 0.28, y0 + (y1 - y0) * 0.55),
             (x0 + (x1 - x0) * 0.72, y0 + (y1 - y0) * 0.38)]
    max_dist = max(1.0, math.hypot(x1 - x0, y1 - y0) * 0.65)
    noise = noise_image((max(2, width // 8), max(2, height // 8)), 60).resize(
        (width, height), Image.BICUBIC
    ).filter(ImageFilter.GaussianBlur(3))
    noise_px = noise.load()
    frame_dir = out_dir / f"ink_{spec.layer_id}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("m_*.png"):
        old.unlink()
    frames = max(1, int(round(duration * fps)))
    mask_px = mask.load()
    for index in range(frames):
        t = index / max(1, frames - 1)
        progress = 0.15 + smoothstep(min(1.0, t / 0.85)) * 1.05
        out = Image.new("L", (width, height), 0)
        dst = out.load()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if mask_px[x, y] == 0:
                    continue
                dist = min(math.hypot(x - sx, y - sy) for sx, sy in seeds) / max_dist
                perturb = (noise_px[x, y] - 128) / 128.0 * 0.12
                value = smoothstep((progress - dist + perturb) / max(0.05, spec.feather / 300.0))
                if value > 0:
                    dst[x, y] = int(round(mask_px[x, y] * value * opacity))
        out.save(frame_dir / f"m_{index:04d}.png")
    ink_rgb = Image.new("RGB", (width, height), (34, 31, 27))
    rgb_path = out_dir / f"rgb_{spec.layer_id}.png"
    ink_rgb.save(rgb_path)
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(rgb_path), sequence=False),
                InputSpec(path=str(frame_dir / "m_%04d.png"), sequence=True)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x="0",
        overlay_y="0",
        info={"rgb": str(rgb_path), "mask_dir": str(frame_dir), "frames": frames,
              "opacity": opacity, "seeds": [list(s) for s in seeds],
              "reveal_complete_at": 0.85, "alpha_coverage": mask_coverage(mask)},
    )


def _external_layer(
    root: Path,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
) -> LayerRender:
    if not spec.asset:
        raise ValueError(f"{spec.layer_id}: external layer needs an asset")
    asset = (root / spec.asset).resolve()
    if not asset.is_file():
        raise FileNotFoundError(asset)
    with Image.open(asset) as image:
        if image.mode != "RGBA":
            raise ValueError(f"{spec.layer_id}: asset must be RGBA, got {image.mode}")
        if image.size != (W, H):
            raise ValueError(f"{spec.layer_id}: asset must be {W}x{H}, got {image.size}")
        path = out_dir / f"layer_{spec.layer_id}.png"
        image.save(path)
        coverage = mask_coverage(image.getchannel("A"))
    amp = spec.amplitude
    progress = f"min(1,max(0,t/{max(0.1, 1.0 / spec.frequency):.6f}))"
    if spec.direction == "rtl":
        x = f"-{amp:.3f}*({progress})"
    elif spec.direction in ("up", "down"):
        x = "0"
    else:
        x = f"{amp:.3f}*({progress})"
    if spec.direction == "down":
        y = f"{amp:.3f}*sin(2*PI*{spec.frequency:.6f}*t)"
    else:
        y = f"-{amp * 0.35:.3f}*sin(2*PI*{spec.frequency:.6f}*t)"
    return LayerRender(
        layer_id=spec.layer_id,
        motion_type=spec.motion_type,
        inputs=[InputSpec(path=str(path), sequence=False)],
        graph="",
        label=f"layer_{spec.layer_id}",
        overlay_x=x,
        overlay_y=y,
        info={"asset": str(path), "amplitude_px": amp, "frequency_hz": spec.frequency,
              "opacity": spec.opacity if spec.opacity is not None else policy.opacity,
              "alpha_coverage": coverage},
    )


def prepare_layers(
    *,
    root: Path,
    base_half: Image.Image,
    gray_half: Image.Image,
    spec: LocalMotionSpec,
    policy: LocalPolicy,
    out_dir: Path,
    duration: float,
    fps: int,
    regions: list[RegionSpec] | None = None,
) -> LayerRender:
    # The shot may omit amplitude/frequency; the style local_policy then supplies
    # the values, so every declared policy field has a real consumer.
    resolved = spec.model_copy(update={
        "amplitude": spec.amplitude if spec.amplitude is not None else policy.amplitude_px,
        "frequency": spec.frequency if spec.frequency is not None else 1.0 / policy.period_s,
    })
    region_list = list(regions or [])
    by_id = {region.id: region for region in region_list}
    region = by_id.get(resolved.region_id) if resolved.region_id else None
    exclusions = effective_exclusions(resolved, region_list)
    _check_region_caps(resolved, region, float(resolved.amplitude or 0.0),
                       float(resolved.frequency or 0.0))

    if resolved.motion_type == "water_ripple":
        layer = _water_ripple(base_half, gray_half, resolved, policy, out_dir, exclusions,
                              duration, fps)
    elif resolved.motion_type == "reflection_distortion":
        layer = _reflection_distortion(base_half, gray_half, resolved, policy, out_dir,
                                       exclusions, duration, fps)
    elif resolved.motion_type == "cloud_drift":
        layer = _cloud_drift(base_half, gray_half, resolved, policy, out_dir, exclusions,
                             duration, fps)
    elif resolved.motion_type in ("leaf_sway", "reed_sway"):
        layer = _sway_frames(base_half, gray_half, resolved, policy, out_dir, exclusions,
                             duration, fps)
    elif resolved.motion_type == "ink_diffusion":
        layer = _ink_diffusion(base_half, gray_half, resolved, policy, out_dir, duration, fps,
                               exclusions)
    elif resolved.motion_type in ("petal_drift", "bird_motion"):
        layer = _external_layer(root, resolved, policy, out_dir)
    else:
        raise ValueError(f"unsupported local motion: {spec.motion_type}")
    layer.info.setdefault("amplitude_requested", spec.amplitude)
    layer.info.setdefault("frequency_requested", spec.frequency)
    layer.info.setdefault("policy_amplitude_px", policy.amplitude_px)
    layer.info.setdefault("policy_period_s", policy.period_s)
    coverage = float(layer.info.get("alpha_coverage", 0.0))
    _check_mask_coverage(resolved, coverage)
    layer.info["protection"] = {
        "region_id": resolved.region_id,
        "role": region.role if region else None,
        "permission": region.permission if region else None,
        "excluded_regions": [item.id for item in exclusions],
        "alpha_coverage": coverage,
        "caps": {
            "max_amplitude_px": region.max_amplitude_px if region else None,
            "max_frequency_hz": region.max_frequency_hz if region else None,
        },
    }
    return layer
