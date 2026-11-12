"""Layered plate composition for 2.5D shots.

A plate is one motion plane: a background, a cut-out subject, or an
independently generated foreground element. Every plate is driven by the same
camera; the only per-plate parameter is ``depth_alpha`` (plane distance divided
by background distance). That is what stops plates from drifting apart or
inventing their own motion.

Two camera models, because the two shot types need different things:

``dolly``  the window shrinks by ``1/s`` about the focus, clamped to the plate
           exactly like production's ``zoompan``. A nearer plane shrinks faster.
``pan``    the window is full height and slides sideways. A nearer plane slides
           farther, by ``1 / depth_alpha`` of the background's travel.

The pan model is why a long-scroll shot needs a canvas with margin: nothing
covers a plane that walks off its own plate, so the window origin is *not*
clamped for pan — a plane that runs out of plate is a defect the gate must see,
not something to hide.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image

from drama_studio.domain.motion.spec import H, W, PlateSpec

Window = tuple[float, float, float, float]  # x0, y0, width, height (plate-normalized)


@dataclass(frozen=True)
class LoadedPlate:
    spec: PlateSpec
    image: Image.Image  # RGBA, already upscaled for sampling


@dataclass(frozen=True)
class CameraState:
    """Where the background window is at one instant."""

    mode: Literal["dolly", "pan"] = "dolly"
    scale: float = 1.0
    focus: tuple[float, float] = (0.5, 0.48)
    pan: float = 0.0        # background window left edge, in plate-normalized units
    pan_start: float = 0.0
    span: float = 1.0       # how much of the plate's width the frame covers

    def plane_window(self, depth_alpha: float) -> Window:
        if self.mode == "pan":
            return pan_window(self.pan, depth_alpha, self.pan_start, self.span)
        return camera_window(plate_scale(self.scale, depth_alpha), self.focus)


def ease_value(easing: str, progress: float) -> float:
    """Numeric easing, matching the FFmpeg expressions in ``spec._ease``."""
    p = max(0.0, min(1.0, progress))
    if easing == "linear":
        return p
    if easing == "ease_in":
        return p * p
    if easing == "ease_out":
        return 1.0 - (1.0 - p) * (1.0 - p)
    return p * p * (3.0 - 2.0 * p)


def background_scale(camera, index: int, frames: int) -> float:
    """The background plane's scale on frame ``index`` (dolly shots)."""
    progress = index / max(1, frames - 1)
    span = float(camera.scale_end) - float(camera.scale_start)
    return float(camera.scale_start) + span * ease_value(camera.easing, progress)


def background_pan(camera, index: int, frames: int, panel_width: float) -> float:
    """Background window left edge on frame ``index`` (pan shots), plate-normalized."""
    progress = index / max(1, frames - 1)
    start = float(camera.pan_start_px)
    end = float(camera.pan_end_px)
    pixels = start + (end - start) * ease_value(camera.easing, progress)
    return pixels / max(1.0, panel_width)


def plate_scale(scale_bg: float, depth_alpha: float) -> float:
    """Scale of a plane at ``depth_alpha`` under the background's dolly.

    ``u`` is the camera's progress as a fraction of the background distance, so
    the same projective relationship applies to every plane and a nearer plane
    can never scale slower than a farther one for a given ``u``.
    """
    if scale_bg <= 0.0:
        raise ValueError(f"scale_bg must be positive, got {scale_bg}")
    if depth_alpha >= 1.0:
        return float(scale_bg)
    if depth_alpha <= 0.0:
        raise ValueError(f"depth_alpha must be positive, got {depth_alpha}")
    u = 1.0 - 1.0 / float(scale_bg)
    return 1.0 / (1.0 - u / depth_alpha)


def camera_window(scale: float, focus: tuple[float, float]) -> Window:
    """Dolly window: origin and size, clamped exactly like ``zoompan``'s x/y."""
    window = 1.0 / float(scale)
    if window > 1.0:
        raise ValueError(f"scale must be >= 1.0, got {scale}")
    fx, fy = focus
    x0 = min(max(fx - 0.5 * window, 0.0), 1.0 - window)
    y0 = min(max(fy - 0.5 * window, 0.0), 1.0 - window)
    return x0, y0, window, window


def pan_window(pan: float, depth_alpha: float = 1.0, pan_start: float = 0.0,
               span: float = 1.0) -> Window:
    """Pan window: full height, ``span`` of the width, sliding sideways unclamped.

    ``span`` is the frame's width as a fraction of the plate's: a wide plate
    seen through a 9:16 frame covers well under half of it, and forgetting that
    is what pushes the window off the plate (a black bar) on the second frame.
    """
    if depth_alpha <= 0.0:
        raise ValueError(f"depth_alpha must be positive, got {depth_alpha}")
    if not 0.0 < span <= 1.0:
        raise ValueError(f"span must be in (0, 1], got {span}")
    x0 = pan_start + (pan - pan_start) / depth_alpha
    return x0, 0.0, span, 1.0


def map_point(point: tuple[float, float], window: Window) -> tuple[float, float]:
    """Where a normalized plate point lands on screen under this window."""
    x0, y0, span_x, span_y = window
    return ((point[0] - x0) / span_x, (point[1] - y0) / span_y)


def sample_window(image: Image.Image, window: Window,
                  out_size: tuple[int, int] = (W, H)) -> Image.Image:
    """Sample a plate through ``window`` into ``out_size``."""
    layer_w, layer_h = image.size
    out_w, out_h = out_size
    x0, y0, span_x, span_y = window
    return image.transform(
        (out_w, out_h), Image.AFFINE,
        (span_x * layer_w / out_w, 0.0, x0 * layer_w,
         0.0, span_y * layer_h / out_h, y0 * layer_h),
        resample=Image.BICUBIC)


def sample(image: Image.Image, scale: float, focus: tuple[float, float],
           out_size: tuple[int, int] = (W, H)) -> Image.Image:
    """Sample a plate under a dolly camera (kept for existing callers)."""
    return sample_window(image, camera_window(scale, focus), out_size)


def place(image: Image.Image, anchor, window: Window,
          out_size: tuple[int, int] = (W, H)) -> Image.Image:
    """Place a partial plate with sub-pixel accuracy.

    Resizing to an integer box and pasting at an integer offset quantises the
    motion to whole pixels, which reads as judder on a slow move. Sampling the
    plate through its own affine keeps the placement continuous.
    """
    left, top = map_point((anchor.x0, anchor.y0), window)
    right, bottom = map_point((anchor.x1, anchor.y1), window)
    span_x = right - left
    span_y = bottom - top
    if span_x <= 1e-9 or span_y <= 1e-9:
        raise ValueError("anchor collapses to zero size under this camera")
    layer_w, layer_h = image.size
    out_w, out_h = out_size
    return image.transform(
        (out_w, out_h), Image.AFFINE,
        (layer_w / (out_w * span_x), 0.0, -left * layer_w / span_x,
         0.0, layer_h / (out_h * span_y), -top * layer_h / span_y),
        resample=Image.BICUBIC)


def enforce_policy(policy, *, shot_id: str, move: str, plates: list) -> None:
    """Refuse a layered shot the style does not permit.

    Kept here rather than in the renderer so the rule has one home and can be
    tested without building a shot.
    """
    if not getattr(policy, "allowed", False):
        raise ValueError(f"{shot_id}: 当前风格未允许分层 2.5D")
    moves = list(getattr(policy, "camera_moves", []) or [])
    if move not in moves:
        raise ValueError(
            f"{shot_id}: {move} 不在该风格允许的分层镜头类型 {moves} 中")
    if len(plates) > int(getattr(policy, "max_plates", 3)):
        raise ValueError(
            f"{shot_id}: {len(plates)} 层超过上限 {policy.max_plates}")
    for plate in plates:
        if getattr(plate, "coverage", "full_frame") == "full_frame":
            continue  # the background defines the reference distance; alpha 1.0
        alpha = float(plate.depth_alpha)
        if not (policy.depth_alpha_min <= alpha <= policy.depth_alpha_max):
            raise ValueError(
                f"{shot_id}/{plate.id}: depth_alpha {alpha} 超出允许区间 "
                f"[{policy.depth_alpha_min}, {policy.depth_alpha_max}]")


def load_plate(spec: PlateSpec, root: Path, factor: int = 2) -> LoadedPlate:
    path = Path(spec.path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise FileNotFoundError(f"{spec.id}: plate not found: {path}")
    image = Image.open(path).convert("RGBA")
    return LoadedPlate(spec=spec, image=image.resize(
        (image.width * factor, image.height * factor), Image.LANCZOS))


def compose(plates: list[LoadedPlate], state: CameraState,
            out_size: tuple[int, int] = (W, H)) -> Image.Image:
    """Compose the stack for one frame, farthest first."""
    ordered = sorted(plates, key=lambda item: item.spec.z_order)
    background = next((item for item in ordered if item.spec.coverage == "full_frame"), None)
    if background is None:
        raise ValueError("no full_frame background plate in the stack")

    canvas = sample_window(background.image, state.plane_window(1.0), out_size).convert("RGBA")
    for item in ordered:
        if item.spec is background.spec:
            continue
        anchor = item.spec.anchor
        if anchor is None:
            raise ValueError(f"{item.spec.id}: partial plate without anchor")
        window = state.plane_window(item.spec.depth_alpha)
        canvas.alpha_composite(place(item.image, anchor, window, out_size))
    return canvas.convert("RGB")
