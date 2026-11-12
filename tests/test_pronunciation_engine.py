from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from drama_studio.domain.voice.pronunciation import (
    Entry,
    build_report,
    line_layers,
    load_lexicon,
    rewrite_acoustic,
)
from drama_studio.domain.voice.recitation import mode_spec, plan_line
from drama_studio.voice.tts import synthesize_narration

ROOT = Path(__file__).resolve().parents[1]


def _wav_bytes(seconds: float = 0.2, rate: int = 22050) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def test_lexicon_exposes_candidate_aliases() -> None:
    lexicon = load_lexicon(ROOT)
    by_phrase = {entry.phrase: entry for entry in lexicon.entries}
    for phrase in ("碣石", "潇湘", "扁舟", "似霰", "青枫浦"):
        entry = by_phrase[phrase]
        assert entry.tts_alias
        assert entry.status == "verified"
        assert entry.audio_test == "PASS"
        assert entry.human_review == "APPROVED"
    # The 胜 reading is checked, but the original audio already reads it
    # correctly; no alias is configured.
    assert by_phrase["不胜愁"].pinyin == "bù shèng chóu"
    assert by_phrase["不胜愁"].tts_alias is None
    assert by_phrase["不胜愁"].audio_test == "PASS"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("碣石潇湘无限路", "节石消湘无限路"),
        ("谁家今夜扁舟子", "谁家今夜偏舟子"),
        ("月照花林皆似霰", "月照花林皆似线"),
        ("青枫浦上不胜愁", "青枫普上不胜愁"),
    ],
)
def test_homophone_rewrite_is_acoustic_only(text: str, expected: str) -> None:
    lexicon = load_lexicon(ROOT)
    acoustic, replacements = rewrite_acoustic(text, lexicon)
    assert acoustic == expected
    assert len(acoustic) == len(text)
    assert replacements
    assert all(item.status == "verified" for item in replacements)


def test_verified_original_phrases_are_not_rewritten() -> None:
    lexicon = load_lexicon(ROOT)
    for text in ("鸿雁长飞光不度", "昨夜闲潭梦落花", "鱼龙潜跃水成文", "捣衣砧上拂还来"):
        acoustic, replacements = rewrite_acoustic(text, lexicon)
        assert acoustic == text
        assert replacements == []


def test_display_text_is_never_rewritten() -> None:
    lexicon = load_lexicon(ROOT)
    line = line_layers(
        {"text": "碣石潇湘无限路", "subtitle_text": "碣石瀟湘無限路"}, lexicon, 1
    )
    assert line["display_text"] == "碣石瀟湘無限路"
    assert line["source_text"] == "碣石瀟湘無限路"
    assert line["tts_text"] == "碣石潇湘无限路"
    assert line["acoustic_text"] == "节石消湘无限路"
    assert line["display_is_source"] is True
    assert line["acoustic_differs"] is True
    aliases = {(item["phrase"], item["alias"]) for item in line["replacements"]}
    assert ("碣石", "节石") in aliases
    assert ("潇湘", "消湘") in aliases


def test_traditional_variant_rewrites_to_simplified_alias() -> None:
    lexicon = load_lexicon(ROOT)
    acoustic, replacements = rewrite_acoustic("青楓浦上不勝愁", lexicon)
    assert acoustic == "青枫普上不勝愁"
    assert [item.matched for item in replacements] == ["青楓浦"]
    assert [item.alias for item in replacements] == ["青枫普"]


def test_longest_match_wins() -> None:
    lexicon = load_lexicon(ROOT)
    acoustic, replacements = rewrite_acoustic("碣石潇湘无限路", lexicon)
    assert acoustic == "节石消湘无限路"
    assert [item.phrase for item in replacements] == ["碣石", "潇湘"]
    assert "".join(item.matched for item in replacements) == "碣石潇湘"


def test_alias_length_must_match_phrase() -> None:
    with pytest.raises(ValidationError, match="same length"):
        Entry(phrase="碣石", pinyin="jié shí", category="proper_noun",
              tts_alias="节石石")


def test_verified_requires_audio_and_human_evidence() -> None:
    with pytest.raises(ValidationError, match="verified requires"):
        Entry(phrase="碣石", pinyin="jié shí", category="proper_noun",
              tts_alias="节石", status="verified")
    entry = Entry(phrase="碣石", pinyin="jié shí", category="proper_noun",
                  tts_alias="节石", status="verified", audio_test="PASS",
                  human_review="APPROVED")
    assert entry.status == "verified"


def test_report_records_all_text_layers() -> None:
    lexicon = load_lexicon(ROOT)
    line = line_layers(
        {"text": "碣石潇湘无限路", "subtitle_text": "碣石瀟湘無限路"}, lexicon, 1
    )
    report = build_report([line], lexicon)
    assert report["lines"][0]["source_text"] == "碣石瀟湘無限路"
    assert report["lines"][0]["display_text"] == "碣石瀟湘無限路"
    assert report["lines"][0]["tts_text"] == "碣石潇湘无限路"
    assert report["lines"][0]["acoustic_text"] == "节石消湘无限路"
    assert report["summary"]["acoustic_changes"] == 2
    assert report["summary"]["verified_aliases"] >= 5
    assert report["summary"]["candidate_aliases"] == 0
    assert report["summary"]["display_equals_source"] is True


def test_classical_recitation_uses_one_line_with_dash_breaths() -> None:
    spec = mode_spec(ROOT, "classical_recitation")
    text = "春江潮水连海平，海上明月共潮生。"
    plan = plan_line(text, spec)
    assert plan["breath_text"] == "春江潮水——连海平，海上明月——共潮生。"
    assert [part["text"] for part in plan["parts"]] == [plan["breath_text"]]
    assert [part["pause_after_ms"] for part in plan["parts"]] == [0]


def test_five_character_line_gets_one_dash_breath() -> None:
    spec = mode_spec(ROOT, "classical_recitation")
    plan = plan_line("床前明月光", spec)
    assert plan["breath_text"] == "床前——明月光"
    assert [part["text"] for part in plan["parts"]] == ["床前——明月光"]


def _root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text(
        'paths: {}\ntts:\n  base_url: "http://tts.test"\n  sample_rate: 48000\n',
        encoding="utf-8",
    )
    (tmp_path / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_audio: "assets/ref.wav"\n'
        '    prompt_text: "参考音"\n    speed: 0.9\n', encoding="utf-8"
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "ref.wav").write_bytes(_wav_bytes())
    (tmp_path / "config" / "pronunciation.yaml").write_text(
        '''schema_version: "2.0"
capabilities:
  api_phoneme_control: false
  api_pinyin_control: false
  pitch_control: false
  duration_control: false
entries:
  - {id: jieshi, phrase: 碣石, pinyin: "jié shí", category: proper_noun, tts_alias: 节石}
  - {id: xiaoxiang, phrase: 潇湘, pinyin: "xiāo xiāng", category: proper_noun, tts_alias: 消湘}
''',
        encoding="utf-8",
    )
    return tmp_path


def test_tts_sends_acoustic_text_to_voxcpm(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    narration = root / "episode" / "narration.json"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_text(json.dumps({
        "speed": 0.9,
        "lines": [{"text": "碣石潇湘", "subtitle_text": "碣石瀟湘"}],
    }, ensure_ascii=False), encoding="utf-8")
    seen: list[str] = []

    def fake(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append(text)
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ready", "model_class": "VoxCPM2",
                "model_dir": "models/voxcpm2", "speakers": [],
                "modes": ["zero_shot"],
            })
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client, force=True,
    )
    assert seen
    assert "节石消湘" in seen[0]
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    line = manifest["lines"][0]
    assert line["display_text"] == "碣石瀟湘"
    assert line["tts_text"] == "碣石潇湘"
    assert line["acoustic_text"] == "节石消湘"
    report = json.loads((result.manifest.parent / "pronunciation_report.json").read_text(encoding="utf-8"))
    assert report["lines"][0]["acoustic_text"] == "节石消湘"
    assert report["summary"]["display_equals_source"] is True
