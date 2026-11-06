"""Edit timeline construction (FILM_PRODUCTION_GUIDE §8)."""

from __future__ import annotations

from .schemas import EditTimeline, Storyboard, TimelineEntry, Transition


def build_timeline(storyboard: Storyboard, sample_rate: int = 48000) -> EditTimeline:
    entries: list[TimelineEntry] = []
    cursor = 0
    for index, shot in enumerate(storyboard.shots):
        duration_ms = int(round(shot.duration_seconds * 1000))
        previous = storyboard.shots[index - 1] if index > 0 else None
        transition_in = (
            Transition.MATCH_CUT
            if previous is not None and shot.continuity.match_cut_to == previous.shot_id
            else Transition.CUT
        )
        transition_out = Transition.MATCH_CUT if shot.continuity.match_cut_to else Transition.CUT
        entries.append(
            TimelineEntry(
                shot_id=shot.shot_id,
                start_ms=cursor,
                end_ms=cursor + duration_ms,
                narration_ids=list(shot.narration_ids),
                visual_asset=None,
                transition_in=transition_in,
                transition_out=transition_out,
            )
        )
        cursor += duration_ms
    return EditTimeline(
        project_id=storyboard.project_id,
        sample_rate=sample_rate,
        entries=entries,
        total_ms=cursor,
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
