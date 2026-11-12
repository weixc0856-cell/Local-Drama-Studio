import pytest
from pydantic import ValidationError

from drama_studio.domain.contracts import Shot, ShotStatus, Storyboard


def _shot(index: int, **overrides):
    data = {
        "shot_id": f"shot_{index:03d}",
        "index": index,
        "character_ids": ["char_001"],
        "location_id": "loc_001",
        "prop_ids": [],
        "duration_seconds": 5,
        "camera": "close-up",
        "action": "男人看着手机，表情逐渐惊讶",
        "dialogue": "喂？",
        "image_prompt": "a man looking at his phone, night, cinematic",
        "video_prompt": "slow push in, phone glow on face",
        "status": "PENDING",
    }
    data.update(overrides)
    return data


def _storyboard(**overrides):
    data = {
        "title": "最后一通电话",
        "logline": "深夜接到去世三年的父亲来电。",
        "duration_target_seconds": 45,
        "style": "cinematic, realistic",
        "characters": [
            {
                "id": "char_001",
                "name": "男主",
                "age": 32,
                "appearance": "黑色短发，深色外套",
                "voice_id": "male_01",
            }
        ],
        "locations": [
            {"id": "loc_001", "name": "公寓客厅", "description": "深夜，只有手机屏幕的光"}
        ],
        "props": [],
        "shots": [_shot(1)],
    }
    data.update(overrides)
    return data


def test_storyboard_accepts_valid_contract() -> None:
    sb = Storyboard(**_storyboard())
    assert sb.shots[0].status is ShotStatus.PENDING


def test_shot_id_must_match_index() -> None:
    with pytest.raises(ValidationError, match="does not match index"):
        Storyboard(**_storyboard(shots=[_shot(1, shot_id="shot_002")]))


def test_unknown_character_reference_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown characters"):
        Storyboard(**_storyboard(shots=[_shot(1, character_ids=["char_999"])]))


def test_duplicate_character_id_rejected() -> None:
    chars = _storyboard()["characters"]
    with pytest.raises(ValidationError, match="duplicate character id"):
        Storyboard(**_storyboard(characters=chars + chars))


def test_extra_fields_rejected() -> None:
    shot = _shot(1)
    shot["surprise"] = 1
    with pytest.raises(ValidationError):
        Shot(**shot)


def test_shot_indexes_must_be_contiguous() -> None:
    with pytest.raises(ValidationError, match="contiguous"):
        Storyboard(**_storyboard(shots=[_shot(1), _shot(3)]))
