"""Adapt a film edit timeline to the r3_build contracts.

``segments.json`` and ``audio_manifest.json`` are the only boundary between the
film layer and the build engine. The film layer does not know how FFmpeg mixes
or burns subtitles; r3_build does not know what a shot or a beat is.

A still that the motion stage already rendered enters as a video segment. A
still without a motion clip enters as an image segment and keeps the r3_build
Ken Burns path. A Wan frame run must be encoded by ``film clips`` first; this
module refuses to pretend frames are a video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from drama_studio.application.film.assets import ShotAsset, resolve_asset
from drama_studio.domain.film.schemas import EditTimeline, Storyboard
from drama_studio.application.film.timeline import apply_line_timing


class SegmentError(RuntimeError):
    pass


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SegmentError(f"asset escapes the project root: {path}") from exc


def build_segments(
    project_root: Path,
    storyboard: Storyboard,
    timeline: EditTimeline,
    *,
    root: Path,
    assets: dict[str, ShotAsset] | None = None,
) -> list[dict[str, Any]]:
    entries = {entry.shot_id: entry for entry in timeline.entries}
    segments: list[dict[str, Any]] = []
    for shot in storyboard.shots:
        entry = entries[shot.shot_id]
        duration = round((entry.end_ms - entry.start_ms) / 1000.0, 3)
        asset = (assets or {}).get(shot.shot_id) or resolve_asset(project_root, shot.shot_id)
        if asset is None:
            raise SegmentError(f"{shot.shot_id}: no keyframe, clip or frame run")
        if asset.kind == "image_sequence":
            raise SegmentError(
                f"{shot.shot_id}: Wan PNG frames exist but are not encoded; run `drama film clips` first")
        if asset.path is None:
            raise SegmentError(f"{shot.shot_id}: {asset.kind} has no file")
        segments.append({
            "id": shot.shot_id,
            "shot_id": shot.shot_id,
            "type": "video" if asset.kind == "video" else "image",
            "source": _rel(asset.path, root),
            "duration": duration,
            "line_ids": list(shot.narration_ids),
            "transition_in": entry.transition_in.value,
            "transition_out": entry.transition_out.value,
            "asset_kind": asset.kind,
            "sha256": asset.sha256,
            "planned_duration_seconds": shot.duration_seconds,
        })
    total = round(sum(item["duration"] for item in segments), 3)
    expected = round(timeline.total_ms / 1000.0, 3)
    if abs(total - expected) > 0.002:
        raise SegmentError(f"segments total {total:.3f}s != timeline {expected:.3f}s")
    return segments


def build_audio_manifest(
    audio_manifest: dict,
    timeline: EditTimeline,
    *,
    root: Path,
) -> dict[str, Any]:
    payload = apply_line_timing(audio_manifest, timeline)
    for line in payload["lines"]:
        path = Path(line["file"])
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            raise SegmentError(f"{line['id']}: audio file missing: {path}")
    payload["timeline"] = {
        "total_ms": timeline.total_ms,
        "leading_silence_ms": timeline.leading_silence_ms,
        "fps": timeline.fps,
        "narration_events": [event.model_dump(mode="json") for event in timeline.narration_events],
    }
    return payload


def build_audio_timeline(
    audio_manifest: dict,
    timeline: EditTimeline,
    *,
    root: Path,
    bgm_asset_id: str | None = None,
    bgm_gain_db: float = -18.0,
    ambience_asset_id: str | None = None,
    ambience_gain_db: float = -26.0,
) -> dict[str, Any] | None:
    """Multi-track timeline: absolute narration events plus an optional BGM bed.

    Returns ``None`` when no BGM is requested, so the legacy narration-only mix
    stays byte-compatible for projects that do not use it.
    """
    if not bgm_asset_id and not ambience_asset_id:
        return None
    events = []
    by_id = {str(line["id"]): line for line in audio_manifest.get("lines", [])}
    for event in timeline.narration_events:
        line = by_id.get(event.id)
        if line is None:
            raise SegmentError(f"timeline event {event.id} has no audio line")
        duration = event.end_ms - event.start_ms
        if duration <= 0:
            raise SegmentError(f"{event.id}: non-positive duration")
        events.append({
            "event_id": event.id,
            "path": line["file"],
            "line_id": event.id,
            "start_ms": event.start_ms,
            "duration_ms": duration,
            "gain_db": 0.0,
            "fade_in_ms": 0,
            "fade_out_ms": 0,
        })
    total = int(timeline.total_ms)
    tracks: list[dict[str, Any]] = [
        {
            "track_id": "narration",
            "type": "narration",
            "gain_db": 0.0,
            "events": events,
        },
    ]
    if ambience_asset_id:
        # A continuous wind/water bed covers every cut. It is intentionally not
        # triggered by narration: ambience is the glue, not a sound effect.
        tracks.append({
            "track_id": "ambience",
            "type": "bgm",
            "asset_id": ambience_asset_id,
            "start_ms": 0,
            "duration_ms": total,
            "loop": True,
            "fade_in_ms": 1000,
            "fade_out_ms": 1000,
            "gain_db": ambience_gain_db,
        })
    if bgm_asset_id:
        tracks.append({
            "track_id": "bgm",
            "type": "bgm",
            "asset_id": bgm_asset_id,
            "start_ms": 0,
            "duration_ms": total,
            "loop": True,
            "fade_in_ms": min(2000, max(0, total // 10)),
            "fade_out_ms": min(3000, max(0, total // 8)),
            "gain_db": bgm_gain_db,
            "ducking": {
                "enabled": True,
                "trigger_track_ids": ["narration"],
                "threshold": 0.03,
                "ratio": 8.0,
                "attack_ms": 20,
                "release_ms": 500,
            },
        })
    return {
        "schema_version": "1.0",
        "sample_rate": int(timeline.sample_rate),
        "duration_ms": total,
        "tracks": tracks,
    }


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
