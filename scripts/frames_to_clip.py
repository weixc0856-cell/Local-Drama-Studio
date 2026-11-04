"""Assemble a Wan PNG frame sequence into a reviewable MP4.

Wan's verified workflow saves PNG frames; this helper turns one run directory
into ``<out>.mp4`` without changing frame order. It is intentionally not part
of the production renderer: the caller still chooses the shot and duration.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", required=True, help="directory containing PNG frames")
    parser.add_argument("--out", required=True)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    frames = Path(args.frames)
    images = sorted(frames.glob("*.png"))
    if not images:
        raise SystemExit(f"no PNG frames in {frames}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-framerate", str(args.fps),
        "-pattern_type", "glob", "-i", str(frames / "*.png"),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {proc.stderr[-2000:]}")
    print(f"{out} {len(images)} frames @ {args.fps} fps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
