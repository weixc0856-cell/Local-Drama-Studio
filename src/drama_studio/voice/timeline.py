"""Pure timeline rules for R3-D voice production.

All internal times are integer milliseconds.

Segment input:
  {"segment_id": "P01", "duration": 3.053, "pause_after_ms": 300,
   "subtitle_text": "..."}

The leading silence is added exactly once at the start of the full audio.
Subtitles never start before the corresponding speech, and never include the
leading silence.

speech_start_ms / speech_end_ms are planned boundaries derived from the design
timeline and segment durations. They are not VAD output and must not be
described as measured or detected speech boundaries.

Each event has:
  audio_start_ms / audio_end_ms: segment slot in the full audio; audio_end_ms
    includes that segment's trailing pause.
  speech_start_ms / speech_end_ms: voiced part only.
  subtitle_start_ms / subtitle_end_ms: display interval, never in leading silence.
"""

from __future__ import annotations

from pathlib import Path

import pysubs2


def build_timeline(
    segments: list[dict],
    leading_silence_ms: int,
    subtitle_tail_ms: int = 200,
    subtitle_gap_ms: int = 50,
) -> dict:
    if leading_silence_ms < 0:
        raise ValueError("leading_silence_ms must be >= 0")
    cursor = int(leading_silence_ms)
    events: list[dict] = []
    for i, seg in enumerate(segments):
        duration_ms = int(round(float(seg["duration"]) * 1000))
        if duration_ms <= 0:
            raise ValueError(f"{seg['segment_id']}: duration must be > 0")
        speech_start = cursor
        speech_end = speech_start + duration_ms
        pause_after = int(seg.get("pause_after_ms", 0))
        if pause_after < 0:
            raise ValueError(f"{seg['segment_id']}: pause_after_ms must be >= 0")
        next_speech = speech_end + pause_after
        if i < len(segments) - 1:
            sub_end = min(speech_end + subtitle_tail_ms, next_speech - subtitle_gap_ms)
        else:
            sub_end = speech_end + subtitle_tail_ms
        sub_end = max(sub_end, speech_end)
        events.append({
            "segment_id": seg["segment_id"],
            "audio_start_ms": speech_start,
            "audio_end_ms": next_speech,
            "speech_start_ms": speech_start,
            "speech_end_ms": speech_end,
            "pause_after_ms": pause_after,
            "subtitle_start_ms": speech_start,
            "subtitle_end_ms": sub_end,
            "subtitle_text": seg.get("subtitle_text", ""),
            "leading_silence_ms": int(leading_silence_ms),
        })
        cursor = next_speech
    return {
        "audio_start_ms": 0,
        "audio_end_ms": cursor,
        "leading_silence_ms": int(leading_silence_ms),
        "segments": events,
    }


def pad_timeline_to(timeline: dict, total_ms: int) -> dict:
    """Pad the final audio with trailing silence to match the visual duration.

    The voice events and subtitles are unchanged. The returned timeline keeps
    the unpadded voice end separately so callers can audit the padding.
    """
    if total_ms < 0:
        raise ValueError("total_ms must be >= 0")
    voice_end = int(timeline["audio_end_ms"])
    if total_ms < voice_end:
        raise ValueError(
            f"total_ms {total_ms} is shorter than voice end {voice_end}; "
            "extend visuals or shorten pauses first"
        )
    padded = dict(timeline)
    padded["voice_end_ms"] = voice_end
    padded["trailing_silence_ms"] = total_ms - voice_end
    padded["audio_end_ms"] = int(total_ms)
    return padded


def make_srt(timeline: dict, path: Path) -> None:
    subs = pysubs2.SSAFile()
    for event in timeline["segments"]:
        text = event["subtitle_text"].replace("\n", "\\N")
        subs.append(pysubs2.SSAEvent(
            start=pysubs2.make_time(ms=event["subtitle_start_ms"]),
            end=pysubs2.make_time(ms=event["subtitle_end_ms"]),
            text=text,
        ))
    subs.save(str(path))


def leading_silence_for(content_type: str) -> int:
    defaults = {"poetry": 400, "narration": 300, "mixed": 350}
    if content_type not in defaults:
        raise ValueError(f"unknown content_type: {content_type}")
    return defaults[content_type]
