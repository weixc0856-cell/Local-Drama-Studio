"""Voice profile and cast contracts.

A voice profile is the unit that may enter production. It names either an SFT
preset speaker or a zero-shot reference recording, and carries the status and
licence fields that gate production use. Profiles are deliberately separate
from the audio asset registry: the registry owns files and hashes, while a
profile owns the *performance* choice (mode, speaker, prompt, speed).

The loader is opt-in. ``narration.json`` may name a profile per line; without
one, the historical ``tts.mode`` / ``default_speaker`` / ``zero_shot`` config
path is unchanged. A run may mix profiles, but only within one backend mode:
one CosyVoice process can load either CosyVoice-300M-SFT or CosyVoice2-0.5B,
so mixing ``sft`` and ``zero_shot`` in one run is refused instead of silently
switching the service.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

VoiceStatus = Literal["DRAFT", "TECHNICALLY_VALIDATED", "LICENSE_VERIFIED",
                      "APPROVED", "BLOCKED"]
TtsMode = Literal["sft", "zero_shot"]

READY_STATUSES = {"APPROVED"}


class VoiceProfileError(RuntimeError):
    pass


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    display_name: str = Field(min_length=1, max_length=80)
    tts_mode: TtsMode
    speaker: str | None = Field(default=None, min_length=1, max_length=80)
    prompt_audio: str | None = Field(default=None, min_length=1, max_length=500)
    prompt_text: str | None = Field(default=None, min_length=1, max_length=500)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    status: VoiceStatus = "DRAFT"
    commercial_allowed: bool | None = None
    license_evidence: str | None = Field(default=None, max_length=500)
    asset_id: str | None = Field(default=None, max_length=120)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _mode_fields(self) -> "VoiceProfile":
        if self.tts_mode == "sft":
            if not self.speaker:
                raise ValueError(f"{self.profile_id}: sft profile needs speaker")
            if self.prompt_audio or self.prompt_text:
                raise ValueError(f"{self.profile_id}: sft profile cannot carry a zero-shot prompt")
        else:
            if not self.prompt_audio or not self.prompt_text:
                raise ValueError(
                    f"{self.profile_id}: zero_shot profile needs prompt_audio and prompt_text")
            if self.speaker:
                raise ValueError(f"{self.profile_id}: zero_shot profile cannot name an SFT speaker")
        if self.status == "APPROVED" and self.commercial_allowed is False:
            raise ValueError(f"{self.profile_id}: APPROVED profile cannot be non-commercial")
        if self.status == "APPROVED" and not self.license_evidence:
            raise ValueError(f"{self.profile_id}: APPROVED profile needs license_evidence")
        return self

    @property
    def ready(self) -> bool:
        return self.status in READY_STATUSES and self.commercial_allowed is not False


class VoiceLibrary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    default_profile: str | None = None
    profiles: list[VoiceProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_and_default(self) -> "VoiceLibrary":
        ids = [p.profile_id for p in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate voice profile_id")
        if self.default_profile and self.default_profile not in set(ids):
            raise ValueError(f"default_profile {self.default_profile!r} is not defined")
        return self

    def get(self, profile_id: str) -> VoiceProfile:
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        raise VoiceProfileError(
            f"voice profile not found: {profile_id}; "
            f"available: {[p.profile_id for p in self.profiles]}")


class VoiceCastFile(BaseModel):
    """Sidecar mapping from narration lines to voice profiles.

    Keys may be 1-based indexes (``"1"``) or script line ids (``"line_001"``).
    The sidecar keeps casting out of the LLM's ``ProductionScript`` contract.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    default_profile: str | None = None
    header_profile: str | None = None
    lines: dict[str, str] = Field(default_factory=dict)
    characters: dict[str, str] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _keys(self) -> "VoiceCastFile":
        import re

        line_key = re.compile(r"^(line_)?\d{1,3}$")
        char_key = re.compile(r"^char_\d{3}$")
        for key in self.lines:
            if not line_key.match(key):
                raise ValueError(f"voice cast line key must be 001/1/line_001, got {key!r}")
        for key in self.characters:
            if not char_key.match(key):
                raise ValueError(f"voice cast character key must be char_001, got {key!r}")
        return self

    def line_profile(self, index: int, line_id: str | None = None) -> str | None:
        if line_id and line_id in self.lines:
            return self.lines[line_id]
        padded = f"{index:03d}"
        for key in (str(index), padded, f"line_{padded}"):
            if key in self.lines:
                return self.lines[key]
        return None


class ResolvedVoice(BaseModel):
    """A profile with paths and hashes resolved against the project root."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    display_name: str
    tts_mode: TtsMode
    speaker: str | None = None
    speaker_id: str | None = None
    prompt_audio: str | None = None
    prompt_text: str | None = None
    prompt_sha256: str | None = None
    speed: float | None = None
    status: VoiceStatus
    commercial_allowed: bool | None = None
    license_evidence: str | None = None
    asset_id: str | None = None

    @property
    def label(self) -> str:
        if self.tts_mode == "sft":
            return str(self.speaker)
        return f"zero_shot:{Path(self.prompt_audio or '').stem}"

    def cast_record(self) -> dict[str, Any]:
        """Stable per-line provenance; paths are project-relative."""
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "label": self.label,
            "tts_mode": self.tts_mode,
            "speaker": self.speaker,
            "speaker_id": self.speaker_id,
            "prompt_audio": self.prompt_audio,
            "prompt_sha256": self.prompt_sha256,
            "prompt_text": self.prompt_text,
            "speed": self.speed,
            "status": self.status,
            "commercial_allowed": self.commercial_allowed,
            "license_evidence": self.license_evidence,
            "asset_id": self.asset_id,
        }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def default_library_path(root: Path) -> Path:
    return Path(root) / "config" / "voices.yaml"


def load_library(path: Path | None = None, *, root: Path | None = None,
                 allow_missing: bool = True) -> VoiceLibrary | None:
    """Load ``config/voices.yaml``; missing is allowed unless requested."""
    if path is None:
        if root is None:
            raise VoiceProfileError("load_library needs path or root")
        path = default_library_path(root)
    path = Path(path)
    if not path.is_file():
        if allow_missing:
            return None
        raise VoiceProfileError(f"voice library not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise VoiceProfileError(f"cannot read voice library {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise VoiceProfileError("voice library must be a YAML object")
    try:
        return VoiceLibrary.model_validate(raw)
    except ValueError as exc:
        raise VoiceProfileError(f"invalid voice library {path}: {exc}") from exc


def load_voice_cast(path: Path) -> VoiceCastFile:
    path = Path(path)
    if not path.is_file():
        raise VoiceProfileError(f"voice cast not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise VoiceProfileError(f"cannot read voice cast {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise VoiceProfileError("voice cast must be a YAML object")
    try:
        return VoiceCastFile.model_validate(raw)
    except ValueError as exc:
        raise VoiceProfileError(f"invalid voice cast {path}: {exc}") from exc


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def resolve_voice(profile: VoiceProfile, root: Path,
                  *, require_approved: bool = True) -> ResolvedVoice:
    """Resolve one profile, enforcing status and reference-audio integrity."""
    if require_approved and not profile.ready:
        raise VoiceProfileError(
            f"{profile.profile_id}: status={profile.status}, "
            f"commercial_allowed={profile.commercial_allowed}; "
            "only APPROVED profiles may enter a production TTS run"
        )
    speaker_id = profile.speaker if profile.tts_mode == "sft" else None
    prompt_audio: str | None = None
    prompt_sha: str | None = None
    if profile.tts_mode == "zero_shot":
        assert profile.prompt_audio is not None
        prompt_path = Path(profile.prompt_audio)
        prompt_path = prompt_path if prompt_path.is_absolute() else (Path(root) / prompt_path)
        if not prompt_path.is_file():
            raise VoiceProfileError(
                f"{profile.profile_id}: reference audio not found: {prompt_path}")
        prompt_audio = _relative(prompt_path, Path(root))
        prompt_sha = _sha256(prompt_path)
    return ResolvedVoice(
        profile_id=profile.profile_id,
        display_name=profile.display_name,
        tts_mode=profile.tts_mode,
        speaker=profile.speaker,
        speaker_id=speaker_id,
        prompt_audio=prompt_audio,
        prompt_text=profile.prompt_text,
        prompt_sha256=prompt_sha,
        speed=profile.speed,
        status=profile.status,
        commercial_allowed=profile.commercial_allowed,
        license_evidence=profile.license_evidence,
        asset_id=profile.asset_id,
    )


def cast_sha256(casts: list[dict[str, Any]]) -> str:
    payload = json.dumps(casts, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_one_backend(casts: list[ResolvedVoice]) -> str:
    """One CosyVoice process serves one model; refuse mixed backend modes."""
    modes = {cast.tts_mode for cast in casts}
    if len(modes) != 1:
        raise VoiceProfileError(
            f"mixed TTS modes in one run: {sorted(modes)}; "
            "start one runtime per mode and render separate passes")
    return next(iter(modes))
