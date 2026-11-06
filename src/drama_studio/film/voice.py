"""Per-segment narration synthesis through the VoxCPM2 HTTP service."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import load_audio, load_settings
from ..voice.zeroshot import synthesize as zeroshot_synthesize
from .project import FilmProject
from .schemas import NarrationSegment


def render_text(segment: NarrationSegment) -> str:
    """Optional natural-language direction prefix understood by VoxCPM2."""
    hints = [item for item in (segment.emotion, segment.delivery) if item]
    if not hints:
        return segment.text
    return f"({', '.join(hints)}){segment.text}"


def synthesize_narration(
    project: FilmProject,
    root: Path,
    *,
    base_url: str | None = None,
    out_dir: Path | None = None,
    use_direction: bool = True,
) -> dict:
    if project.narration is None:
        raise ValueError("narration.json is required")
    audio_cfg = load_audio(root)
    zero = (audio_cfg.get("tts") or {}).get("zero_shot") or {}
    prompt_audio = zero.get("prompt_audio")
    prompt_text = zero.get("prompt_text")
    if not prompt_audio or not prompt_text:
        raise ValueError("config/audio.yaml tts.zero_shot.prompt_audio/prompt_text are required")

    settings = load_settings(root)
    endpoint = (base_url or settings.tts.base_url).rstrip("/")
    project_root = (root / "projects" / project.project_id).resolve()
    target = out_dir or (project_root / "assets" / "audio")
    target.mkdir(parents=True, exist_ok=True)

    records = []
    for segment in project.narration.segments:
        wav = target / f"{segment.id}.wav"
        spoken = render_text(segment) if use_direction else segment.text
        result = zeroshot_synthesize(
            spoken,
            prompt_wav=root / prompt_audio,
            prompt_text=prompt_text,
            out_wav=wav,
            speed=segment.speed,
            base=endpoint,
        )
        records.append({
            "id": segment.id,
            "text": segment.text,
            "rendered_text": spoken,
            "emotion": segment.emotion,
            "delivery": segment.delivery,
            "speed": segment.speed,
            "pause_after_ms": segment.pause_after_ms,
            "wav": str(wav.relative_to(root)).replace("\\", "/"),
            "seconds": round(result.seconds, 3),
            "synth_seconds": round(result.synth_seconds, 3),
            "sample_rate": result.sample_rate,
            "prompt_sha256": result.prompt_sha256,
        })

    manifest = {
        "project_id": project.project_id,
        "engine": "voxcpm2",
        "endpoint": endpoint,
        "reference": prompt_audio,
        "reference_text": prompt_text,
        "segments": records,
    }
    (target / "narration_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"manifest": str(target / "narration_manifest.json"), "segments": len(records),
            "audio_seconds": round(sum(item["seconds"] for item in records), 2)}
