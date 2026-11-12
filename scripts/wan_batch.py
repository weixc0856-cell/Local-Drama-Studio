"""Batch Wan chaining for several shots, resume-friendly.

Each shot uses the same safe 8 GB profile: 448x768, 49 frames per segment,
last-frame chaining, clean-prefix QC. Segment counts adapt to the edit duration:
<= 5.9 s -> 2 segments, >= 6.0 s -> 3 segments.

This is intentionally sequential: one GPU job at a time. Existing chain
manifests with a usable clip are skipped, so an interrupted batch can resume.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drama_studio.application.film.project import load_project  # noqa: E402
from drama_studio.application.film.wan_chain import ChainError, chain_shot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--shots", default="S02,S03,S04,S05,S06,S07,S08")
    parser.add_argument("--frames", type=int, default=49)
    parser.add_argument("--width", type=int, default=448)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--seed-base", type=int, default=7400)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = ROOT
    project = load_project(root, args.project)
    if project.storyboard is None:
        raise SystemExit("storyboard.json is required")
    durations = {shot.shot_id: shot.duration_seconds for shot in project.storyboard.shots}
    shots_by_id = {shot.shot_id: shot for shot in project.storyboard.shots}

    def camera_for(shot_id: str) -> str | None:
        shot = shots_by_id[shot_id]
        layers = " ".join([
            shot.layers.foreground, shot.layers.midground, shot.layers.background,
        ]).lower()
        architecture = ("tower", "pavilion", "eave", "building", "hall", "palace",
                        "楼", "阁", "亭", "宫", "殿", "檐")
        if shot.character_in_frame or any(word in layers for word in architecture):
            return "static"
        return None
    shots = [item.strip() for item in args.shots.split(",") if item.strip()]
    summary = []
    for shot_id in shots:
        directory = root / "projects" / args.project / "shots" / shot_id
        clip = directory / f"{shot_id}_wan.mp4"
        manifest = directory / "chain_manifest.json"
        if clip.is_file() and manifest.is_file() and not args.force:
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if data.get("frames", 0) >= 8 and data.get("source_seconds", 0) > 0:
                    summary.append({"shot": shot_id, "status": "skipped", "seconds": data.get("source_seconds")})
                    print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        segments = 3 if durations.get(shot_id, 5.0) >= 6.5 else 2
        print(json.dumps({"shot": shot_id, "status": "start", "segments": segments,
                          "duration": durations.get(shot_id)}, ensure_ascii=False), flush=True)
        try:
            result = chain_shot(
                project, root, shot_id, segments=segments, frames=args.frames,
                width=args.width, height=args.height, seed_base=args.seed_base,
                camera_override=camera_for(shot_id),
            )
        except ChainError as exc:
            summary.append({"shot": shot_id, "status": "failed", "error": str(exc)[-500:]})
            print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
            return 1
        summary.append({"shot": shot_id, "status": "done",
                        "seconds": result["source_seconds"], "frames": result["frames"]})
        print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
