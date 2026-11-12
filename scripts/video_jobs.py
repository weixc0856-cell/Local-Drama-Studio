"""Create Wan I2V jobs for ProductionScript shots with ``type=video``.

FLUX stills are generated first (``build_jobs``); those stills are the structural
anchor for Wan. This CLI never invents a video when the keyframe is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drama_studio.production import ProductionError, build_video_jobs
from drama_studio.script_engine import ProductionScript


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--keyframes", required=True, help="directory containing <shot_id>/*.png")
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", default=None, help="comma-separated shot ids")
    parser.add_argument("--frames", type=int, default=73)
    parser.add_argument("--width", type=int, default=576)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--cfg", type=float, default=5.0)
    parser.add_argument("--shift", type=float, default=8.0)
    parser.add_argument("--seed-base", type=int, default=9200)
    args = parser.parse_args()
    try:
        script = ProductionScript.model_validate(json.loads((ROOT / args.script).read_text(encoding="utf-8")))
        only = {item.strip() for item in (args.only or "").split(",") if item.strip()} or None
        result = build_video_jobs(
            script,
            root=ROOT,
            episode_root=(ROOT / args.script).parent,
            keyframes_dir=ROOT / args.keyframes,
            jobs_path=ROOT / args.out,
            only=only,
            seed_base=args.seed_base,
            width=args.width,
            height=args.height,
            frames=args.frames,
            steps=args.steps,
            cfg=args.cfg,
            shift=args.shift,
        )
    except (ProductionError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
