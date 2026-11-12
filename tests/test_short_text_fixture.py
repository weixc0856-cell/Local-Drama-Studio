from __future__ import annotations

from pathlib import Path

from drama_studio.application.voice.timeline import build_timeline, leading_silence_for

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "literary_intelligence" / "tests" / "fixtures" / "corpus_short"
SHORT_TEXT = "白日依山尽"


def test_short_fixture_is_replaceable_and_short() -> None:
    normalized = (CORPUS / "normalized_text.txt").read_text(encoding="utf-8")
    assert SHORT_TEXT in normalized
    assert len(normalized.strip()) <= 20
    assert (CORPUS / "source_registry.json").is_file()
    assert (CORPUS / "claims.json").is_file()


def test_timeline_accepts_short_text() -> None:
    timeline = build_timeline(
        [{"segment_id": "line_01", "duration": 2.0, "subtitle_text": SHORT_TEXT}],
        leading_silence_for("poetry"),
    )
    event = timeline["segments"][0]
    assert timeline["leading_silence_ms"] == 400
    assert event["speech_start_ms"] == 400
    assert event["subtitle_text"] == SHORT_TEXT
    assert event["subtitle_start_ms"] >= timeline["leading_silence_ms"]
