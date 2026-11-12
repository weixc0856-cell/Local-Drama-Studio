"""Spoken-text cleaning: director notes must never reach TTS."""

from __future__ import annotations

import pytest

from drama_studio.domain.film.text import TextCleanError, clean_spoken_text


def test_removes_parenthesised_director_notes() -> None:
    audit = clean_spoken_text("黄河入海流（majestic, expansive）", language="zh-CN")
    assert audit.cleaned == "黄河入海流"
    assert "majestic" in audit.removed[0]


def test_removes_latin_words_from_chinese_lines() -> None:
    audit = clean_spoken_text("欲穷千里目, contemplative, slower", language="zh-CN")
    assert audit.cleaned == "欲穷千里目"
    assert "contemplative" in audit.latin_removed


def test_keeps_latin_for_english_projects() -> None:
    audit = clean_spoken_text("It was the best of times.", language="en")
    assert audit.cleaned == "It was the best of times"


def test_removes_title_markers_but_keeps_title() -> None:
    audit = clean_spoken_text("《登鹳雀楼》", language="zh-CN")
    assert audit.cleaned == "登鹳雀楼"


def test_empty_after_cleaning_is_an_error() -> None:
    with pytest.raises(TextCleanError):
        clean_spoken_text("(solemn, calm)", language="zh-CN")


def test_narration_render_text_has_no_prefix() -> None:
    from drama_studio.domain.film.schemas import NarrationSegment
    from drama_studio.application.film.voice import render_text

    segment = NarrationSegment(id="N001", text="白日依山尽。", emotion="open", delivery="gentle")
    assert render_text(segment) == "白日依山尽"
