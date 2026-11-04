r"""Render per-shot camera/local-motion clips and an optional transition sequence.

Input is a motion plan JSON (see ``drama_studio.motion.spec``). Style behaviour
comes from ``config/styles.yaml``; the plan only carries content (still, duration,
motion hint, authored local-motion regions, transitions).

Example:

    .venv\Scripts\python.exe scripts/motion_build.py ^
        --plan projects/<project>/episodes/<episode>/work/motion_shots.json ^
        --out projects/<project>/episodes/<episode>/work/motion
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from drama_studio.config import find_project_root
from drama_studio.motion.render import render_plan
from drama_studio.motion.spec import load_plan

ROOT = find_project_root()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render deterministic motion clips from a plan")
    parser.add_argument("--plan", required=True, help="motion_shots.json")
    parser.add_argument("--out", required=True, help="renders root (a new build-<time> dir is written)")
    parser.add_argument("--no-sequence", action="store_true", help="render clips only, no transition sequence")
    parser.add_argument("--expected-seconds", type=float, default=None,
                        help="fail if the built sequence differs from this duration by more than one frame")
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = ROOT / plan_path
    plan = load_plan(plan_path)
    result = render_plan(plan, root=ROOT, out_root=Path(args.out), build_sequence=not args.no_sequence)
    result["plan"] = str(plan_path.resolve().relative_to(ROOT)).replace("\\", "/")
    if args.expected_seconds is not None:
        measured = result.get("sequence_seconds")
        if measured is None:
            raise SystemExit("--expected-seconds requires a sequence build")
        error = abs(float(measured) - args.expected_seconds)
        if error > (1.0 / plan.fps) + 0.02:
            raise SystemExit(
                f"sequence {measured:.3f}s does not match expected {args.expected_seconds:.3f}s "
                f"(error {error:.3f}s)"
            )
        result["expected_seconds"] = args.expected_seconds
        result["duration_error_seconds"] = round(float(measured) - args.expected_seconds, 3)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
