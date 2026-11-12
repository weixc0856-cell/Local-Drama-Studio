"""Optional learned super-resolution stage for Wan clips.

The pipeline already separates low-resolution temporal generation from final
1920x1080 assembly: Wan runs at 448x768 (or 576x1024) and r3_build upscales with
Lanczos. Lanczos is a resampler, not a texture reconstructor. A learned SR stage
can add detail, but it is opt-in because this repo has no SR model or weights,
and adding PyTorch to the root venv is forbidden.

Supported backends:

* ``lanczos`` (default, verified): FFmpeg scale + optional light denoise.
* ``realesrgan-ncnn``: any local ``realesrgan-ncnn-vulkan`` executable
  (``REALESRGAN_NCNN`` or ``D:/AI/tools/realesrgan-ncnn-vulkan``). This is an
  external tool, not a Python dependency.

A requested backend that is missing fails loudly; it never silently falls back.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

Backend = Literal["lanczos", "realesrgan-ncnn"]

W, H = 1920, 1080


class UpscaleError(RuntimeError):
    pass


def _find_ncnn() -> Path | None:
    configured = os.environ.get("REALESRGAN_NCNN")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates += [
        Path("D:/AI/tools/realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan.exe"),
        Path("D:/AI/tools/realesrgan/realesrgan-ncnn-vulkan.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return shutil.which("realesrgan-ncnn-vulkan")


def available_backends() -> dict[str, dict]:
    ncnn = _find_ncnn()
    return {
        "lanczos": {"available": True, "kind": "ffmpeg", "note": "verified default"},
        "realesrgan-ncnn": {
            "available": ncnn is not None,
            "kind": "external",
            "path": str(ncnn) if ncnn else None,
            "note": "needs the ncnn-vulkan executable and model weights; no Python dependency",
        },
    }


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise UpscaleError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-1500:])


def _lanczos(src: Path, out: Path, *, width: int, height: int, denoise: bool) -> Path:
    vf = f"scale={width}:{height}:flags=lanczos,setsar=1"
    if denoise:
        # Light temporal denoise keeps SR from amplifying paper-grain noise and
        # reduces frame-to-frame shimmer without softening the motion.
        vf = "hqdn3d=1.2:1.2:5:5," + vf
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
          "-c:v", "libx264", "-crf", "18", "-preset", "medium",
          "-pix_fmt", "yuv420p", str(out)])
    return out


def _ncnn(src: Path, out: Path, *, width: int, height: int, denoise: bool,
          model: str = "realesrnet-x4plus", scale: int = 4, tile_size: int = 128) -> Path:
    exe = _find_ncnn()
    if exe is None:
        raise UpscaleError(
            "realesrgan-ncnn-vulkan not found; set REALESRGAN_NCNN or install it under D:/AI/tools")
    with tempfile.TemporaryDirectory() as directory:
        frames = Path(directory) / "in"
        upscaled = Path(directory) / "out"
        frames.mkdir()
        upscaled.mkdir()
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vsync", "0",
              str(frames / "f_%06d.png")])
        command = [str(exe), "-i", str(frames), "-o", str(upscaled),
                   "-n", model, "-s", str(scale), "-f", "png"]
        if tile_size > 0:
            command += ["-t", str(tile_size)]
        _run(command)
        vf = f"scale={width}:{height}:flags=lanczos,setsar=1"
        if denoise:
            vf = "hqdn3d=1.2:1.2:5:5," + vf
        _run(["ffmpeg", "-y", "-v", "error", "-framerate", "24",
              "-i", str(upscaled / "f_%06d.png"), "-vf", vf,
              "-c:v", "libx264", "-crf", "18", "-preset", "medium",
              "-pix_fmt", "yuv420p", str(out)])
    return out


def upscale_clip(
    src: Path,
    out: Path,
    *,
    backend: Backend = "lanczos",
    width: int = W,
    height: int = H,
    denoise: bool = True,
    model: str = "realesrnet-x4plus",
    scale: int = 4,
    tile_size: int = 128,
) -> dict:
    """Upscale one clip. ``lanczos`` is the verified fallback; ncnn is opt-in."""
    if not src.is_file():
        raise UpscaleError(f"source clip not found: {src}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if backend == "lanczos":
        _lanczos(src, out, width=width, height=height, denoise=denoise)
    elif backend == "realesrgan-ncnn":
        _ncnn(src, out, width=width, height=height, denoise=denoise,
              model=model, scale=scale, tile_size=tile_size)
    else:
        raise UpscaleError(f"unknown upscale backend: {backend}")
    return {"source": str(src), "output": str(out), "backend": backend,
            "width": width, "height": height, "denoise": denoise,
            "model": model, "scale": scale, "tile_size": tile_size}


def upscale_wan_clips(
    project_root: Path,
    shot_ids: list[str],
    *,
    backend: Backend = "lanczos",
    width: int = W,
    height: int = H,
    denoise: bool = True,
    force: bool = False,
    model: str = "realesrnet-x4plus",
    scale: int = 4,
    tile_size: int = 128,
) -> dict:
    """Write ``<shot>_sr.mp4`` next to each encoded Wan clip.

    ``resolve_asset`` picks the newest video, so the SR file wins only after it
    is written; the original clip remains for provenance and rollback.
    """
    clips: dict[str, dict] = {}
    for shot_id in shot_ids:
        directory = project_root / "shots" / shot_id
        source = directory / f"{shot_id}_clip.mp4"
        if not source.is_file():
            source = directory / f"{shot_id}_wan.mp4"
        if not source.is_file():
            continue
        target = directory / f"{shot_id}_sr.mp4"
        if target.is_file() and not force:
            clips[shot_id] = {"output": str(target), "reused": True, "backend": backend}
            continue
        clips[shot_id] = upscale_clip(
            source, target, backend=backend, width=width, height=height,
            denoise=denoise, model=model, scale=scale, tile_size=tile_size)
    return {"backend": backend, "clips": clips, "count": len(clips)}
