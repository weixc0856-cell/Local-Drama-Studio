"""Project loading and validation for the Script-to-Film layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel

from ..paths import config_root
from .continuity import Issue, check_continuity
from .schemas import Narration, Screenplay, SourceText, Storyboard, VisualBible

PROJECT_FILE = "project.json"
SOURCE_FILE = "source.json"
SCREENPLAY_FILE = "screenplay.json"
NARRATION_FILE = "narration.json"
BIBLE_FILE = "visual_bible.yaml"
STORYBOARD_FILE = "storyboard.json"
TIMELINE_FILE = "timeline.json"


@dataclass
class FilmProject:
    root: Path
    project_id: str
    source: SourceText | None = None
    screenplay: Screenplay | None = None
    narration: Narration | None = None
    bible: VisualBible | None = None
    storyboard: Storyboard | None = None
    style_id: str | None = None


def project_dir(root: Path, project_id: str) -> Path:
    return root / "projects" / project_id


def load_json_model(path: Path, model: type[BaseModel]) -> BaseModel:
    if not path.is_file():
        raise FileNotFoundError(f"missing {path.name} at {path}")
    return model.model_validate(json.loads(path.read_text(encoding="utf-8")))


def write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_project(root: Path, project_id: str) -> FilmProject:
    directory = project_dir(root, project_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"project directory not found: {directory}")

    project_file = directory / PROJECT_FILE
    if not project_file.is_file():
        raise FileNotFoundError(f"missing {PROJECT_FILE} at {project_file}")
    meta = json.loads(project_file.read_text(encoding="utf-8"))
    if meta.get("project_id") != project_id:
        raise ValueError(f"{PROJECT_FILE} project_id {meta.get('project_id')!r} != {project_id!r}")

    visual = meta.get("visual") or {}
    result = FilmProject(root=root, project_id=project_id, style_id=visual.get("style_id"))

    if (directory / SOURCE_FILE).is_file():
        result.source = load_json_model(directory / SOURCE_FILE, SourceText)  # type: ignore[assignment]
    if (directory / SCREENPLAY_FILE).is_file():
        result.screenplay = load_json_model(directory / SCREENPLAY_FILE, Screenplay)  # type: ignore[assignment]
    if (directory / NARRATION_FILE).is_file():
        result.narration = load_json_model(directory / NARRATION_FILE, Narration)  # type: ignore[assignment]
    bible_path = directory / BIBLE_FILE
    if bible_path.is_file():
        result.bible = VisualBible.model_validate(yaml.safe_load(bible_path.read_text(encoding="utf-8")))
    if (directory / STORYBOARD_FILE).is_file():
        result.storyboard = load_json_model(directory / STORYBOARD_FILE, Storyboard)  # type: ignore[assignment]

    for loaded, name, expected in (
        (result.source, SOURCE_FILE, project_id),
        (result.screenplay, SCREENPLAY_FILE, project_id),
        (result.narration, NARRATION_FILE, project_id),
        (result.bible, BIBLE_FILE, project_id),
        (result.storyboard, STORYBOARD_FILE, project_id),
    ):
        if loaded is not None and getattr(loaded, "project_id", expected) != expected:
            raise ValueError(f"{name}: project_id does not match {expected!r}")

    return result


def validate_project(root: Path, project_id: str) -> dict:
    """Load every file and run cross-file checks; never raises for content issues."""
    issues: list[Issue] = []
    try:
        project = load_project(root, project_id)
    except (FileNotFoundError, ValueError) as exc:
        return {"ok": False, "issues": [{"level": "error", "code": "load", "shot_id": "-", "message": str(exc)}]}

    if project.storyboard is None:
        issues.append(Issue("error", "storyboard_missing", "-", "storyboard.json is required"))
    else:
        issues.extend(check_continuity(project.storyboard, project.narration))
    if project.narration is None:
        issues.append(Issue("warning", "narration_missing", "-", "narration.json is missing; voice stage will fail"))
    else:
        from .text import TextCleanError, clean_spoken_text

        for segment in project.narration.segments:
            try:
                audit = clean_spoken_text(segment.text, language=project.narration.language)
            except TextCleanError as exc:
                issues.append(Issue("error", "spoken_text_empty", segment.id, str(exc)))
                continue
            if audit.removed or audit.latin_removed:
                issues.append(Issue(
                    "warning", "spoken_text_cleaned", segment.id,
                    f"TTS input will be cleaned: removed={audit.removed}, latin={audit.latin_removed}"))
    if project.bible is None:
        issues.append(Issue("error", "bible_missing", "-", "visual_bible.yaml is required"))
    if project.style_id:
        from ..style_engine import get_pack
        try:
            get_pack(config_root(root), project.style_id)
        except KeyError as exc:
            issues.append(Issue("error", "style_unknown", "-", str(exc)))

    payload = {
        "ok": not any(item.level == "error" for item in issues),
        "project_id": project_id,
        "shots": len(project.storyboard.shots) if project.storyboard else 0,
        "issues": [
            {"level": item.level, "code": item.code, "shot_id": item.shot_id, "message": item.message}
            for item in issues
        ],
    }
    return payload
