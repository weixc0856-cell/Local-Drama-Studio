"""Edit timeline construction (FILM_PRODUCTION_GUIDE §7–§8).

Two modes:

* :func:`build_timeline` is the planned timeline: shot durations come from the
  storyboard. It is kept for validation and for projects that have no audio yet.
* :func:`build_edit_timeline` is the production timeline: narration owns the
  clock. A shot must be long enough to hold its lines plus their pauses; the
  extra tail is expressed as a gap before the next line, so audio, subtitles and
  picture all share one set of integer-millisecond boundaries.

Every boundary in this module is a planned boundary, not VAD output.
"""

from __future__ import annotations

import math

from drama_studio.application.film.assets import ShotAsset
from drama_studio.application.film.config import ProductionSettings
from drama_studio.domain.film.schemas import EditTimeline, NarrationEvent, Storyboard, TimelineEntry, Transition


def _transition_for(shot, previous) -> tuple[Transition, Transition]:
    transition_in = (
        Transition.MATCH_CUT
        if previous is not None and shot.continuity.match_cut_to == previous.shot_id
        else Transition.CUT
    )
    transition_out = Transition.MATCH_CUT if shot.continuity.match_cut_to else Transition.CUT
    if previous is not None and transition_in == Transition.CUT:
        same_size = shot.shot_size == previous.shot_size
        scene_change = shot.scene_id != previous.scene_id
        vector_jump = (previous.camera.move.value, shot.camera.move.value) in {
            ("dolly_in", "dolly_out"), ("dolly_out", "dolly_in"),
        }
        # Every ordinary cut gets a short dissolve. Match cuts stay cuts because
        # the action itself is the transition.
        transition_in = Transition.DISSOLVE
    return transition_in, transition_out


def build_timeline(storyboard: Storyboard, sample_rate: int = 48000, fps: int = 24) -> EditTimeline:
    """Planned timeline from storyboard durations (no audio required)."""
    entries: list[TimelineEntry] = []
    cursor = 0
    for index, shot in enumerate(storyboard.shots):
        duration_ms = int(round(shot.duration_seconds * 1000))
        previous = storyboard.shots[index - 1] if index > 0 else None
        transition_in, transition_out = _transition_for(shot, previous)
        entries.append(
            TimelineEntry(
                shot_id=shot.shot_id,
                start_ms=cursor,
                end_ms=cursor + duration_ms,
                narration_ids=list(shot.narration_ids),
                asset_kind=None,
                planned_duration_seconds=shot.duration_seconds,
                transition_in=transition_in,
                transition_out=transition_out,
            )
        )
        cursor += duration_ms
    return EditTimeline(
        project_id=storyboard.project_id,
        sample_rate=sample_rate,
        fps=fps,
        entries=entries,
        total_ms=cursor,
    )


def _line_ms(line: dict) -> int:
    return int(round(float(line["duration_seconds"]) * 1000))


def build_edit_timeline(
    storyboard: Storyboard,
    audio_manifest: dict,
    *,
    settings: ProductionSettings,
    assets: dict[str, ShotAsset] | None = None,
    sample_rate: int = 48000,
) -> EditTimeline:
    """Audio-first timeline: every shot holds its lines and their pauses.

    A line that is longer than its authored shot extends the shot. A shot with
    no line keeps its authored duration, with ``no_narration_seconds`` as the
    floor. The timeline is contiguous by construction, so the picture, the
    mixed audio and the subtitle events all share the same boundaries.
    """
    lines_by_id = {str(line["id"]): line for line in audio_manifest.get("lines", [])}
    if not lines_by_id:
        raise ValueError("audio manifest has no lines")

    plan: list[tuple[object, list[dict], int]] = []
    for shot in storyboard.shots:
        records: list[dict] = []
        for line_id in shot.narration_ids:
            if line_id not in lines_by_id:
                raise ValueError(f"{shot.shot_id}: narration {line_id} not found in audio manifest")
            records.append(lines_by_id[line_id])
        if records:
            block = sum(_line_ms(line) for line in records)
            block += sum(int(line.get("planned_pause_after_ms", 0)) for line in records[:-1])
            duration = max(
                int(round(shot.duration_seconds * 1000)),
                block + int(settings.narration_tail_ms),
                int(round(settings.min_shot_seconds * 1000)),
            )
        else:
            duration = max(
                int(round(shot.duration_seconds * 1000)),
                int(round(settings.no_narration_seconds * 1000)),
            )
            duration = min(duration, int(round(settings.max_shot_seconds * 1000)))
        plan.append((shot, records, duration))

    entries: list[TimelineEntry] = []
    events: list[NarrationEvent] = []
    cursor = int(settings.leading_silence_ms)
    start = 0
    for index, (shot, records, duration) in enumerate(plan):
        end = start + duration
        previous = storyboard.shots[index - 1] if index > 0 else None
        transition_in, transition_out = _transition_for(shot, previous)
        asset = (assets or {}).get(shot.shot_id)
        entries.append(
            TimelineEntry(
                shot_id=shot.shot_id,
                start_ms=start,
                end_ms=end,
                narration_ids=list(shot.narration_ids),
                visual_asset=str(asset.path) if asset and asset.path else None,
                asset_kind=asset.kind if asset else None,
                planned_duration_seconds=shot.duration_seconds,
                transition_in=transition_in,
                transition_out=transition_out,
            )
        )
        line_cursor = 0
        for position, line in enumerate(records):
            desired = start + line_cursor
            if desired < cursor:
                desired = cursor
            length = _line_ms(line)
            events.append(
                NarrationEvent(
                    id=str(line["id"]),
                    shot_id=shot.shot_id,
                    start_ms=desired,
                    end_ms=desired + length,
                    text=str(line.get("subtitle_text") or line.get("text") or ""),
                )
            )
            cursor = desired + length
            line_cursor = (desired - start) + length
            if position + 1 < len(records):
                line_cursor += int(line.get("planned_pause_after_ms", 0))
        start = end

    total = start
    required = cursor + int(round(settings.tail_seconds * 1000))
    if required > total:
        delta = required - total
        last = entries[-1]
        entries[-1] = last.model_copy(update={"end_ms": last.end_ms + delta})
        total += delta

    return EditTimeline(
        project_id=storyboard.project_id,
        sample_rate=sample_rate,
        fps=settings.fps,
        leading_silence_ms=int(settings.leading_silence_ms),
        entries=entries,
        narration_events=events,
        total_ms=total,
    )


def narration_spans(timeline: EditTimeline) -> dict[str, tuple[int, int]]:
    """Map narration id -> (start_ms, end_ms); a line may span several shots."""
    spans: dict[str, list[int]] = {}
    for entry in timeline.entries:
        for item in entry.narration_ids:
            span = spans.setdefault(item, [entry.start_ms, entry.end_ms])
            span[0] = min(span[0], entry.start_ms)
            span[1] = max(span[1], entry.end_ms)
    return {key: (value[0], value[1]) for key, value in spans.items()}


def apply_line_timing(audio_manifest: dict, timeline: EditTimeline) -> dict:
    """Return a copy of the manifest whose lines carry absolute timing.

    ``gap_before_ms`` is the distance from the previous line's end to this
    line's start. ``pause_after_ms`` is forced to zero so the two mechanisms
    cannot double-count a pause.
    """
    by_id = {event.id: event for event in timeline.narration_events}
    # r3_build adds --leading-ms itself before the first line; start from the
    # same offset so the first gap is zero and silence is not counted twice.
    cursor = int(timeline.leading_silence_ms)
    lines: list[dict] = []
    for line in audio_manifest.get("lines", []):
        event = by_id.get(str(line["id"]))
        if event is None:
            raise ValueError(f"timeline has no event for narration {line['id']}")
        gap = max(0, event.start_ms - cursor)
        updated = dict(line)
        updated["gap_before_ms"] = gap
        updated["pause_after_ms"] = 0
        updated["start_ms"] = event.start_ms
        updated["end_ms"] = event.end_ms
        lines.append(updated)
        cursor = event.end_ms
    payload = dict(audio_manifest)
    payload["lines"] = lines
    payload["timeline"] = {
        "total_ms": timeline.total_ms,
        "leading_silence_ms": timeline.leading_silence_ms,
        "narration_events": [event.model_dump(mode="json") for event in timeline.narration_events],
    }
    return payload


def shot_at(timeline: EditTimeline, milliseconds: int) -> TimelineEntry | None:
    for entry in timeline.entries:
        if entry.start_ms <= milliseconds < entry.end_ms:
            return entry
    return None


def seconds_to_ms(value: float) -> int:
    return int(round(float(value) * 1000.0))


def frames_for(seconds: float, fps: int) -> int:
    return max(1, int(math.ceil(float(seconds) * fps)))
