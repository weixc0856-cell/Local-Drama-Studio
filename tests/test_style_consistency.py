from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from drama_studio.application.style_consistency import StyleConsistencyError, check_style_consistency


def _solid(path: Path, color: tuple[int, int, int], size=(320, 320)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def _shots(tmp_path: Path, colors: list[tuple[int, int, int]]) -> list[tuple[str, Path]]:
    return [
        (f"shot_{index:03d}", _solid(tmp_path / f"shot_{index:03d}.png", color))
        for index, color in enumerate(colors, start=1)
    ]


def test_same_palette_is_technically_ok_but_needs_review(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (237, 228, 211)])
    report = check_style_consistency(shots, style_id="ink_wash")
    assert report["technical_status"] == "OK"
    assert report["aesthetic_status"] == "PENDING_HUMAN_REVIEW"
    assert report["overall_status"] == "PARTIAL"
    assert report["flags"] == []


def test_human_approval_is_required_for_pass(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (237, 228, 211)])
    report = check_style_consistency(
        shots, style_id="ink_wash", review_status="APPROVED", review_note="人工审片通过")
    assert report["overall_status"] == "PASS_VERIFIED"
    assert report["aesthetic_status"] == "APPROVED"


def test_strong_cross_shot_color_jump_is_a_failure(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (220, 20, 20)])
    report = check_style_consistency(shots, style_id="ink_wash")
    assert report["technical_status"] == "RISK"
    assert report["overall_status"] == "FAIL"
    assert any(flag["code"] in {"cross_shot_color", "palette_distance"} for flag in report["flags"])


def test_rejected_review_fails_even_when_technical_ok(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (237, 228, 211)])
    report = check_style_consistency(shots, style_id="ink_wash", review_status="REJECTED")
    assert report["technical_status"] == "OK"
    assert report["overall_status"] == "FAIL"


def test_one_shot_is_not_enough(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211)])
    with pytest.raises(StyleConsistencyError, match="at least two"):
        check_style_consistency(shots, style_id="ink_wash")


def test_missing_image_is_loud(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (237, 228, 211)])
    missing = [shots[0], ("shot_999", tmp_path / "missing.png")]
    with pytest.raises(StyleConsistencyError, match="not found"):
        check_style_consistency(missing, style_id="ink_wash")


def test_report_is_json_serialisable(tmp_path: Path) -> None:
    shots = _shots(tmp_path, [(237, 228, 211), (237, 228, 211)])
    report = check_style_consistency(shots, style_id="ink_wash")
    json.dumps(report, ensure_ascii=False)
    assert report["shot_count"] == 2
    assert len(report["pairs"]) == 1
