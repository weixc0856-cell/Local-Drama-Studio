"""Text entry: split, narration, beats and project initialization."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from drama_studio.film.project import load_project, validate_project
from drama_studio.film.script import build_beats, build_bible, build_narration, init_project, split_text

REPO = Path(__file__).resolve().parents[1]


def _install_pack(tmp_path: Path) -> None:
    import shutil
    source = REPO / "config" / "style_packs" / "oriental" / "ink_wash"
    target = tmp_path / "config" / "style_packs" / "oriental" / "ink_wash"
    target.mkdir(parents=True, exist_ok=True)
    for item in source.glob("*.yaml"):
        shutil.copy2(item, target / item.name)


def test_split_poem_keeps_clauses_together() -> None:
    lines = split_text("白日依山尽，黄河入海流。欲穷千里目，更上一层楼。")
    assert lines == ["白日依山尽，黄河入海流。", "欲穷千里目，更上一层楼。"]


def test_split_paragraphs_are_hard_boundaries() -> None:
    text = "庆历四年春，滕子京谪守巴陵郡。\n\n越明年，政通人和，百废具兴。"
    lines = split_text(text)
    assert len(lines) == 2
    assert lines[0].startswith("庆历四年春")
    assert lines[1].startswith("越明年")


def test_long_sentence_is_split_at_clause_punctuation() -> None:
    text = "予观夫巴陵胜状，在洞庭一湖，衔远山，吞长江，浩浩汤汤，横无际涯，朝晖夕阴，气象万千。"
    lines = split_text(text, max_chars=12)
    assert len(lines) > 1
    assert all(len(line) <= 14 for line in lines)


def test_build_narration_assigns_ids_and_pauses() -> None:
    narration = build_narration("p1", ["白日依山尽。", "黄河入海流。"])
    assert [item.id for item in narration.segments] == ["N001", "N002"]
    assert narration.segments[0].pause_after_ms == 900
    assert narration.segments[-1].pause_after_ms == 1200


def test_init_project_writes_a_valid_contract(tmp_path: Path) -> None:
    _install_pack(tmp_path)
    result = init_project(
        tmp_path, "yueyang",
        title="岳阳楼记",
        text="庆历四年春，滕子京谪守巴陵郡。\n\n予观夫巴陵胜状，在洞庭一湖。",
        author="范仲淹",
        dynasty="宋",
        style_id="oriental.ink_wash",
        target_duration_seconds=30,
    )
    assert result["lines"] == 2
    assert result["shots"] == 2
    directory = tmp_path / "projects" / "yueyang"
    for name in ("project.json", "source.json", "screenplay.json", "narration.json",
                 "visual_bible.yaml", "beats.json", "storyboard.json"):
        assert (directory / name).is_file(), name
    report = validate_project(tmp_path, "yueyang")
    assert report["ok"] is True, report
    loaded = load_project(tmp_path, "yueyang")
    assert loaded.style_id == "oriental.ink_wash"
    assert len(loaded.storyboard.shots) == 2


def test_beats_stay_inside_style_camera_moves(tmp_path: Path) -> None:
    from drama_studio.domain.style import get_pack

    _install_pack(tmp_path)
    pack = get_pack(tmp_path, "oriental.ink_wash")
    text = "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。"
    narration = build_narration("p1", split_text(text))
    bible = build_bible("p1", "登鹳雀楼", text, pack)
    beats = build_beats(text, narration, bible, allowed_cameras=list(pack.camera.allowed_moves))
    assert all(beat["move"] in pack.camera.allowed_moves for beat in beats)
    assert all(beat["narration_ids"] for beat in beats)
    assert all(1.0 <= beat["duration_seconds"] <= 12.0 for beat in beats)


def test_video_prompt_does_not_use_ambiguous_crane() -> None:
    from drama_studio.film.prompts import CINEMATIC_VIDEO, build_video_prompt, motion_phrase
    from drama_studio.domain.film.schemas import (
        CameraSpec, ContinuitySpec, Layers, MotionSpec, ShotSpec,
    )

    shot = ShotSpec(
        shot_id="S01", scene_id="SC01", duration_seconds=3.0, shot_size="ews",
        camera=CameraSpec(move="crane"), layers=Layers(background="clouds and river"),
        motion=MotionSpec(primary="camera_descent", secondary=["cloud_drift"]),
        continuity=ContinuitySpec(lighting="dawn", environment="SC01"),
    )
    prompt = build_video_prompt(shot, build_bible("p1", "t", "clouds and river", None))
    assert "crane" not in prompt.lower()
    assert "jib" not in prompt.lower()
    assert "boom" not in prompt.lower()
    assert "hidden rig" in prompt.lower()
    assert "camera_descent" not in prompt
    assert "descends" in prompt
    assert "machinery" in CINEMATIC_VIDEO["crane"].lower() or "jib" in CINEMATIC_VIDEO["crane"].lower()
    assert motion_phrase("camera_descent").startswith("the camera")


def test_validate_warns_when_director_notes_need_cleaning(tmp_path: Path) -> None:
    from drama_studio.film.storyboard import plan_storyboard

    _install_pack(tmp_path)
    directory = tmp_path / "projects" / "p1"
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(json.dumps({"project_id": "p1"}), encoding="utf-8")
    (directory / "narration.json").write_text(json.dumps({
        "project_id": "p1",
        "segments": [{"id": "N001", "text": "黄河入海流（majestic, expansive）"}],
    }, ensure_ascii=False), encoding="utf-8")
    bible = build_bible("p1", "t", "黄河", None)
    (directory / "visual_bible.yaml").write_text(
        yaml.safe_dump(bible.model_dump(mode="json"), allow_unicode=True), encoding="utf-8")
    board = plan_storyboard("p1", build_beats("黄河", build_narration("p1", ["黄河入海流（majestic）"]), bible), bible)
    (directory / "storyboard.json").write_text(
        json.dumps(board.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    report = validate_project(tmp_path, "p1")
    codes = {issue["code"] for issue in report["issues"]}
    assert "spoken_text_cleaned" in codes
