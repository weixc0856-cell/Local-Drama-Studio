from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.voice.pronunciation import annotate, line_layers, load_lexicon

ROOT = Path(__file__).resolve().parents[1]


def test_lexicon_covers_the_first_batch() -> None:
    lexicon = load_lexicon(ROOT)
    phrases = {entry.phrase for entry in lexicon.entries}
    required = {
        "扁舟", "似霰", "青枫浦", "宛转", "汀上", "江畔", "不胜愁",
        "徘徊", "捣衣砧", "鸿雁", "鱼龙潜跃", "闲潭", "碣石", "潇湘",
    }
    assert required <= phrases
    assert all(len(entry.phrase) >= 2 for entry in lexicon.entries)
    assert lexicon.capabilities.api_pinyin_control is False


def test_phrase_level_longest_match() -> None:
    lexicon = load_lexicon(ROOT)
    hits = annotate("谁家今夜扁舟子，何处相思明月楼？", lexicon)
    assert [(hit.phrase, hit.pinyin) for hit in hits] == [("扁舟", "piān zhōu")]

    hits = annotate("月照花林皆似霰", lexicon)
    assert [hit.phrase for hit in hits] == ["似霰"]

    hits = annotate("白云一片去悠悠，青枫浦上不胜愁。", lexicon)
    assert [hit.phrase for hit in hits] == ["青枫浦", "不胜愁"]

    hits = annotate("鱼龙潜跃水成文", lexicon)
    assert [hit.phrase for hit in hits] == ["鱼龙潜跃"]


def test_layers_keep_display_and_tts_separate() -> None:
    lexicon = load_lexicon(ROOT)
    line = line_layers(
        {"text": "谁家今夜扁舟子", "subtitle_text": "誰家今夜扁舟子"}, lexicon, 1
    )
    assert line["display_text"] == "誰家今夜扁舟子"
    assert line["tts_text"] == "谁家今夜扁舟子"
    assert line["source_text"] == "誰家今夜扁舟子"
    assert line["display_is_source"] is True
    assert {hit["on"] for hit in line["hits"]} == {"display", "tts"}
    # The annotation never rewrites the text it was given.
    assert line["tts_text"].count("扁舟") == 1


def test_override_phrase_must_occur_in_the_line() -> None:
    lexicon = load_lexicon(ROOT)
    with pytest.raises(ValueError, match="does not occur"):
        line_layers(
            {"text": "白日依山尽", "subtitle_text": "白日依山尽",
             "pronunciation_overrides": [{"phrase": "扁舟", "pinyin": "piān zhōu"}]},
            lexicon,
            1,
        )


def test_traditional_variant_matches_the_same_entry() -> None:
    lexicon = load_lexicon(ROOT)
    hits = annotate("青楓浦上不勝愁", lexicon)
    assert [hit.phrase for hit in hits] == ["青枫浦", "不胜愁"]
    assert [hit.matched for hit in hits] == ["青楓浦", "不勝愁"]
