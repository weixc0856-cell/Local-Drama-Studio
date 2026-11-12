"""Per-segment narration synthesis through the VoxCPM2 HTTP service.

The output is the same ``audio_manifest.json`` contract that ``r3_build`` and
``quality`` consume. There is no second, film-only manifest: that divergence is
what made ``film voice`` and ``film assemble`` disagree about WAV paths.

Per-line voice casting is supported through ``narration.json``
``voice_profile`` and ``config/voices.yaml``. This is VoxCPM2 zero-shot only;
an ``sft`` profile is refused by name rather than silently downgraded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import load_audio, load_settings
from ..voice.profiles import VoiceProfileError, load_library, resolve_voice
from ..voice.zeroshot import synthesize as zeroshot_synthesize
from . import audio as audio_contract
from .project import FilmProject
from .text import clean_spoken_text
from .schemas import NarrationSegment

AUDIO_MANIFEST = audio_contract.AUDIO_MANIFEST


class FilmVoiceError(RuntimeError):
    pass


def render_text(segment: NarrationSegment, language: str = "zh-CN") -> str:
    """Return only speakable text.

    Director notes stay in ``emotion`` / ``delivery`` metadata. They are never
    prepended to the TTS input: the previous implementation did that and the
    runtime read ``(majestic, expansive)`` aloud.
    """
    return clean_spoken_text(segment.text, language=language).cleaned


def _default_reference(root: Path) -> tuple[str, str] | None:
    audio_cfg = load_audio(root)
    zero = (audio_cfg.get("tts") or {}).get("zero_shot") or {}
    prompt_audio = zero.get("prompt_audio")
    prompt_text = zero.get("prompt_text")
    if prompt_audio and prompt_text:
        return str(prompt_audio), str(prompt_text)
    return None


def _profile_for(segment: NarrationSegment, root: Path, default_profile: str | None,
                 *, require_approved: bool = True):
    library = load_library(root=root)
    if library is None:
        return None
    profile_id = segment.voice_profile or default_profile
    if not profile_id:
        return None
    profile = library.get(profile_id)
    if profile.status == "BLOCKED":
        raise VoiceProfileError(
            f"{profile_id}: status=BLOCKED; even a local research run refuses it")
    if profile.commercial_allowed is False and require_approved:
        raise VoiceProfileError(
            f"{profile_id}: commercial_allowed=false; pass allow_noncommercial for a local research run")
    return resolve_voice(profile, root, require_approved=require_approved)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_ok(path: Path, record: dict | None, spoken: str, speed: float,
                 profile_id: str | None, prompt_sha256: str) -> bool:
    if not path.is_file() or not record:
        return False
    return (
        record.get("rendered_text") == spoken
        and abs(float(record.get("speed") or 1.0) - speed) < 1e-6
        and (record.get("voice_profile") or None) == (profile_id or None)
        and record.get("prompt_sha256") == prompt_sha256
        and int(record.get("bytes") or 0) == path.stat().st_size
    )


def synthesize_narration(
    project: FilmProject,
    root: Path,
    *,
    base_url: str | None = None,
    out_dir: Path | None = None,
    use_direction: bool = True,
    force: bool = False,
    allow_noncommercial: bool = False,
) -> dict:
    if project.narration is None:
        raise ValueError("narration.json is required")
    settings = load_settings(root)
    endpoint = (base_url or settings.tts.base_url).rstrip("/")
    project_root = (root / "projects" / project.project_id).resolve()
    target = out_dir or (project_root / "assets" / "audio")
    target.mkdir(parents=True, exist_ok=True)
    manifest_path = target / AUDIO_MANIFEST
    previous: dict[str, dict] = {}
    if manifest_path.is_file():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous = {str(item["id"]): item for item in raw.get("segments", [])}
        except (OSError, json.JSONDecodeError, KeyError):
            previous = {}

    library = load_library(root=root)
    default_profile = library.default_profile if library else None
    legacy = _default_reference(root)
    if library is None and legacy is None:
        raise FilmVoiceError(
            "no reference voice: config/voices.yaml or config/audio.yaml tts.zero_shot is required")

    records: list[dict] = []
    reused = 0
    language = project.narration.language
    manifest_reference = legacy[0] if legacy else None
    manifest_reference_text = legacy[1] if legacy else None
    for segment in project.narration.segments:
        # Direction is metadata, never a spoken prefix. use_direction is kept
        # as a compatibility parameter but no longer changes the input text.
        audit = clean_spoken_text(segment.text, language=language)
        spoken = audit.cleaned
        subtitle_text = clean_spoken_text(
            segment.subtitle_text or segment.text, language=language).cleaned
        resolved = _profile_for(segment, root, default_profile,
                                require_approved=not allow_noncommercial)
        if resolved is not None:
            if resolved.tts_mode != "zero_shot":
                raise FilmVoiceError(
                    f"{segment.id}: profile {resolved.profile_id} is {resolved.tts_mode}; "
                    "the VoxCPM2 runtime is zero-shot only")
            prompt_audio = root / str(resolved.prompt_audio)
            prompt_text = str(resolved.prompt_text or "")
            profile_id = resolved.profile_id
            speed = segment.speed if segment.speed != 1.0 else (resolved.speed or 1.0)
            prompt_sha = resolved.prompt_sha256 or _sha256(prompt_audio)
            manifest_reference = resolved.prompt_audio
            manifest_reference_text = resolved.prompt_text
        else:
            if legacy is None:
                raise FilmVoiceError(f"{segment.id}: no voice profile and no legacy reference")
            prompt_audio = root / legacy[0]
            prompt_text = legacy[1]
            profile_id = None
            speed = segment.speed
            prompt_sha = _sha256(prompt_audio)

        wav = target / f"{segment.id}.wav"
        prior = previous.get(segment.id)
        if not force and _existing_ok(wav, prior, spoken, speed, profile_id, prompt_sha):
            record = dict(prior or {})
            record.update({
                "id": segment.id,
                "text": segment.text,
                "subtitle_text": subtitle_text,
                "rendered_text": spoken,
                "text_audit": audit.as_record(),
                "emotion": segment.emotion,
                "delivery": segment.delivery,
                "speed": speed,
                "voice_profile": profile_id,
                "reference": manifest_reference,
                "prompt_sha256": prompt_sha,
            })
            record["wav"] = str(wav)
            records.append(record)
            reused += 1
            continue

        result = zeroshot_synthesize(
            spoken,
            prompt_wav=prompt_audio,
            prompt_text=prompt_text,
            out_wav=wav,
            speed=speed,
            base=endpoint,
        )
        info = audio_contract.wav_info(wav)
        records.append({
            "id": segment.id,
            "text": segment.text,
            "subtitle_text": subtitle_text,
            "rendered_text": spoken,
            "text_audit": audit.as_record(),
            "emotion": segment.emotion,
            "delivery": segment.delivery,
            "speed": speed,
            "voice_profile": profile_id,
            "reference": manifest_reference,
            "commercial_allowed": (resolved.commercial_allowed if resolved else None),
            "pause_after_ms": segment.pause_after_ms,
            "wav": str(wav),
            "seconds": info["duration_seconds"],
            "synth_seconds": round(result.synth_seconds, 3),
            "sample_rate": result.sample_rate,
            "prompt_sha256": result.prompt_sha256,
            "bytes": wav.stat().st_size,
        })

    manifest = audio_contract.standard_manifest(
        project_id=project.project_id,
        segments=[
            {
                "id": record["id"],
                "text": record["text"],
                "subtitle_text": record.get("subtitle_text"),
                "wav": record["wav"],
                "emotion": record.get("emotion"),
                "delivery": record.get("delivery"),
                "speed": record.get("speed", 1.0),
                "pause_after_ms": record.get("pause_after_ms", 0),
                "voice_profile": record.get("voice_profile"),
            }
            for record in records
        ],
        root=root,
        content_type="poetry",
        language=project.narration.language,
        endpoint=endpoint,
        reference=manifest_reference,
        reference_text=manifest_reference_text,
        extra={
            "segments": records,
            "voice_library": "config/voices.yaml" if library else None,
            "default_profile": default_profile,
        },
    )
    audio_contract.write_manifest(manifest_path, manifest)
    return {
        "manifest": str(manifest_path),
        "segments": len(records),
        "reused": reused,
        "audio_seconds": round(sum(item["duration_seconds"] for item in manifest["lines"]), 2),
    }
