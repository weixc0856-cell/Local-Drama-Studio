"""Encode Wan frame sequences to MP4 and compute basic quality metrics.

No new dependencies: Pillow + ffmpeg/ffprobe. Metrics are descriptive:
- consecutive-frame difference (proxy for flicker / sudden changes)
- brightness per frame (detect black or blown frames)
- spike count above mean + 3*std

Human review remains authoritative for deformation, artifacts and motion quality.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

FRAME_RE = re.compile(r"^(.*)_(\d{5})_?\.png$", re.IGNORECASE)


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--out-name", default="clip.mp4")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    frames = sorted(p for p in run_dir.glob("*.png") if FRAME_RE.match(p.name))
    if not frames:
        raise SystemExit(f"no frame PNGs in {run_dir}")
    match = FRAME_RE.match(frames[0].name)
    assert match
    prefix, first = match.group(1), int(match.group(2))
    expected = list(range(first, first + len(frames)))
    actual = [int(FRAME_RE.match(p.name).group(2)) for p in frames]
    contiguous = actual == expected

    out_mp4 = run_dir / args.out_name
    pattern = f"{prefix}_%05d_.png"
    encode = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-framerate", str(args.fps), "-start_number", str(first),
         "-i", str(run_dir / pattern), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-movflags", "+faststart", str(out_mp4)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(out_mp4), "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ) if out_mp4.is_file() else None
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,nb_frames,duration", "-of", "json", str(out_mp4)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ) if out_mp4.is_file() else None

    diffs: list[float] = []
    brightness: list[float] = []
    prev = None
    sample_size = (192, 108)
    for path in frames:
        im = Image.open(path).convert("RGB").resize(sample_size, Image.BILINEAR)
        brightness.append(round(ImageStat.Stat(im).mean[0] + ImageStat.Stat(im).mean[1] + ImageStat.Stat(im).mean[2], 2) / 3)
        if prev is not None:
            diffs.append(round(sum(ImageStat.Stat(ImageChops.difference(prev, im)).mean) / 3, 3))
        prev = im

    mean_diff = round(sum(diffs) / len(diffs), 3) if diffs else 0.0
    if diffs:
        var = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
        std_diff = var ** 0.5
    else:
        std_diff = 0.0
    threshold = mean_diff + 3 * std_diff
    quality = {
        "run_dir": str(run_dir),
        "frame_count": len(frames),
        "frame_numbers_contiguous": contiguous,
        "frame_first": first,
        "fps": args.fps,
        "duration_seconds": round(len(frames) / args.fps, 3),
        "clip": str(out_mp4) if out_mp4.is_file() else None,
        "clip_sha256": sha256(out_mp4) if out_mp4.is_file() else None,
        "encode_returncode": encode.returncode,
        "encode_stderr": encode.stderr.strip()[-1000:],
        "decode_returncode": decode.returncode if decode else None,
        "decode_stderr": (decode.stderr.strip()[-1000:] if decode else None),
        "ffprobe": json.loads(probe.stdout) if probe and probe.returncode == 0 else None,
        "mean_consecutive_diff": mean_diff,
        "std_consecutive_diff": round(std_diff, 3),
        "max_consecutive_diff": max(diffs) if diffs else 0.0,
        "flicker_spike_threshold": round(threshold, 3),
        "flicker_spikes": sum(1 for d in diffs if d > threshold) if diffs else 0,
        "brightness_mean": round(sum(brightness) / len(brightness), 2) if brightness else 0,
        "brightness_min": min(brightness) if brightness else 0,
        "brightness_max": max(brightness) if brightness else 0,
        "black_frames_below_5": sum(1 for b in brightness if b < 5),
        "first_last_diff": round(sum(ImageStat.Stat(ImageChops.difference(
            Image.open(frames[0]).convert("RGB").resize(sample_size, Image.BILINEAR),
            Image.open(frames[-1]).convert("RGB").resize(sample_size, Image.BILINEAR))).mean) / 3, 3),
    }
    (run_dir / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: quality[k] for k in (
        "frame_count", "frame_numbers_contiguous", "encode_returncode", "decode_returncode",
        "mean_consecutive_diff", "max_consecutive_diff", "flicker_spikes",
        "brightness_min", "black_frames_below_5", "duration_seconds")}, ensure_ascii=False))
    return 0 if encode.returncode == 0 and (decode is None or decode.returncode == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
