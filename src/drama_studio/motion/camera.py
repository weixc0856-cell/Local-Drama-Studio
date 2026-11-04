"""FFmpeg filter chains for deterministic camera moves.

All expressions are functions of ``t`` (seconds) or zoompan's ``on`` counter,
so a render is reproducible from the recorded CameraSpec alone.

The chain is split into two halves:

* ``camera_pre`` scales the still to an intermediate canvas that keeps the
  source aspect ratio. Local-motion layers are composited on that canvas.
* ``camera_post`` crops / zooms that composed canvas to 1080x1920.

Splitting the chain is what keeps authored masks locked to the content: a
mask and its subject go through the same crop/zoom instead of the mask being
applied to an already-moved frame.
"""

from __future__ import annotations

from .spec import H, W, CameraSpec, progress_expr, scaled_width, zoom_progress_expr

PUSH_MOVES = ("slow_push_in", "slow_pull_out", "push_in_with_pan")


def intermediate_size(spec: CameraSpec, source_size: tuple[int, int]) -> tuple[int, int]:
    """Canvas size after ``camera_pre`` and before ``camera_post``."""
    width, height = source_size
    target_height = H * 2 if spec.move in PUSH_MOVES else H
    return scaled_width(width, height, target_height), target_height


def camera_pre(spec: CameraSpec, fps: int = 24) -> str:
    """Scale the still to the intermediate canvas; no crop and no zoom yet."""
    if spec.move in ("scroll_pan", "slow_lateral_track"):
        return f"scale=-2:{H}:flags=lanczos,format=rgb24,fps={fps}"
    if spec.move == "static":
        return (
            f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"format=rgb24,fps={fps}"
        )
    return (
        f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"format=rgb24,fps={fps}"
    )


def camera_post(spec: CameraSpec, fps: int = 24) -> str:
    """Crop / zoom the composed intermediate canvas to 1080x1920."""
    duration = spec.duration_seconds
    if spec.move in ("scroll_pan", "slow_lateral_track"):
        return f"crop={W}:{H}:x='{pan_expr(spec)}':y=0"
    if spec.move == "static":
        return f"crop={W}:{H}:x='(in_w-out_w)/2':y='(in_h-out_h)/2'"

    # Push/pull render from a 2x canvas so the zoom window never upsamples from
    # a smaller-than-output image.
    frames = max(1, round(duration * fps))
    z = (
        f"{spec.scale_start:.6f}+({spec.scale_end - spec.scale_start:.6f})*"
        f"{zoom_progress_expr(spec.easing)}"
    )
    fx, fy = spec.focus
    x = f"max(0,min(iw-iw/zoom,{fx:.4f}*iw-(iw/zoom)/2"
    if spec.move == "push_in_with_pan":
        x += f"+{spec.push_pan_fraction:.4f}*iw*({zoom_progress_expr(spec.easing)}-0.5)"
    x += "))"
    y = f"max(0,min(ih-ih/zoom,{fy:.4f}*ih-(ih/zoom)/2))"
    return (
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={fps}"
    )


def camera_chain(spec: CameraSpec, fps: int = 24) -> str:
    """Full pre + post chain, kept for callers that still want one string."""
    return f"{camera_pre(spec, fps)},{camera_post(spec, fps)}"


def pan_expr(spec: CameraSpec) -> str:
    progress = progress_expr(spec.easing, spec.duration_seconds)
    return f"{spec.pan_start_px:.3f}+({spec.pan_end_px - spec.pan_start_px:.3f})*{progress}"


def pan_speed(spec: CameraSpec) -> float:
    if spec.duration_seconds <= 0:
        return 0.0
    return round(abs(spec.pan_end_px - spec.pan_start_px) / spec.duration_seconds, 3)
