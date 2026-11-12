"""Strict audio timeline contract for multi-track mixes.

The timeline is a sidecar next to ``segments.json``. It deliberately does not
change the existing ``segments.json`` array or ``audio_manifest.json`` line
format: those consumers stay compatible, and a build without a timeline keeps
the old narration-only mix.

Times are integer milliseconds. Events must fit inside the timeline. Narration
and dialogue events may point at a TTS WAV path directly; BGM/SFX tracks must
reference an ``asset_id`` in the audio asset registry so licensing and hashes
are checked before a production mix.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TrackType = Literal["narration", "dialogue", "bgm", "sfx"]


class TimelineError(RuntimeError):
    pass


class AudioEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=r"^[A-Za-z0-9_\-]{1,64}$")
    asset_id: str | None = Field(default=None, min_length=1, max_length=120)
    path: str | None = Field(default=None, min_length=1, max_length=500)
    line_id: str | None = Field(default=None, min_length=1, max_length=80)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    gain_db: float = Field(default=0.0, ge=-60.0, le=24.0)
    fade_in_ms: int = Field(default=0, ge=0)
    fade_out_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _source_and_fades(self) -> "AudioEvent":
        if not self.asset_id and not self.path:
            raise ValueError(f"{self.event_id}: asset_id or path is required")
        if self.fade_in_ms + self.fade_out_ms > self.duration_ms:
            raise ValueError(f"{self.event_id}: fades exceed duration")
        return self


class DuckingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    trigger_track_ids: list[str] = Field(default_factory=list, min_length=1)
    threshold: float = Field(default=0.03, gt=0.0, le=1.0)
    ratio: float = Field(default=8.0, ge=1.0, le=20.0)
    attack_ms: int = Field(default=20, ge=1, le=2000)
    release_ms: int = Field(default=500, ge=1, le=5000)


class AudioTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str = Field(pattern=r"^[A-Za-z0-9_\-]{1,64}$")
    type: TrackType
    gain_db: float = Field(default=0.0, ge=-60.0, le=24.0)
    events: list[AudioEvent] = Field(default_factory=list)

    # BGM-only fields. They are rejected on event tracks by _track_shape.
    asset_id: str | None = Field(default=None, min_length=1, max_length=120)
    start_ms: int = Field(default=0, ge=0)
    duration_ms: int | None = Field(default=None, gt=0)
    loop: bool = False
    fade_in_ms: int = Field(default=0, ge=0)
    fade_out_ms: int = Field(default=0, ge=0)
    ducking: DuckingSpec | None = None

    @model_validator(mode="after")
    def _track_shape(self) -> "AudioTrack":
        if self.type in ("narration", "dialogue"):
            if not self.events:
                raise ValueError(f"{self.track_id}: {self.type} track needs events")
            if self.asset_id or self.loop or self.ducking:
                raise ValueError(f"{self.track_id}: {self.type} track cannot use bgm fields")
            return self
        if self.type == "bgm":
            if self.events:
                raise ValueError(f"{self.track_id}: bgm track uses asset_id, not events")
            if not self.asset_id:
                raise ValueError(f"{self.track_id}: bgm track needs asset_id")
            return self
        # sfx
        if not self.events:
            raise ValueError(f"{self.track_id}: sfx track needs events")
        if self.asset_id or self.loop or self.ducking:
            raise ValueError(f"{self.track_id}: sfx track cannot use bgm fields")
        return self

    def end_ms(self, timeline_duration_ms: int) -> int:
        if self.type == "bgm":
            effective = self.duration_ms or max(0, timeline_duration_ms - self.start_ms)
            return self.start_ms + effective
        return max((e.start_ms + e.duration_ms for e in self.events), default=0)


class AudioTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    sample_rate: int = Field(default=48000, ge=8000, le=192000)
    duration_ms: int = Field(gt=0)
    tracks: list[AudioTrack] = Field(min_length=1)

    @model_validator(mode="after")
    def _integrity(self) -> "AudioTimeline":
        track_ids = [t.track_id for t in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("duplicate track_id")
        event_ids: list[str] = []
        by_id = {t.track_id: t for t in self.tracks}
        for track in self.tracks:
            if track.end_ms(self.duration_ms) > self.duration_ms:
                raise ValueError(
                    f"{track.track_id}: events end at {track.end_ms(self.duration_ms)}ms "
                    f"> timeline {self.duration_ms}ms")
            if track.type == "bgm":
                effective = track.duration_ms or max(0, self.duration_ms - track.start_ms)
                if track.fade_in_ms + track.fade_out_ms > effective:
                    raise ValueError(f"{track.track_id}: fades exceed bgm duration")
            event_ids.extend(e.event_id for e in track.events)
            if track.ducking:
                for trigger in track.ducking.trigger_track_ids:
                    target = by_id.get(trigger)
                    if target is None:
                        raise ValueError(f"{track.track_id}: ducking trigger {trigger} not found")
                    if target.type not in ("narration", "dialogue"):
                        raise ValueError(
                            f"{track.track_id}: ducking trigger {trigger} must be narration/dialogue")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate event_id")
        return self


def load_timeline(path: Path) -> AudioTimeline:
    path = Path(path)
    if not path.is_file():
        raise TimelineError(f"audio timeline not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TimelineError(f"cannot read audio timeline {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise TimelineError("audio timeline must be a JSON object")
    return AudioTimeline.model_validate(raw)


def _manifest_line_start(manifest: dict[str, Any], line: dict[str, Any]) -> int:
    ledger = manifest.get("ledger") or []
    index = int(line.get("index") or 0)
    for item in ledger:
        if item.get("kind") == "line" and int(item.get("index") or 0) == index:
            return int(round(float(item.get("start") or 0.0) * 1000))
    # Fallback: sequential, including the optional spoken header.
    cursor = 0
    header = manifest.get("header")
    if header:
        cursor += int(round(float(header.get("duration_seconds") or 0.0) * 1000))
        cursor += int(header.get("pause_ms") or 0)
    for item in manifest.get("lines") or []:
        if int(item.get("index") or 0) == index:
            return cursor
        cursor += int(round(float(item.get("duration_seconds") or 0.0) * 1000))
        cursor += int(item.get("pause_after_ms") or 0)
    return cursor


def from_audio_manifest(manifest_path: Path, *, track_id: str = "narration_main") -> AudioTimeline:
    """Derive a narration track from an existing ``audio_manifest.json``.

    This is the bridge for the current TTS output. BGM/SFX are added by the
    author/editor; they are not invented here.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise TimelineError(f"audio manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TimelineError(f"cannot read audio manifest {manifest_path}: {exc}") from exc
    lines = manifest.get("lines") or []
    if not lines:
        raise TimelineError("audio manifest has no lines")
    events: list[AudioEvent] = []
    end = 0
    for index, line in enumerate(lines, start=1):
        start = _manifest_line_start(manifest, line)
        duration = int(round(float(line.get("duration_seconds") or 0.0) * 1000))
        if duration <= 0:
            raise TimelineError(f"line {index}: duration_seconds must be > 0")
        events.append(AudioEvent(
            event_id=f"narration_{index:03d}",
            path=str(line["file"]),
            line_id=f"line_{index:03d}",
            start_ms=start,
            duration_ms=duration,
        ))
        end = max(end, start + duration)
    if end <= 0:
        raise TimelineError("audio manifest produced an empty timeline")
    return AudioTimeline(
        schema_version="1.0",
        sample_rate=int(manifest.get("sample_rate") or 48000),
        duration_ms=end,
        tracks=[AudioTrack(track_id=track_id, type="narration", events=events)],
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Derive a narration audio timeline from audio_manifest.json")
    parser.add_argument("--audio-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--track-id", default="narration_main")
    args = parser.parse_args(argv)
    try:
        timeline = from_audio_manifest(Path(args.audio_manifest), track_id=args.track_id)
    except (OSError, ValueError, TimelineError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(timeline.model_dump_json(indent=2) + chr(10), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "duration_ms": timeline.duration_ms,
                      "tracks": len(timeline.tracks)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
