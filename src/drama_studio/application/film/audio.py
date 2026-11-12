"""Audio manifest helpers for the film chain.

The standard contract consumed by ``r3_build`` and ``quality`` is
``audio_manifest.json`` with a ``lines`` array. The film layer used to write a
private ``narration_manifest.json`` whose ``wav`` paths were resolved against
the repository root; the assembler then joined them onto the project root a
second time. This module owns the single conversion so both producers and
consumers agree.
"""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Any

from drama_studio.domain.film.text import clean_spoken_text

AUDIO_MANIFEST = "audio_manifest.json"
FILM_NARRATION_MANIFEST = "narration_manifest.json"


class AudioError(RuntimeError):
    pass


def wrap_subtitle(text: str, max_chars: int = 16) -> str:
    """Wrap display text without changing the spoken text.

    A 28-character poetry line is readable in a script but too wide for a
    1080-pixel subtitle. The break is inserted as a newline, which r3_build
    writes as an ASS line break.
    """
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    rows: list[str] = []
    current = ""
    for char in stripped:
        current += char
        if len(current) >= max_chars and char in "，,、；;。！？!? ":
            rows.append(current)
            current = ""
    if current:
        rows.append(current)
    # Hard-wrap a run with no punctuation near the limit.
    final: list[str] = []
    for row in rows:
        while len(row) > max_chars * 2:
            final.append(row[:max_chars])
            row = row[max_chars:]
        final.append(row)
    return "\n".join(final)


def wav_info(path: Path) -> dict[str, Any]:
    """Duration/sample rate of a PCM WAV; ffprobe fallback for other encodings."""
    if not path.is_file():
        raise AudioError(f"audio file not found: {path}")
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            channels = handle.getnchannels()
            return {
                "duration_seconds": round(frames / float(rate), 6) if rate else 0.0,
                "sample_rate": rate,
                "channels": channels,
            }
    except (wave.Error, EOFError):
        pass
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=sample_rate,channels:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AudioError(f"cannot probe audio {path}: {proc.stderr[-400:]}")
    payload = json.loads(proc.stdout or "{}")
    stream = (payload.get("streams") or [{}])[0]
    return {
        "duration_seconds": round(float((payload.get("format") or {}).get("duration") or 0.0), 6),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AudioError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_audio_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    if not manifest.get("lines"):
        raise AudioError(f"{path} has no lines")
    return manifest


def standard_manifest(
    *,
    project_id: str,
    segments: list[dict[str, Any]],
    root: Path,
    content_type: str = "poetry",
    language: str = "zh-CN",
    engine: str = "voxcpm2",
    endpoint: str | None = None,
    reference: str | None = None,
    reference_text: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert per-line film records into the r3_build/quality contract.

    ``file`` is repository-relative because r3_build resolves ``ROOT / file``.
    Durations are probed from the WAV, never trusted from an earlier manifest.
    """
    lines: list[dict[str, Any]] = []
    for segment in segments:
        spoken = clean_spoken_text(str(segment.get("text", "")), language=language).cleaned
        subtitle = clean_spoken_text(
            str(segment.get("subtitle_text") or segment.get("text", "")),
            language=language,
        ).cleaned
        wav = Path(str(segment.get("wav") or segment.get("file") or ""))
        if not wav.is_absolute():
            wav = root / wav
        info = wav_info(wav)
        try:
            relative = wav.resolve().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise AudioError(f"{segment.get('id')}: audio must live inside the project root: {wav}") from exc
        line = {
            "id": segment["id"],
            "file": relative,
            "text": spoken,
            "subtitle_text": wrap_subtitle(subtitle),
            "duration_seconds": info["duration_seconds"],
            "planned_pause_after_ms": int(segment.get("pause_after_ms", 0) or 0),
            # Timing is expressed as gap_before_ms by the film timeline; keeping
            # pause_after_ms at zero stops the two from double-counting.
            "pause_after_ms": 0,
            "gap_before_ms": int(segment.get("gap_before_ms", 0) or 0),
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "emotion": segment.get("emotion"),
            "delivery": segment.get("delivery"),
            "speed": segment.get("speed", 1.0),
            "voice_profile": segment.get("voice_profile"),
        }
        if segment.get("sha256"):
            line["sha256"] = segment["sha256"]
        lines.append(line)
    payload: dict[str, Any] = {
        "project_id": project_id,
        "engine": engine,
        "content_type": content_type,
        "lines": lines,
    }
    if endpoint:
        payload["endpoint"] = endpoint
    if reference:
        payload["reference"] = reference
        payload["reference_text"] = reference_text
    if extra:
        payload.update(extra)
    return payload


def write_manifest(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
