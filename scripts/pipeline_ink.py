"""Pipeline A first validation: static ink landscape + layered deterministic motion.

This is intentionally narrow. It proves four things on one still:

* a soft cloud layer can drift horizontally while the mountain body stays frozen;
* the water layer can move by a few pixels without touching the shore or boat;
* the boat can drift by a few pixels as a feathered patch;
* raw-paper texture can be layered without washing out the ink.

It does not add a general animation framework and does not call Wan. Layers are
defined per sample in ``layers.json``; the script only consumes them.

Usage:

    .venv\\Scripts\\python.exe scripts\\pipeline_ink.py ^
        --source experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png ^
        --layers experiments/pipeline_a/layers.json ^
        --static-quality experiments/pipeline_a/static/IA4/static_quality.json ^
        --duration 20 --out experiments/pipeline_a/renders
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from s2_build import (  # noqa: E402 - shared experiment helpers, not a framework
    black_frames,
    check_image,
    check_video,
    make_texture,
    rel,
    run,
    sample_frames,
    sha256,
)
from drama_studio.config import find_project_root
from drama_studio.style_presets import load_style_presets  # noqa: E402

ROOT = find_project_root()
W, H, FPS = 1080, 1920, 24


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def vertical_feather(y: int, y0: int, y1: int, feather: int) -> float:
    if y < y0 or y > y1:
        return 0.0
    return min(1.0, (y - y0) / max(1, feather), (y1 - y) / max(1, feather))


def luma_alpha(gray: Image.Image, band: tuple[float, float], lo: int, hi: int, feather: int) -> Image.Image:
    """Soft alpha for the bright mist inside a vertical band.

    The mask is computed from a blurred luminance, not raw pixels: thin bright
    ridge highlights average out, while broad mist survives. This keeps the
    cloud layer from dragging mountain structure with it.
    """
    width, height = gray.size
    y0, y1 = int(band[0] * height), int(band[1] * height)
    alpha = Image.new("L", gray.size, 0)
    blurred = gray.filter(ImageFilter.GaussianBlur(6))
    src = blurred.load()
    dst = alpha.load()
    span = max(1, hi - lo)
    for y in range(y0, y1 + 1):
        vf = vertical_feather(y, y0, y1, feather)
        if vf <= 0:
            continue
        for x in range(width):
            value = (src[x, y] - lo) / span
            a = smoothstep(value) * vf
            if a > 0:
                dst[x, y] = int(round(a * 255))
    return alpha


def band_alpha(size: tuple[int, int], band: tuple[float, float], feather: int) -> Image.Image:
    width, height = size
    y0, y1 = int(band[0] * height), int(band[1] * height)
    alpha = Image.new("L", size, 0)
    dst = alpha.load()
    for y in range(y0, y1 + 1):
        vf = vertical_feather(y, y0, y1, feather)
        if vf <= 0:
            continue
        value = int(round(vf * 255))
        for x in range(width):
            dst[x, y] = value
    return alpha


def subtract_box(alpha: Image.Image, box: tuple[int, int, int, int], feather: int) -> Image.Image:
    """Feather a rectangular hole into an alpha mask (used to keep the boat still)."""
    hole = Image.new("L", alpha.size, 255)
    draw = ImageDraw.Draw(hole)
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], fill=0)
    hole = hole.filter(ImageFilter.GaussianBlur(feather))
    # hole is white outside the exclusion box and black inside; keep alpha
    # outside and zero it inside. The previous argument order was inverted,
    # which left only the boat/reflection area animated and froze the water.
    return Image.composite(alpha, Image.new("L", alpha.size, 0), hole)


def boat_alpha(size: tuple[int, int], box: tuple[int, int, int, int], feather: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather))


def edge_feather(alpha: Image.Image, px: int) -> Image.Image:
    """Fade the left/right edges so a shifting layer never leaves a hard seam."""

    if px <= 0:
        return alpha
    width, height = alpha.size
    ramp = Image.new("L", (width, 1), 0)
    for x in range(width):
        value = min(1.0, x / px, (width - 1 - x) / px)
        ramp.putpixel((x, 0), int(round(value * 255)))
    return ImageChops.multiply(alpha, ramp.resize((width, height)))


def make_cloud_frames(
    base_half: Image.Image,
    gray_half: Image.Image,
    layers: dict,
    out_dir: Path,
    duration: float,
    fps: int,
) -> dict:
    """Cloud RGBA frames with a slow opacity modulation baked into alpha.

    FFmpeg shifts the sequence horizontally; baking opacity here avoids an
    expensive full-resolution geq over every frame.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("cloud_*.png"):
        old.unlink()
    size = base_half.size
    scale = size[0] / W
    band = tuple(layers["cloud_band"])
    alpha = luma_alpha(
        gray_half,
        band,
        layers["cloud_luma"][0],
        layers["cloud_luma"][1],
        int(layers.get("cloud_feather_px", 40) * scale),
    )
    alpha = edge_feather(alpha, int(layers.get("cloud_edge_feather_px", 100) * scale))
    gain = float(layers.get("cloud_alpha_gain", 1.0))
    if gain != 1.0:
        alpha = alpha.point(lambda v: max(0, min(255, int(round(v * gain)))))
    frames = int(round(duration * fps))
    lo = float(layers.get("cloud_opacity_min", 0.90))
    hi = float(layers.get("cloud_opacity_max", 1.00))
    period = float(layers.get("cloud_opacity_period_s", duration))
    for index in range(1, frames + 1):
        t = (index - 1) / max(1, frames - 1)
        phase = 0.5 + 0.5 * math.sin(2.0 * math.pi * t * duration / period)
        opacity = lo + (hi - lo) * phase
        frame = base_half.copy()
        frame.putalpha(alpha.point(lambda v: max(0, min(255, int(round(v * opacity))))))
        frame.save(out_dir / f"cloud_{index:04d}.png")
    return {
        "dir": rel(out_dir),
        "frames": frames,
        "size": list(size),
        "opacity_min": lo,
        "opacity_max": hi,
        "opacity_period_s": period,
        "edge_feather_px": layers.get("cloud_edge_feather_px", 100),
    }


def make_ripple_layer(
    base_half: Image.Image,
    water_alpha_half: Image.Image,
    layers: dict,
    path: Path,
) -> dict:
    """Low-contrast horizontal ripple texture masked to the water region.

    This is an overlay, not a pixel remap: it adds shimmer without moving the
    boat, reflection or shoreline geometry. OpenCV is not installed, and a
    1.5-2.5 px remap at 1080p is below the 8-bit displace filter's resolution.
    """

    width, height = base_half.size
    scale = width / W
    wavelength = max(4.0, float(layers.get("ripple_wavelength_px", 40)) * scale)
    brightness = float(layers.get("ripple_brightness", 10))
    noise = Image.effect_noise((width // 8 + 1, height // 8 + 1), 40).resize(
        (width, height), Image.BICUBIC
    ).filter(ImageFilter.GaussianBlur(4))
    texture = Image.new("L", (width, height), 128)
    dst = texture.load()
    noise_px = noise.load()
    for y in range(height):
        phase_y = 0.8 * math.sin(2.0 * math.pi * y / max(1.0, height * 0.15))
        for x in range(width):
            wave = math.sin(2.0 * math.pi * x / wavelength + phase_y)
            n = (noise_px[x, y] - 128) / 128.0
            value = 128.0 + brightness * (0.55 * wave + 0.45 * n)
            dst[x, y] = max(0, min(255, int(round(value))))
    opacity = float(layers.get("ripple_opacity", 0.25))
    alpha = water_alpha_half.point(lambda v: max(0, min(255, int(round(v * opacity)))))
    alpha = edge_feather(alpha, int(layers.get("ripple_edge_feather_px", 30) * scale))
    layer = texture.convert("RGB")
    layer.putalpha(alpha)
    layer.save(path)
    return {
        "path": rel(path),
        "size": [width, height],
        "wavelength_px": layers.get("ripple_wavelength_px", 40),
        "brightness": brightness,
        "opacity": opacity,
        "amplitude_px": layers.get("ripple_amplitude_px", 12),
        "period_s": layers.get("ripple_period_s", 3.333),
        "edge_feather_px": layers.get("ripple_edge_feather_px", 30),
    }


def make_plate_frames(
    base_half: Image.Image,
    gray_half: Image.Image,
    layers: dict,
    out_dir: Path,
    duration: float,
    fps: int,
) -> dict:
    """Soft procedural white-mist plate for the waist band.

    The still's own mist is low-contrast and concentrated at the tree line; a
    large translation of that layer ghosts the mountain structure. This plate
    carries its own soft noise, is restricted to bright areas, and adds moving
    haze without dragging ridges or trees.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("plate_*.png"):
        old.unlink()
    width, height = base_half.size
    scale = width / W
    band = tuple(layers.get("plate_band", [0.48, 0.64]))
    y0, y1 = int(band[0] * height), int(band[1] * height)
    feather = int(layers.get("plate_band_feather_px", 50) * scale)
    opacity = float(layers.get("plate_opacity", 0.35))
    bright_lo = float(layers.get("plate_bright_lo", 160))
    bright_span = float(layers.get("plate_bright_span", 80))
    noise_div = max(2, int(layers.get("plate_noise_div", 6)))
    noise_blur = float(layers.get("plate_noise_blur", 6))
    bright = gray_half.filter(ImageFilter.GaussianBlur(4))
    bright_px = bright.load()
    noise = Image.effect_noise((width // noise_div + 1, height // noise_div + 1), 70).resize(
        (width, height), Image.BICUBIC
    ).filter(ImageFilter.GaussianBlur(noise_blur))
    noise_px = noise.load()
    alpha = Image.new("L", (width, height), 0)
    dst = alpha.load()
    for y in range(y0, y1 + 1):
        vf = vertical_feather(y, y0, y1, feather)
        if vf <= 0:
            continue
        for x in range(width):
            bright_mask = smoothstep((bright_px[x, y] - bright_lo) / bright_span)
            n = smoothstep((noise_px[x, y] - 90) / 80.0)
            value = vf * bright_mask * (0.35 + 0.65 * n) * opacity
            if value > 0:
                dst[x, y] = max(0, min(255, int(round(value * 255))))
    alpha = edge_feather(alpha, int(layers.get("plate_edge_feather_px", 100) * scale))
    frames = int(round(duration * fps))
    lo = float(layers.get("cloud_opacity_min", 0.90))
    hi = float(layers.get("cloud_opacity_max", 1.00))
    period = float(layers.get("cloud_opacity_period_s", duration))
    for index in range(1, frames + 1):
        t = (index - 1) / max(1, frames - 1)
        phase = 0.5 + 0.5 * math.sin(2.0 * math.pi * t * duration / period)
        factor = lo + (hi - lo) * phase
        frame = Image.new("RGB", (width, height), (246, 246, 244))
        frame.putalpha(alpha.point(lambda v: max(0, min(255, int(round(v * factor))))))
        frame.save(out_dir / f"plate_{index:04d}.png")
    return {
        "dir": rel(out_dir),
        "frames": frames,
        "size": [width, height],
        "band": list(band),
        "opacity": opacity,
        "shift_px": layers.get("plate_shift_px", 96),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the pipeline-A ink motion validation clip")
    parser.add_argument("--source", required=True)
    parser.add_argument("--layers", required=True)
    parser.add_argument("--static-quality", required=True)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if not 3.0 <= args.duration <= 30.0:
        raise SystemExit("--duration must be within 3-30 seconds (3 s is the Wan A/B slice)")
    source = (ROOT / args.source).resolve()
    layers = json.loads((ROOT / args.layers).read_text(encoding="utf-8"))
    quality = json.loads((ROOT / args.static_quality).read_text(encoding="utf-8"))
    if quality.get("overall_status") == "FAIL":
        raise SystemExit("static quality gate is FAIL; repair the still before animation")
    if quality.get("overall_status") not in ("PASS_STATIC", "PARTIAL"):
        raise SystemExit(f"static quality gate not ready: {quality.get('overall_status')}")

    preset = load_style_presets(ROOT).get("ink_wash")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = (ROOT / args.out / f"build-{stamp}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    layers_dir = out_dir / "layers"
    layers_dir.mkdir()

    base = Image.open(source).convert("RGB").resize((W, H), Image.LANCZOS)
    base_path = layers_dir / "base.png"
    base.save(base_path)
    gray = base.convert("L")
    half_size = (W // 2, H // 2)
    base_half = base.resize(half_size, Image.LANCZOS)
    gray_half = base_half.convert("L")

    cloud_is_sequence = "cloud_opacity_min" in layers
    cloud_info = None
    cloud_path: Path | None = None
    if cloud_is_sequence:
        cloud_info = make_cloud_frames(
            base, gray, layers, layers_dir / "cloud_frames",
            args.duration, FPS,
        )
    else:
        cloud_alpha = luma_alpha(gray, tuple(layers["cloud_band"]),
                                 layers["cloud_luma"][0], layers["cloud_luma"][1],
                                 int(layers.get("cloud_feather_px", 60)))
        if layers.get("cloud_edge_feather_px"):
            cloud_alpha = edge_feather(cloud_alpha, int(layers["cloud_edge_feather_px"]))
        cloud = base.copy()
        cloud.putalpha(cloud_alpha)
        cloud_path = layers_dir / "cloud.png"
        cloud.save(cloud_path)

    water_band = tuple(layers["water_band"])
    water_alpha = band_alpha((W, H), water_band, int(layers.get("water_feather_px", 40)))

    def norm_box(values: list[float]) -> tuple[int, int, int, int]:
        return tuple(int(round(v * (W if i % 2 == 0 else H))) for i, v in enumerate(values))

    for exclude in layers.get("water_exclude_boxes", []):
        water_alpha = subtract_box(water_alpha, norm_box(exclude),
                                   int(layers.get("water_exclude_feather_px", 20)))

    boat_box = norm_box(layers["boat_bbox"])
    reflection_box = norm_box(layers["reflection_bbox"])
    boat_margin = int(layers.get("boat_mask_margin_px", 20))
    for box in (boat_box, reflection_box):
        expanded = (box[0] - boat_margin, box[1] - boat_margin,
                    box[2] + boat_margin, box[3] + boat_margin)
        water_alpha = subtract_box(water_alpha, expanded,
                                   int(layers.get("water_hole_feather_px", 25)))
    water = base.copy()
    water.putalpha(water_alpha)
    water_path = layers_dir / "water.png"
    water.save(water_path)

    boat_mask = boat_alpha((W, H), boat_box, int(layers.get("boat_feather_px", 30)))
    boat = base.copy()
    boat.putalpha(boat_mask)
    boat_path = layers_dir / "boat.png"
    boat.save(boat_path)

    reflection_mask = boat_alpha((W, H), reflection_box,
                                 int(layers.get("reflection_feather_px", 25)))
    reflection = base.copy()
    reflection.putalpha(reflection_mask)
    reflection_path = layers_dir / "reflection.png"
    reflection.save(reflection_path)

    ripple_opacity = float(layers.get("ripple_opacity", 0.0))
    ripple_info = None
    ripple_path: Path | None = None
    if ripple_opacity > 0:
        water_alpha_half = water_alpha.resize(half_size, Image.LANCZOS)
        ripple_path = layers_dir / "water_ripple.png"
        ripple_info = make_ripple_layer(base_half, water_alpha_half, layers, ripple_path)

    plate_opacity = float(layers.get("plate_opacity", 0.0))
    plate_info = None
    if plate_opacity > 0:
        plate_info = make_plate_frames(
            base_half, gray_half, layers, layers_dir / "plate_frames",
            args.duration, FPS,
        )

    texture_path = layers_dir / "texture_raw_paper.png"
    texture = make_texture("raw_paper", texture_path, seed=int(layers.get("texture_seed", 7)))

    duration = args.duration
    cloud_px = float(layers.get("cloud_shift_px", 12))
    cloud_period = float(layers.get("cloud_period_s", 16))
    cloud_mode = str(layers.get("cloud_mode", "sine"))
    water_px = float(layers.get("water_shift_px", 2.5))
    water_period = float(layers.get("water_period_s", 9))
    boat_mode = str(layers.get("boat_mode", "anchored_boat"))
    if boat_mode == "drifting_boat":
        boat_speed = float(layers.get("drifting_boat_speed_px_per_s", 3.0))
    else:
        boat_speed = float(layers.get("boat_speed_px_per_s", 0.6))
    boat_px = boat_speed * duration
    boat_bob = float(layers.get("boat_bob_px", 1.2))
    boat_period = float(layers.get("boat_period_s", 6))
    texture_opacity = float(layers.get("texture_opacity", preset.compositing.texture.opacity))

    inputs: list[str] = ["-framerate", str(FPS), "-loop", "1", "-i", str(base_path)]
    index = 1
    water_idx = index
    inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(water_path)]
    index += 1
    ripple_idx = None
    if ripple_info is not None:
        ripple_idx = index
        inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(ripple_path)]
        index += 1
    boat_idx = index
    inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(boat_path)]
    index += 1
    reflection_idx = index
    inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(reflection_path)]
    index += 1
    cloud_idx = index
    if cloud_is_sequence:
        inputs += ["-framerate", str(FPS), "-i",
                   str(layers_dir / "cloud_frames" / "cloud_%04d.png")]
    else:
        inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(cloud_path)]
    index += 1
    plate_idx = None
    if plate_info is not None:
        plate_idx = index
        inputs += ["-framerate", str(FPS), "-i",
                   str(layers_dir / "plate_frames" / "plate_%04d.png")]
        index += 1
    texture_idx = index
    inputs += ["-framerate", str(FPS), "-loop", "1", "-i", str(texture_path)]
    index += 1
    audio_idx = index
    inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"]

    if cloud_mode == "one_way_ease":
        cloud_x = f"{cloud_px:.3f}*(1-cos((t/{duration:.3f})*PI/2))"
    else:
        cloud_x = f"{-cloud_px:.3f}+{cloud_px:.3f}*sin(2*PI*t/{cloud_period:.3f})"

    graph = "[0:v]format=rgb24[base];"
    current = "base"
    graph += (
        f"[{current}][{water_idx}:v]overlay="
        f"x='{-water_px:.3f}+{water_px:.3f}*sin(2*PI*t/{water_period:.3f})':"
        "y=0:format=auto[w1];"
    )
    current = "w1"
    if ripple_info is not None:
        ripple_amp = float(layers.get("ripple_amplitude_px", 12))
        ripple_period = float(layers.get("ripple_period_s", 3.333))
        graph += (
            f"[{current}][{ripple_idx}:v]overlay="
            f"x='{ripple_amp:.3f}*sin(2*PI*t/{ripple_period:.3f})':"
            "y=0:format=auto[w2];"
        )
        current = "w2"
    boat_y = f"floor({boat_bob:.3f}*sin(2*PI*t/{boat_period:.3f})+0.5)"
    graph += (
        f"[{current}][{boat_idx}:v]overlay="
        f"x='floor({boat_px:.3f}*t/{duration:.3f})':y='{boat_y}':format=auto[w3];"
    )
    current = "w3"
    graph += (
        f"[{current}][{reflection_idx}:v]overlay="
        f"x='floor({boat_px:.3f}*t/{duration:.3f})':y='{boat_y}':format=auto[w4];"
    )
    current = "w4"
    graph += f"[{cloud_idx}:v]scale={W}:{H}:flags=bicubic[cloud];"
    graph += f"[{current}][cloud]overlay=x='{cloud_x}':y=0:format=auto[w5];"
    current = "w5"
    if plate_info is not None:
        plate_shift = float(layers.get("plate_shift_px", 96))
        plate_x = f"{plate_shift:.3f}*(1-cos((t/{duration:.3f})*PI/2))"
        graph += f"[{plate_idx}:v]scale={W}:{H}:flags=bicubic[plate];"
        graph += f"[{current}][plate]overlay=x='{plate_x}':y=0:format=auto[w6];"
        current = "w6"
    graph += (
        f"[{current}][{texture_idx}:v]blend=all_mode=overlay:"
        f"all_opacity={texture_opacity:.2f},format=yuv420p[outv]"
    )
    output = out_dir / "final_9x16.mp4"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        *inputs,
        "-filter_complex", graph,
        "-map", "[outv]", "-map", f"{audio_idx}:a",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(output),
    ]
    run(cmd)

    video_check = check_video(output, expected_width=W, expected_height=H)
    frames = sample_frames(output, out_dir / "frames", duration)
    for name, at in (("25pct", duration * 0.25), ("75pct", duration * 0.75)):
        path = out_dir / "frames" / f"frame_{name}.png"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(output),
             "-frames:v", "1", str(path)])
        frames.append({"name": name, "at_seconds": round(at, 3), **check_image(path),
                       "path": rel(path), "sha256": sha256(path)})
    black = black_frames(output)

    manifest = {
        "stage": "pipeline_a_validation",
        "style_id": preset.id,
        "style_name": preset.name,
        "source": {"path": rel(source), "sha256": sha256(source)},
        "static_quality": {
            "path": rel((ROOT / args.static_quality)),
            "sha256": sha256((ROOT / args.static_quality)),
            "overall_status": quality.get("overall_status"),
        },
        "layers": layers,
        "cloud": ({**cloud_info, "mode": cloud_mode, "shift_px": cloud_px}
                  if cloud_info else {"mode": cloud_mode, "shift_px": cloud_px, "static": True}),
        "ripple": ripple_info,
        "plate": plate_info,
        "boat_mode": boat_mode,
        "boat_speed_px_per_s": boat_speed,
        "boat_shift_px": round(boat_px, 3),
        "layers_dir": rel(layers_dir),
        "layer_hashes": {
            p.name: sha256(p) for p in sorted(layers_dir.glob("*.png"))
        },
        "texture": texture,
        "duration_seconds": duration,
        "fps": FPS,
        "size": [W, H],
        "argv": cmd,
        "outputs": {"final": rel(output), "final_sha256": sha256(output),
                    "bytes": output.stat().st_size},
        "video_check": video_check,
        "sample_frames": frames,
        "black_frames": black,
        "human_review": {"status": "PENDING",
                         "note": "云气、水面、孤舟与纸本质感需要人工看片"},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"build": rel(out_dir), "final": rel(output),
                      "video_check": video_check["status"],
                      "frames": len(frames), "black_segments": len(black["black_segments"])},
                     ensure_ascii=False))
    return 0 if video_check["status"] == "PASS" and not black["black_segments"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
