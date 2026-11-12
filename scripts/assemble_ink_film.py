"""Assemble the 24-shot ink film once every Wan clip exists.

Pipeline: frames_to_clip -> reference_hybrid (stretch) -> r3_build -> quality.
A missing clip is a hard failure; it never falls back to a still.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = output_path("experiments/ink_dream")
IDS = [f"ink{i:02d}" for i in range(1, 25)]


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="experiments/ink_dream/renders_24")
    args = parser.parse_args()
    clips = BASE / "clips24"
    clips.mkdir(parents=True, exist_ok=True)
    for sid in IDS:
        target = clips / f"{sid}.mp4"
        if target.is_file():
            continue
        source = BASE / "wan24" / sid
        frames = sorted(source.glob("*.png")) if source.is_dir() else []
        if not frames:
            raise SystemExit(f"{sid}: missing Wan frames")
        run([sys.executable, "scripts/frames_to_clip.py", "--frames", str(source),
             "--out", str(target), "--fps", "24"])
    run([sys.executable, "scripts/reference_hybrid.py",
         "--segments", str(BASE / "segments_24.json"), "--clips", str(clips),
         "--out", str(BASE / "segments_24_hybrid.json"),
         "--ready-dir", str(clips / "ready"), "--mode", "stretch"])
    out = output_path(args.out)
    run([sys.executable, "scripts/r3_build.py",
         "--segments", str(BASE / "segments_24_hybrid.json"),
         "--audio", str(BASE / "audio_24.json"), "--out", str(out),
         "--audio-timeline", str(BASE / "audio_timeline_24.json"),
         "--audio-assets", "assets/audio/manifest.json"])
    run([sys.executable, "-m", "drama_studio.quality",
         "--manifest", str(out / "build_manifest.json")])
    manifest = json.loads((out / "build_manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out),
                      "final": manifest.get("outputs", {}).get("final")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
