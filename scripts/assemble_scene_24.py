"""Assemble the 24-shot 2-minute scene film after all Wan clips exist.

This is intentionally a thin orchestrator around the verified tools:
``frames_to_clip.py`` -> ``reference_hybrid.py`` -> ``r3_build.py`` -> quality.
It never fabricates a missing clip; a missing shot is a hard failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = output_path("experiments/shinkai_scene")
IDS = [f"s{i:02d}" for i in range(1, 25)]
EXISTING = {
    "s02": "scene_01.mp4", "s10": "scene_02.mp4", "s11": "scene_03.mp4",
    "s12": "scene_04.mp4", "s16": "scene_05.mp4", "s21": "scene_06.mp4",
}


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="experiments/shinkai_scene/renders_24")
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
         "--ready-dir", str(BASE / "clips24" / "ready"), "--mode", "stretch"])
    out = output_path(args.out)
    run([sys.executable, "scripts/r3_build.py",
         "--segments", str(BASE / "segments_24_hybrid.json"),
         "--audio", str(BASE / "audio_24.json"), "--out", str(out),
         "--audio-timeline", str(BASE / "audio_timeline_24.json"),
         "--audio-assets", "assets/audio/manifest.json"])
    run([sys.executable, "-m", "drama_studio.quality",
         "--manifest", str(out / "build_manifest.json")])
    manifest = json.loads((out / "build_manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "final": manifest.get("outputs", {}).get("final")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
