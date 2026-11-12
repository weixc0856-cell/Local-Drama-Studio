"""Read/write API for Script-to-Film projects.

The workspace UI reads film projects from disk (project.json + storyboard.json),
not from workspace.db. Edits are validated with the film schemas before writing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ..config import find_project_root
from ..film.assets import latest_output, resolve_asset
from ..film.project import STORYBOARD_FILE, load_project, validate_project
from ..film.status import film_status
from ..film.schemas import ShotSpec, Storyboard
from ..style_engine import get_pack, list_packs

router = APIRouter(prefix="/api/film", tags=["film"])


def _root() -> Path:
    return find_project_root()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _film_projects(root: Path) -> list[Path]:
    base = root / "projects"
    if not base.is_dir():
        return []
    return sorted(base.glob("*/project.json"))


def _project_dir(root: Path, project_id: str) -> Path:
    """Resolve one project directory, refusing anything that escapes projects/."""
    name = project_id.strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise HTTPException(status_code=404, detail=f"film project not found: {project_id}")
    return root / "projects" / name


def _progress(directory: Path) -> dict[str, Any]:
    meta = _read_json(directory / "project.json")
    storyboard_path = directory / STORYBOARD_FILE
    storyboard = _read_json(storyboard_path) if storyboard_path.is_file() else {"shots": []}
    shots = storyboard.get("shots") or []
    keyframes = clips = frames = 0
    cover = None
    for shot in shots:
        shot_id = str(shot.get("shot_id", ""))
        if not shot_id:
            continue
        keyframe = latest_output(directory / "assets" / "keyframes" / shot_id, shot_id, ".png")
        asset = resolve_asset(directory, shot_id)
        if keyframe:
            keyframes += 1
            cover = cover or keyframe
        if asset and asset.kind == "video":
            clips += 1
            cover = (asset.path, 10) if asset.path else cover
        elif asset and asset.kind == "image_sequence":
            frames += 1
    if isinstance(cover, tuple):
        cover = cover[0]
    audio_dir = directory / "assets" / "audio"
    audio = len(list(audio_dir.glob("N*.wav"))) if audio_dir.is_dir() else 0
    narration_path = directory / "narration.json"
    narration = len(_read_json(narration_path).get("segments", [])) if narration_path.is_file() else 0
    timeline = (directory / "timeline.json").is_file()
    finals = sorted(directory.glob("renders/build-*/final_9x16.mp4")) if (directory / "renders").is_dir() else []
    final = bool(finals)
    return {
        "shots": len(shots),
        "keyframes": keyframes,
        "clips": clips,
        "audio": audio,
        "narration": narration,
        "stages": {
            "script": (directory / "screenplay.json").is_file(),
            "storyboard": storyboard_path.is_file(),
            "keyframes": f"{keyframes}/{len(shots)}" if shots else "0/0",
            "video": f"{clips}/{len(shots)}" if shots else "0/0",
            "frame_runs": f"{frames}/{len(shots)}" if shots else "0/0",
            "voice": f"{audio}/{narration}" if narration else "0/0",
            "edit": timeline,
            "final": final,
        },
        "title": meta.get("title", directory.name),
        "aspect_ratio": meta.get("aspect_ratio", "9:16"),
        "target_duration_seconds": meta.get("target_duration_seconds"),
        "style_id": (meta.get("visual") or {}).get("style_id"),
        "cover": str(cover.relative_to(directory.parent.parent)).replace("\\", "/") if cover else None,
        "updated_at": max((p.stat().st_mtime for p in directory.glob("*.json")), default=0),
    }


@router.get("/projects")
def list_film_projects() -> dict[str, Any]:
    root = _root()
    items = []
    for path in _film_projects(root):
        try:
            items.append({"project_id": path.parent.name, **_progress(path.parent)})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            items.append({"project_id": path.parent.name, "error": str(exc)})
    return {"projects": items}


@router.get("/projects/{project_id}")
def get_film_project(project_id: str) -> dict[str, Any]:
    root = _root()
    directory = _project_dir(root, project_id)
    if not (directory / "project.json").is_file():
        raise HTTPException(status_code=404, detail=f"film project not found: {project_id}")
    project = load_project(root, project_id)
    payload: dict[str, Any] = {
        "project_id": project_id,
        "meta": _read_json(directory / "project.json"),
        "progress": _progress(directory),
        "validation": validate_project(root, project_id),
        "narration": project.narration.model_dump(mode="json") if project.narration else None,
        "storyboard": project.storyboard.model_dump(mode="json") if project.storyboard else None,
        "timeline": _read_json(directory / "timeline.json")
        if (directory / "timeline.json").is_file() else None,
    }
    assets = {}
    if project.storyboard:
        for shot in project.storyboard.shots:
            keyframe = latest_output(directory / "assets" / "keyframes" / shot.shot_id, shot.shot_id, ".png")
            asset = resolve_asset(directory, shot.shot_id)
            clip = asset.path if asset and asset.kind == "video" else None
            assets[shot.shot_id] = {
                "keyframe": str(keyframe.relative_to(root)).replace("\\", "/") if keyframe else None,
                "clip": str(clip.relative_to(root)).replace("\\", "/") if clip else None,
                "kind": asset.kind if asset else None,
                "frames": asset.frame_count if asset and asset.kind == "image_sequence" else 0,
            }
    payload["assets"] = assets
    if project.style_id:
        try:
            pack = get_pack(root, project.style_id)
            payload["style"] = {
                "id": pack.identity.id, "name": pack.identity.name,
                "version": pack.identity.version, "status": pack.identity.status,
            }
        except KeyError:
            payload["style"] = {"id": project.style_id, "missing": True}
    return payload


class ShotPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str | None = None
    narration_ids: list[str] | None = None
    duration_seconds: float | None = None
    shot_size: str | None = None
    camera_move: str | None = None
    camera_angle: str | None = None
    lens_mm: int | None = None
    dof: str | None = None
    foreground: str | None = None
    midground: str | None = None
    background: str | None = None
    motion_primary: str | None = None
    secondary: list[str] | None = None
    character_in_frame: bool | None = None
    keyframe_note: str | None = None


@router.patch("/projects/{project_id}/storyboard/{shot_id}")
def patch_shot(project_id: str, shot_id: str, patch: ShotPatch) -> dict[str, Any]:
    root = _root()
    directory = _project_dir(root, project_id)
    path = directory / STORYBOARD_FILE
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"storyboard not found for {project_id}")
    data = _read_json(path)
    shots = data.get("shots") or []
    target = next((item for item in shots if item.get("shot_id") == shot_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"shot not found: {shot_id}")

    updated = dict(target)
    changes = patch.model_dump(exclude_none=True)
    if "scene_id" in changes:
        updated["scene_id"] = changes["scene_id"]
    if "narration_ids" in changes:
        updated["narration_ids"] = changes["narration_ids"]
    if "duration_seconds" in changes:
        updated["duration_seconds"] = changes["duration_seconds"]
    if "shot_size" in changes:
        updated["shot_size"] = changes["shot_size"]
    if "camera_move" in changes:
        updated.setdefault("camera", {})["move"] = changes["camera_move"]
    if "camera_angle" in changes:
        updated.setdefault("camera", {})["angle"] = changes["camera_angle"]
    if "lens_mm" in changes:
        updated.setdefault("camera", {})["lens_mm"] = changes["lens_mm"]
    if "dof" in changes:
        updated.setdefault("camera", {})["dof"] = changes["dof"]
    for key in ("foreground", "midground", "background"):
        if key in changes:
            updated.setdefault("layers", {})[key] = changes[key]
    if "motion_primary" in changes:
        updated.setdefault("motion", {})["primary"] = changes["motion_primary"]
    if "secondary" in changes:
        updated.setdefault("motion", {})["secondary"] = changes["secondary"]
    if "character_in_frame" in changes:
        updated["character_in_frame"] = changes["character_in_frame"]
    if "keyframe_note" in changes:
        updated["keyframe_note"] = changes["keyframe_note"]

    try:
        validated = ShotSpec.model_validate(updated)
        storyboard = Storyboard.model_validate({**data, "shots": [
            validated.model_dump(mode="json") if item.get("shot_id") == shot_id else item
            for item in shots
        ]})
    except Exception as exc:  # validation errors surface as 422 for the UI
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    path.write_text(json.dumps(storyboard.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return {"shot": validated.model_dump(mode="json"), "storyboard": storyboard.model_dump(mode="json")}


@router.get("/projects/{project_id}/status")
def get_film_status(project_id: str) -> dict[str, Any]:
    root = _root()
    directory = _project_dir(root, project_id)
    if not (directory / "project.json").is_file():
        raise HTTPException(status_code=404, detail=f"film project not found: {project_id}")
    return film_status(load_project(root, project_id), root)


@router.get("/styles/packs")
def style_packs() -> dict[str, Any]:
    root = _root()
    packs = []
    for pack in list_packs(root):
        board = root / "config" / "style_packs" / pack.identity.group / pack.identity.id.split(".")[1] / "reference_board"
        manifest = board / "manifest.json"
        board_status = "NONE"
        board_count = 0
        if manifest.is_file():
            try:
                data = _read_json(manifest)
                board_status = data.get("status", "PENDING_REVIEW")
                board_count = len(list((board / "candidates").glob("[0-9][0-9]/*.png")))
            except (json.JSONDecodeError, OSError):
                board_status = "UNKNOWN"
        packs.append({
            "id": pack.identity.id, "name": pack.identity.name, "group": pack.identity.group,
            "version": pack.identity.version, "status": pack.identity.status,
            "summary": pack.identity.summary,
            "reference_board": {"status": board_status, "samples": board_count},
        })
    return {"packs": packs}


@router.get("/styles/packs/{style_id}")
def style_pack(style_id: str) -> dict[str, Any]:
    root = _root()
    try:
        pack = get_pack(root, style_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"pack": pack.model_dump(mode="json")}
