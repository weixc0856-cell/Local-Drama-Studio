"""Derive film production state from real files, never from intention.

The storyboard carries ``generation.status``, but nothing used to write it back,
so every shot stayed ``planned`` forever. This module computes the state from
artefacts (keyframe, motion/Wan clip, build, quality report, human review) and
records it in ``qc/film_state.json``. Human approvals live in
``qc/reviews.json`` and are the only way a shot reaches an approved state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from drama_studio.application.film.assets import resolve_asset
from drama_studio.domain.film.schemas import ShotStatus, Storyboard

ReviewKind = Literal["keyframe", "video", "final"]
REVIEWS = "reviews.json"
STATE = "film_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_reviews(project_root: Path) -> dict[str, Any]:
    return _read(project_root / "qc" / REVIEWS, {"schema_version": "1.0"})


def record_review(
    project_root: Path,
    *,
    kind: ReviewKind,
    decision: Literal["approve", "reject"],
    shot_id: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    reviews = load_reviews(project_root)
    bucket = reviews.setdefault(f"{kind}s", {})
    key = shot_id or "film"
    bucket[key] = {
        "decision": decision,
        "note": note,
        "at": _now(),
    }
    path = project_root / "qc" / REVIEWS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return reviews


def _approved(reviews: dict[str, Any], kind: ReviewKind, shot_id: str | None) -> bool:
    bucket = reviews.get(f"{kind}s") or {}
    key = shot_id or "film"
    return (bucket.get(key) or {}).get("decision") == "approve"


def _final_status(project_root: Path) -> tuple[str | None, str | None]:
    candidates = sorted(project_root.glob("renders/build-*/build_manifest.json"),
                        key=lambda item: item.stat().st_mtime)
    if not candidates:
        return None, None
    latest = candidates[-1]
    manifest = _read(latest, {})
    final = (manifest.get("outputs") or {}).get("final")
    quality_path = latest.parent / "quality_report.json"
    quality_status = _read(quality_path, {}).get("status")
    return final, quality_status


def shot_state(project_root: Path, shot_id: str, reviews: dict[str, Any]) -> tuple[ShotStatus, dict[str, Any]]:
    asset = resolve_asset(project_root, shot_id)
    keyframe = (project_root / "assets" / "keyframes" / shot_id).is_dir() and bool(
        list((project_root / "assets" / "keyframes" / shot_id).glob(f"{shot_id}_*.png")))
    gate_path = project_root / "work" / "static" / shot_id / "static_quality.json"
    gate = _read(gate_path, {}) if gate_path.is_file() else {}
    evidence = {
        "keyframe": keyframe,
        "static_status": gate.get("overall_status"),
        "asset_kind": asset.kind if asset else None,
        "asset": str(asset.path) if asset and asset.path else None,
        "keyframe_approved": _approved(reviews, "keyframe", shot_id),
        "video_approved": _approved(reviews, "video", shot_id),
    }
    if not keyframe:
        return ShotStatus.PLANNED, evidence
    if not asset or asset.kind == "image":
        return (ShotStatus.KEYFRAME_APPROVED if evidence["keyframe_approved"]
                else ShotStatus.KEYFRAME_GENERATED), evidence
    if evidence["video_approved"]:
        return ShotStatus.VIDEO_APPROVED, evidence
    return ShotStatus.VIDEO_GENERATED, evidence


def film_status(project: Any, root: Path) -> dict[str, Any]:
    if project.storyboard is None:
        raise ValueError("storyboard.json is required")
    directory = root / "projects" / project.project_id
    reviews = load_reviews(directory)
    shots = []
    for shot in project.storyboard.shots:
        state, evidence = shot_state(directory, shot.shot_id, reviews)
        shots.append({"shot_id": shot.shot_id, "status": state.value, **evidence})
    final, quality_status = _final_status(directory)
    final_approved = _approved(reviews, "final", None)
    if final and quality_status == "PASS" and final_approved:
        overall = "finalized"
    elif final:
        overall = "assembled"
    elif any(item["status"] in ("video_generated", "video_approved") for item in shots):
        overall = "video_generated"
    elif any(item["status"] in ("keyframe_generated", "keyframe_approved") for item in shots):
        overall = "keyframe_generated"
    else:
        overall = "planned"
    payload = {
        "project_id": project.project_id,
        "overall": overall,
        "final": final,
        "quality_status": quality_status,
        "final_approved": final_approved,
        "shots": shots,
        "counts": {
            "keyframes": sum(1 for item in shots if item["keyframe"]),
            "clips": sum(1 for item in shots if item["asset_kind"] in ("video", "image_sequence")),
            "keyframe_approved": sum(1 for item in shots if item["keyframe_approved"]),
            "video_approved": sum(1 for item in shots if item["video_approved"]),
        },
        "updated_at": _now(),
    }
    return payload


def write_state(project_root: Path, payload: dict[str, Any]) -> Path:
    path = project_root / "qc" / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
