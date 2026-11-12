"""Per-shot static quality gate for the film chain.

The episode chain already refuses to animate a still without a
``static_quality.json``. The film chain had no equivalent, so a deformed
keyframe could go straight into motion. This module runs the existing
``scripts/static_quality.py`` per shot, records the objective metrics and the
PENDING semantic checklist, and only blocks on an objective FAIL.

A PENDING semantic checklist is not a pass: it is the H2 human gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .assets import latest_output
from .config import MotionSettings, motion_preset_for
from .schemas import Storyboard


class StaticGateError(RuntimeError):
    pass


def _gate_path(project_root: Path, shot_id: str) -> Path:
    return project_root / "work" / "static" / shot_id / "static_quality.json"


def run_static_gate(
    project_root: Path,
    storyboard: Storyboard,
    *,
    root: Path,
    style_id: str | None,
    force: bool = False,
) -> dict[str, Any]:
    # The static gate uses the same two pipeline names as styles.yaml.
    preset = motion_preset_for(style_id, MotionSettings())
    if preset not in ("ink_wash", "court_green_fine_line"):
        return {"status": "SKIPPED", "reason": f"no static checklist for style {style_id!r}", "shots": {}}
    results: dict[str, Any] = {}
    for shot in storyboard.shots:
        image = latest_output(project_root / "assets" / "keyframes" / shot.shot_id,
                              shot.shot_id, ".png")
        if image is None:
            results[shot.shot_id] = {"status": "MISSING", "reason": "no keyframe"}
            continue
        out = _gate_path(project_root, shot.shot_id)
        if out.is_file() and not force:
            payload = json.loads(out.read_text(encoding="utf-8"))
            results[shot.shot_id] = {
                "status": payload.get("overall_status"),
                "report": str(out),
                "reused": True,
            }
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable, str(root / "scripts" / "static_quality.py"),
            "--image", str(image), "--style", preset, "--out", str(out),
        ]
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if not out.is_file():
            raise StaticGateError(
                f"{shot.shot_id}: static gate produced no report\n{proc.stderr[-1000:]}")
        payload = json.loads(out.read_text(encoding="utf-8"))
        results[shot.shot_id] = {
            "status": payload.get("overall_status"),
            "report": str(out),
            "metrics": payload.get("objective"),
            "manual": payload.get("manual_checks"),
            "reused": False,
        }
    failed = [shot for shot, item in results.items() if item.get("status") == "FAIL"]
    if failed:
        raise StaticGateError(f"static gate FAIL: {failed}")
    return {"status": "RECORDED", "preset": preset, "shots": results}
