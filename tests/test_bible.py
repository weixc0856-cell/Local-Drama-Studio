from __future__ import annotations

import json
from pathlib import Path

import yaml

from drama_studio.domain.bible import check_story_bibles, load_character_bible, load_shot_bible


def _script(path: Path, shots: int = 2, style: str = "ink_wash") -> Path:
    payload = {
        "schema_version": "1.0",
        "title": "测试",
        "logline": "测试用",
        "style_id": style,
        "shots": [
            {"shot_id": f"shot_{index:03d}", "index": index}
            for index in range(1, shots + 1)
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _characters(path: Path, voice: str | None = None) -> Path:
    payload = {
        "schema_version": "1.0",
        "style_id": "ink_wash",
        "characters": [
            {
                "character_id": "char_001",
                "name": "渔翁",
                "visual_anchors": ["灰白短须", "斗笠压眉", "青灰蓑衣"],
                "costume": "青灰蓑衣",
                "voice_profile_id": voice,
            }
        ],
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def _shots(path: Path, extra_character: str | None = None) -> Path:
    payload = {
        "schema_version": "1.0",
        "style_id": "ink_wash",
        "shots": [
            {"shot_id": "shot_001", "index": 1, "location_id": "loc_001",
             "character_ids": ["char_001"], "wardrobe_state": "蓑衣被雨打湿"},
            {"shot_id": "shot_002", "index": 2, "location_id": "loc_001",
             "character_ids": ["char_001"] + ([extra_character] if extra_character else [])},
        ],
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def _voices(path: Path, status: str = "APPROVED") -> Path:
    payload = {
        "schema_version": "1.0",
        "default_profile": "narrator_self",
        "profiles": [{
            "profile_id": "narrator_self", "display_name": "旁白",
            "tts_mode": "zero_shot",
            "prompt_audio": "prompt.wav", "prompt_text": "参考文本",
            "status": status, "commercial_allowed": True,
            "license_evidence": "rights.md",
        }],
    }
    (path.parent / "prompt.wav").write_bytes(b"RIFF0000WAVE")
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def test_valid_bibles_pass(tmp_path: Path) -> None:
    report = check_story_bibles(
        _script(tmp_path / "script.json"),
        _characters(tmp_path / "characters.yaml"),
        _shots(tmp_path / "shots.yaml"),
    )
    assert report["status"] == "PASS"
    assert report["same_face_guarantee"] is False
    assert report["voice_check"]["status"] == "SKIPPED"


def test_unknown_character_fails(tmp_path: Path) -> None:
    report = check_story_bibles(
        _script(tmp_path / "script.json"),
        _characters(tmp_path / "characters.yaml"),
        _shots(tmp_path / "shots.yaml", extra_character="char_999"),
    )
    assert report["status"] == "FAIL"
    assert any("char_999" in error for error in report["errors"])


def test_missing_scripted_shot_fails(tmp_path: Path) -> None:
    report = check_story_bibles(
        _script(tmp_path / "script.json", shots=3),
        _characters(tmp_path / "characters.yaml"),
        _shots(tmp_path / "shots.yaml"),
    )
    assert report["status"] == "FAIL"
    assert any("missing scripted shots" in error for error in report["errors"])


def test_style_mismatch_fails(tmp_path: Path) -> None:
    report = check_story_bibles(
        _script(tmp_path / "script.json", style="court_green_fine_line"),
        _characters(tmp_path / "characters.yaml"),
        _shots(tmp_path / "shots.yaml"),
    )
    assert report["status"] == "FAIL"
    assert any("style_id" in error for error in report["errors"])


def test_voice_profile_must_be_approved(tmp_path: Path) -> None:
    voices = _voices(tmp_path / "voices.yaml", status="TECHNICALLY_VALIDATED")
    report = check_story_bibles(
        _script(tmp_path / "script.json"),
        _characters(tmp_path / "characters.yaml", voice="narrator_self"),
        _shots(tmp_path / "shots.yaml"),
        voices_path=voices,
    )
    assert report["status"] == "FAIL"
    assert report["voice_check"]["status"] == "FAIL"


def test_approved_voice_profile_passes(tmp_path: Path) -> None:
    voices = _voices(tmp_path / "voices.yaml")
    report = check_story_bibles(
        _script(tmp_path / "script.json"),
        _characters(tmp_path / "characters.yaml", voice="narrator_self"),
        _shots(tmp_path / "shots.yaml"),
        voices_path=voices,
    )
    assert report["status"] == "PASS"
    assert report["voice_check"]["status"] == "PASS"


def test_bible_loaders_are_strict(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: '1.0'\ncharacters: []\n", encoding="utf-8")
    try:
        load_character_bible(bad)
    except Exception as exc:  # noqa: BLE001
        assert "character bible" in str(exc)
    else:
        raise AssertionError("empty character bible should fail")

    shots = _shots(tmp_path / "shots.yaml")
    assert load_shot_bible(shots).shots[1].index == 2
