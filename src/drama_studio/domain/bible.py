"""Character and shot bibles with deterministic continuity checks.

These are *authoring* contracts, not a face-identity model. A character bible
records visual anchors (hair, costume, palette, props) and an optional voice
profile; a shot bible records which anchors a shot carries forward. The checker
can prove that references resolve, styles agree and every scripted shot is
covered. It cannot prove that two generated frames show the same face, and the
report says so explicitly.

The bibles are sidecars next to ``production_script.json``. They do not change
the LLM's ``ProductionScript`` schema and they are not stored in
``workspace.db``: production state stays derivable from files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from drama_studio.domain.voice.profiles import VoiceLibrary, load_library

CHAR_ID = r"^char_\d{3}$"
LOC_ID = r"^loc_\d{3}$"
SHOT_ID = r"^shot_\d{3}$"
PROFILE_ID = r"^[a-z][a-z0-9_]{1,63}$"

CharacterId = Annotated[str, StringConstraints(pattern=CHAR_ID)]

CheckStatus = Literal["PASS", "FAIL", "SKIPPED"]


class StoryBibleError(RuntimeError):
    pass


class CharacterAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_id: str = Field(pattern=CHAR_ID)
    name: str = Field(min_length=1, max_length=40)
    visual_anchors: list[str] = Field(min_length=1, max_length=12)
    costume: str = Field(default="", max_length=300)
    palette: list[str] = Field(default_factory=list, max_length=8)
    props: list[str] = Field(default_factory=list, max_length=12)
    voice_profile_id: str | None = Field(default=None, pattern=PROFILE_ID)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _anchors_are_usable(self) -> "CharacterAnchor":
        seen: set[str] = set()
        for anchor in self.visual_anchors:
            text = anchor.strip()
            if len(text) < 2:
                raise ValueError(f"{self.character_id}: visual anchors must be descriptive")
            if text in seen:
                raise ValueError(f"{self.character_id}: duplicate visual anchor {text!r}")
            seen.add(text)
        return self


class CharacterBible(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    style_id: str | None = Field(default=None, max_length=80)
    characters: list[CharacterAnchor] = Field(min_length=1)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _unique_ids(self) -> "CharacterBible":
        ids = [c.character_id for c in self.characters]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate character_id in character bible")
        return self


class ShotContinuity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(pattern=SHOT_ID)
    index: int = Field(ge=1, le=999)
    location_id: str | None = Field(default=None, pattern=LOC_ID)
    character_ids: list[CharacterId] = Field(default_factory=list)
    wardrobe_state: str = Field(default="", max_length=300)
    time_of_day: str = Field(default="", max_length=40)
    props: list[str] = Field(default_factory=list, max_length=20)
    axis: str = Field(default="", max_length=120)
    continuity_notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _id_matches_index(self) -> "ShotContinuity":
        expected = f"shot_{self.index:03d}"
        if self.shot_id != expected:
            raise ValueError(f"shot_id {self.shot_id!r} does not match index {self.index}")
        if len(set(self.character_ids)) != len(self.character_ids):
            raise ValueError(f"{self.shot_id}: duplicate character_ids")
        return self


class ShotBible(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    style_id: str | None = Field(default=None, max_length=80)
    shots: list[ShotContinuity] = Field(min_length=1)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _contiguous(self) -> "ShotBible":
        ids = [s.shot_id for s in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate shot_id in shot bible")
        indexes = [s.index for s in self.shots]
        if indexes != list(range(1, len(indexes) + 1)):
            raise ValueError("shot bible indexes must be contiguous starting at 1")
        return self


def _load_yaml(path: Path, model: type[BaseModel], label: str) -> BaseModel:
    path = Path(path)
    if not path.is_file():
        raise StoryBibleError(f"{label} not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StoryBibleError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise StoryBibleError(f"{label} must be a YAML object")
    try:
        return model.model_validate(raw)
    except ValueError as exc:
        raise StoryBibleError(f"invalid {label} {path}: {exc}") from exc


def load_character_bible(path: Path) -> CharacterBible:
    return _load_yaml(path, CharacterBible, "character bible")  # type: ignore[return-value]


def load_shot_bible(path: Path) -> ShotBible:
    return _load_yaml(path, ShotBible, "shot bible")  # type: ignore[return-value]


def _load_script(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise StoryBibleError(f"production script not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoryBibleError(f"cannot read production script {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("shots"), list):
        raise StoryBibleError("production script must contain a shots list")
    return raw


def _voice_checks(
    characters: CharacterBible,
    voices: VoiceLibrary | None,
    *,
    require_approved: bool,
) -> tuple[CheckStatus, list[dict[str, Any]]]:
    referenced = [c for c in characters.characters if c.voice_profile_id]
    if not referenced:
        return "SKIPPED", []
    if voices is None:
        return "FAIL", [
            {"character_id": c.character_id, "profile_id": c.voice_profile_id,
             "error": "voice_profile_id set but no voices.yaml supplied"}
            for c in referenced
        ]
    results: list[dict[str, Any]] = []
    status: CheckStatus = "PASS"
    for character in referenced:
        assert character.voice_profile_id is not None
        try:
            profile = voices.get(character.voice_profile_id)
        except Exception as exc:  # noqa: BLE001 - report, do not crash the whole check
            status = "FAIL"
            results.append({"character_id": character.character_id,
                            "profile_id": character.voice_profile_id,
                            "error": str(exc)})
            continue
        ok = profile.ready if require_approved else True
        if not ok:
            status = "FAIL"
        results.append({
            "character_id": character.character_id,
            "profile_id": profile.profile_id,
            "status": profile.status,
            "commercial_allowed": profile.commercial_allowed,
            "tts_mode": profile.tts_mode,
            "ok": ok,
        })
    return status, results


def check_story_bibles(
    script_path: Path,
    characters_path: Path,
    shots_path: Path,
    *,
    voices_path: Path | None = None,
    require_approved_voices: bool = True,
) -> dict[str, Any]:
    """Check references, coverage and style agreement; never infer identity."""
    script = _load_script(script_path)
    characters = load_character_bible(characters_path)
    shots = load_shot_bible(shots_path)

    errors: list[str] = []
    warnings: list[str] = []

    script_style = script.get("style_id")
    for label, bible in (("character", characters), ("shot", shots)):
        if bible.style_id and script_style and bible.style_id != script_style:
            errors.append(
                f"{label} bible style_id={bible.style_id!r} does not match script "
                f"style_id={script_style!r}")
        if not bible.style_id:
            warnings.append(f"{label} bible has no style_id; style agreement is unverified")

    script_shots = script.get("shots") or []
    script_ids = [str(shot.get("shot_id") or "") for shot in script_shots]
    bible_ids = [shot.shot_id for shot in shots.shots]
    missing = [shot_id for shot_id in script_ids if shot_id not in set(bible_ids)]
    extra = [shot_id for shot_id in bible_ids if shot_id not in set(script_ids)]
    if missing:
        errors.append(f"shot bible is missing scripted shots: {missing}")
    if extra:
        errors.append(f"shot bible references shots not in the script: {extra}")

    known_chars = {c.character_id for c in characters.characters}
    for shot in shots.shots:
        unknown = [char_id for char_id in shot.character_ids if char_id not in known_chars]
        if unknown:
            errors.append(f"{shot.shot_id} references unknown characters: {unknown}")

    voice_status, voice_results = _voice_checks(
        characters, load_library(voices_path, allow_missing=True) if voices_path else None,
        require_approved=require_approved_voices)
    if voice_status == "FAIL":
        errors.append("one or more character voice profiles are missing or not APPROVED")

    status: CheckStatus = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "schema_version": "1.0",
        "script": str(script_path),
        "character_bible": str(characters_path),
        "shot_bible": str(shots_path),
        "style_id": script_style,
        "characters": len(characters.characters),
        "shots": len(shots.shots),
        "voice_check": {"status": voice_status, "profiles": voice_results},
        "errors": errors,
        "warnings": warnings,
        "same_face_guarantee": False,
        "note": (
            "引用/覆盖/风格一致性可被本报告验证；同一角色跨镜头是否同一张脸"
            "必须由人工视觉复核，本工具不提供也不声称提供身份一致性。"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check character/shot bible continuity")
    parser.add_argument("--script", required=True)
    parser.add_argument("--characters", required=True)
    parser.add_argument("--shots", required=True)
    parser.add_argument("--voices", default=None, help="voice library (default: none)")
    parser.add_argument("--allow-unapproved-voices", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        report = check_story_bibles(
            Path(args.script), Path(args.characters), Path(args.shots),
            voices_path=Path(args.voices) if args.voices else None,
            require_approved_voices=not args.allow_unapproved_voices,
        )
    except StoryBibleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["status"] == "PASS", **report}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
