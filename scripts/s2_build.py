"""S2 visual style validation: deterministic animation primitives.

Two 15-30 s clips are built from one still each:

* ``court_green_fine_line`` — silk/paper texture + slow horizontal scroll pan.
* ``ink_wash`` — animated soft ink mask reveal (matte + diffusion) + raw-paper
  texture + a very slow push-in as local motion.

No new dependencies and no animation framework: texture/mask assets are
generated deterministically with Pillow, and composition is a single FFmpeg
filter graph, matching the R3 approach. Outputs are 1080x1920 / 24 fps.

Example:

    .venv\\Scripts\\python.exe scripts\\s2_build.py ^
        --style court_green_fine_line ^
        --source experiments/s2a/runs/A1/A1_court_green_00001_.png ^
        --duration 20 --out experiments/s2a/renders
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageFilter

from drama_studio.config import find_project_root
from drama_studio.motion.texture import make_texture as _make_texture
from drama_studio.quality import check_image, check_video
from drama_studio.style_presets import load_style_presets

ROOT = find_project_root()
W, H = 1080, 1920
FPS = 24
PAPER_RGB = "0xEDE4D3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-3000:])
    return proc


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- textures


def make_texture(kind: str, path: Path, seed: int = 7) -> dict:
    """Delegate to the production motion package; keep this script's rel() shape."""

    info = _make_texture(kind, path, seed=seed, size=(W, H))
    return {"path": rel(path), **{key: value for key, value in info.items() if key != "path"}}


# ---------------------------------------------------------------- ink masks


def make_ink_masks(mask_dir: Path, *, duration: float, seed: int = 11) -> dict:
    """Soft, noise-perturbed distance mask that expands like ink bleeding.

    Masks are small (270x480) and upscaled/blurred by FFmpeg; this keeps the
    generator fast while the edge stays smooth. A 256-level LUT per frame gives
    a gradual reveal without any hard threshold.
    """

    mw, mh = 270, 480
    frames = int(round(duration * FPS))
    mask_dir.mkdir(parents=True, exist_ok=True)
    for old in mask_dir.glob("mask_*.png"):
        old.unlink()

    seeds = [(0.18, 0.52), (0.72, 0.50), (0.45, 0.62)]
    seed_px = [(sx * (mw - 1), sy * (mh - 1)) for sx, sy in seeds]

    noise = Image.effect_noise((mw // 8 + 1, mh // 8 + 1), 70).resize((mw, mh), Image.BICUBIC)
    noise = noise.filter(ImageFilter.GaussianBlur(3))
    noise_bytes = noise.tobytes()

    values = [0] * (mw * mh)
    corners = [(0, 0), (mw - 1, 0), (0, mh - 1), (mw - 1, mh - 1)]
    max_dist = max(
        min(math.hypot(cx - sx, cy - sy) for sx, sy in seed_px) for cx, cy in corners
    )
    for y in range(mh):
        for x in range(mw):
            dist = min(math.hypot(x - sx, y - sy) for sx, sy in seed_px) / max_dist
            perturb = (noise_bytes[y * mw + x] - 128) / 128.0 * 0.10
            values[y * mw + x] = max(0, min(255, int(round((dist + perturb) * 255))))
    field = Image.new("L", (mw, mh))
    field.putdata(values)

    for index in range(1, frames + 1):
        t = (index - 1) / max(1, frames - 1)
        # A small ink seed is visible from the first frame; the rest spreads
        # upward over ~82% of the clip, then holds on the finished painting.
        progress = 0.08 + smoothstep(min(1.0, t / 0.82)) * 1.02
        lut = []
        for q in range(256):
            value = (progress - q / 255.0) / 0.12
            lut.append(max(0, min(255, int(round(value * 255)))))
        field.point(lut).save(mask_dir / f"mask_{index:04d}.png")

    return {
        "dir": rel(mask_dir),
        "frames": frames,
        "size": [mw, mh],
        "seed": seed,
        "seed_points": seeds,
        "softness": 0.12,
        "reveal_complete_at": 0.82,
    }


# ---------------------------------------------------------------- builds


def build_scroll(
    *,
    source: Path,
    texture: Path,
    out: Path,
    duration: float,
    texture_opacity: float,
    pan_start: float = 0.0,
    pan_end: float = 1.0,
) -> list[str]:
    """Crop-window scroll. ``pan_start``/``pan_end`` are fractions of the pan range.

    Defaults (0 -> 1) reproduce the original full-width left-to-right scroll.
    A smaller range yields the same constant speed over a shorter shot.
    """
    if not (0.0 <= pan_start <= 1.0 and 0.0 <= pan_end <= 1.0):
        raise ValueError("pan_start/pan_end must be within 0..1")
    graph = (
        f"[0:v]scale=-2:{H}:flags=lanczos,format=rgb24,"
        f"crop={W}:{H}:x='(in_w-out_w)*({pan_start:.6f}+{pan_end - pan_start:.6f}*(t/{duration:.3f}))':y=0,fps={FPS}[base];"
        f"[1:v]format=rgb24[tex];"
        f"[base][tex]blend=all_mode=overlay:all_opacity={texture_opacity:.2f},"
        f"format=yuv420p[outv]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-loop", "1", "-i", str(source),
        "-framerate", str(FPS), "-loop", "1", "-i", str(texture),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-filter_complex", graph,
        "-map", "[outv]", "-map", "2:a",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)
    return cmd


def build_ink(
    *,
    source: Path,
    texture: Path,
    mask_dir: Path,
    out: Path,
    duration: float,
    texture_opacity: float,
) -> list[str]:
    frames = int(round(duration * FPS))
    graph = (
        f"[0:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='min(zoom+0.00015,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},format=rgb24[base];"
        f"[1:v]scale={W}:{H}:flags=bicubic,gblur=sigma=6,format=gray[mask];"
        f"[base][mask]alphamerge[fg];"
        f"color=c={PAPER_RGB}:s={W}x{H}:r={FPS}:d={duration:.3f}[bg];"
        f"[bg][fg]overlay=format=auto,format=rgb24[ink];"
        f"[2:v]format=rgb24[tex];"
        f"[ink][tex]blend=all_mode=overlay:all_opacity={texture_opacity:.2f},"
        f"format=yuv420p[outv]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-loop", "1", "-i", str(source),
        "-framerate", str(FPS), "-i", str(mask_dir / "mask_%04d.png"),
        "-framerate", str(FPS), "-loop", "1", "-i", str(texture),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-filter_complex", graph,
        "-map", "[outv]", "-map", "3:a",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)
    return cmd


# ---------------------------------------------------------------- evidence


def sample_frames(video: Path, out_dir: Path, duration: float) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    points = [("first", 0.5), ("mid", duration / 2), ("last", max(0.5, duration - 1.0))]
    frames = []
    for name, at in points:
        path = out_dir / f"frame_{name}.png"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video),
             "-frames:v", "1", str(path)])
        frames.append({"name": name, "at_seconds": round(at, 3), **check_image(path),
                       "path": rel(path), "sha256": sha256(path)})
    return frames


def black_frames(video: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(video),
         "-vf", "blackdetect=d=0.1:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    hits = [line for line in proc.stderr.splitlines() if "black_start" in line]
    return {"returncode": proc.returncode, "black_segments": hits}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an S2 style validation clip")
    parser.add_argument("--style", required=True, help="style preset id")
    parser.add_argument("--source", required=True, help="generated still (PNG)")
    parser.add_argument("--duration", type=float, required=True, help="15-30 seconds")
    parser.add_argument("--out", required=True, help="renders root")
    parser.add_argument("--texture-seed", type=int, default=7)
    parser.add_argument("--mask-seed", type=int, default=11)
    args = parser.parse_args(argv)

    if not 15.0 <= args.duration <= 30.0:
        raise SystemExit("--duration must be within 15-30 seconds")
    registry = load_style_presets(ROOT)
    preset = registry.get(args.style)
    source = (ROOT / args.source).resolve()
    if not source.is_file():
        raise SystemExit(f"source not found: {source}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = (ROOT / args.out / f"build-{stamp}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    texture_kind = "silk" if preset.compositing.texture.kind == "silk" else "raw_paper"
    texture = out_dir / f"texture_{texture_kind}.png"
    texture_info = make_texture(texture_kind, texture, seed=args.texture_seed)

    mask_info = None
    if "ink_matte" in preset.compositing.primitives:
        mask_info = make_ink_masks(out_dir / "masks", duration=args.duration, seed=args.mask_seed)
        output = out_dir / "final_9x16.mp4"
        argv_used = build_ink(
            source=source, texture=texture, mask_dir=out_dir / "masks",
            out=output, duration=args.duration,
            texture_opacity=preset.compositing.texture.opacity,
        )
    else:
        output = out_dir / "final_9x16.mp4"
        argv_used = build_scroll(
            source=source, texture=texture, out=output, duration=args.duration,
            texture_opacity=preset.compositing.texture.opacity,
        )

    with Image.open(source) as image:
        source_size = list(image.size)
    video_check = check_video(output, expected_width=W, expected_height=H)
    frames = sample_frames(output, out_dir / "frames", args.duration)
    black = black_frames(output)
    style_config = ROOT / "config" / "styles.yaml"
    manifest = {
        "stage": "S2",
        "style_id": preset.id,
        "style_name": preset.name,
        "style_config": rel(style_config),
        "style_config_sha256": sha256(style_config),
        "style_preset": preset.model_dump(),
        "source": {"path": rel(source), "sha256": sha256(source), "size": source_size},
        "texture": texture_info,
        "mask": mask_info,
        "duration_seconds": args.duration,
        "fps": FPS,
        "size": [W, H],
        "argv": argv_used,
        "outputs": {
            "final": rel(output),
            "final_sha256": sha256(output),
            "bytes": output.stat().st_size,
        },
        "video_check": video_check,
        "sample_frames": frames,
        "black_frames": black,
        "human_review": {
            "status": "PENDING",
            "note": "技术项由脚本检查；风格像不像工笔/水墨必须人工看片后才能 PASS_VERIFIED",
        },
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "style": preset.id,
        "build": rel(out_dir),
        "final": rel(output),
        "video_check": video_check["status"],
        "frames": [f["status"] for f in frames],
        "black_segments": len(black["black_segments"]),
    }, ensure_ascii=False))
    return 0 if video_check["status"] == "PASS" and black["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
