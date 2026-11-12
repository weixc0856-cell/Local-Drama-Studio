"""Script-to-Film contracts: schemas, planning, continuity, timeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.film import (
    CameraMove,
    CameraSpec,
    ContinuitySpec,
    GenerationSpec,
    Layers,
    MotionSpec,
    Narration,
    NarrationSegment,
    ShotSize,
    ShotSpec,
    Storyboard,
    Transition,
    VisualBible,
    build_timeline,
    check_continuity,
    has_errors,
    plan_storyboard,
)
from drama_studio.film.schemas import ArtDirection, CameraLanguage, CharacterDesign, EnvironmentDesign


def _bible() -> VisualBible:
    return VisualBible(
        project_id="p1",
        art_direction=ArtDirection(style="ink", lighting="golden_hour", palette=["warm"]),
        protagonist=CharacterDesign(identity="poet"),
        environment=EnvironmentDesign(landscape="mountains_river"),
        camera_language=CameraLanguage(),
    )


def _narration(*ids: str) -> Narration:
    return Narration(
        project_id="p1",
        segments=[NarrationSegment(id=item, text=f"line {item}") for item in ids],
    )


def _shot(shot_id: str, previous: str | None, following: str | None, **kwargs) -> ShotSpec:
    defaults = dict(
        scene_id="SC01",
        narration_ids=[],
        duration_seconds=5.0,
        shot_size=ShotSize.WS,
        camera=CameraSpec(move=CameraMove.STATIC),
        layers=Layers(midground="ridge"),
        motion=MotionSpec(primary="environment_drift"),
        continuity=ContinuitySpec(
            previous_shot=previous,
            next_shot=following,
            lighting="golden_hour",
            environment="mountains_river",
        ),
        generation=GenerationSpec(),
    )
    defaults.update(kwargs)
    return ShotSpec(shot_id=shot_id, **defaults)


def _beats(count: int = 2) -> list[dict]:
    return [
        {
            "scene_id": "SC01",
            "duration_seconds": 5,
            "shot_size": "ws",
            "motion_primary": "environment_drift",
            "midground": "ridge",
        }
        for _ in range(count)
    ]


def test_storyboard_requires_sequential_ids_and_chain() -> None:
    with pytest.raises(ValueError, match="next_shot"):
        Storyboard(project_id="p1", shots=[_shot("S01", None, None), _shot("S02", "S01", None)])

    first = _shot("S01", None, "S02")
    second = _shot("S02", "S01", None)
    board = Storyboard(project_id="p1", shots=[first, second])
    assert board.ids() == ["S01", "S02"]


def test_storyboard_rejects_broken_previous_link() -> None:
    first = _shot("S01", "S09", "S02")
    second = _shot("S02", "S01", None)
    with pytest.raises(ValueError, match="previous_shot"):
        Storyboard(project_id="p1", shots=[first, second])


def test_plan_storyboard_chains_and_inherits_lighting() -> None:
    board = plan_storyboard("p1", _beats(3), _bible())
    assert [shot.shot_id for shot in board.shots] == ["S01", "S02", "S03"]
    assert board.shots[0].continuity.previous_shot is None
    assert board.shots[0].continuity.next_shot == "S02"
    assert board.shots[-1].continuity.next_shot is None
    assert {shot.continuity.lighting for shot in board.shots} == {"golden_hour"}


def test_plan_storyboard_requires_motion_primary() -> None:
    beats = _beats(1)
    beats[0].pop("motion_primary")
    with pytest.raises(ValueError, match="motion_primary"):
        plan_storyboard("p1", beats, _bible())


def test_continuity_detects_lighting_drift_and_missing_narration() -> None:
    first = _shot("S01", None, "S02")
    second = _shot(
        "S02", "S01", None,
        narration_ids=["N999"],
        continuity=ContinuitySpec(
            previous_shot="S01", next_shot=None, lighting="midday", environment="mountains_river"
        ),
    )
    issues = check_continuity(Storyboard(project_id="p1", shots=[first, second]), _narration("N001"))
    codes = {item.code for item in issues}
    assert "lighting_drift" in codes
    assert "narration_missing" in codes
    assert has_errors(issues)


def test_continuity_flags_digital_zoom_and_motion_flip() -> None:
    first = _shot("S01", None, "S02", motion=MotionSpec(primary="camera_zoom"))
    second = _shot(
        "S02", "S01", None,
        continuity=ContinuitySpec(
            previous_shot="S01", next_shot=None, lighting="golden_hour",
            environment="mountains_river", motion_direction="left_to_right",
        ),
    )
    first.continuity.motion_direction = "right_to_left"
    issues = check_continuity(Storyboard(project_id="p1", shots=[first, second]))
    codes = {item.code for item in issues}
    assert "fake_camera_move" in codes
    assert "motion_flip" in codes
    # motion flip alone is a warning, not an error
    assert has_errors([item for item in issues if item.code == "fake_camera_move"])


def test_timeline_is_contiguous_and_marks_match_cut() -> None:
    first = _shot("S01", None, "S02")
    second = _shot(
        "S02", "S01", None,
        continuity=ContinuitySpec(
            previous_shot="S01", next_shot=None, lighting="golden_hour",
            environment="mountains_river", match_cut_to="S01",
        ),
    )
    timeline = build_timeline(Storyboard(project_id="p1", shots=[first, second]))
    assert timeline.total_ms == 10000
    assert timeline.entries[0].start_ms == 0 and timeline.entries[0].end_ms == 5000
    assert timeline.entries[1].start_ms == 5000
    assert timeline.entries[1].transition_in == Transition.MATCH_CUT


def test_narration_ids_must_be_unique() -> None:
    with pytest.raises(ValueError):
        Narration(
            project_id="p1",
            segments=[NarrationSegment(id="N001", text="a"), NarrationSegment(id="N001", text="b")],
        )


def test_layers_require_at_least_one_depth() -> None:
    with pytest.raises(ValueError):
        Layers()


def test_keyframe_and_video_prompts_follow_the_guide() -> None:
    from drama_studio.film import build_keyframe_prompt, build_video_prompt

    board = plan_storyboard("p1", _beats(1), _bible())
    shot = board.shots[0]
    keyframe = build_keyframe_prompt(shot, _bible())
    assert "golden_hour" in keyframe
    assert "midground: ridge" in keyframe
    assert "no text" in keyframe

    video = build_video_prompt(shot, _bible())
    assert "primary motion: clouds and mist drift" in video
    assert "no new characters" in video
    assert "preserve composition" in video


def test_secondary_motion_is_capped_at_two() -> None:
    from drama_studio.film import MotionSpec

    with pytest.raises(ValueError):
        MotionSpec(primary="camera_forward", secondary=["a", "b", "c"])


def test_character_flag_controls_keyframe_prompt() -> None:
    from drama_studio.film import build_keyframe_prompt

    beats = _beats(1)
    beats[0]["character_in_frame"] = False
    shot = plan_storyboard("p1", beats, _bible()).shots[0]
    prompt = build_keyframe_prompt(shot, _bible())
    assert "no people, empty landscape" in prompt
    assert "protagonist:" not in prompt


def test_continuity_flags_same_shot_size_and_camera_vector_jump() -> None:
    from drama_studio.film.schemas import (
        CameraSpec, ContinuitySpec, Layers, MotionSpec, ShotSpec, Storyboard,
    )

    def shot(shot_id: str, size: str, move: str, previous: str | None, nxt: str | None):
        return ShotSpec(
            shot_id=shot_id, scene_id="SC01", duration_seconds=3.0, shot_size=size,
            camera=CameraSpec(move=move), layers=Layers(midground="ridge"),
            motion=MotionSpec(primary="camera_push_in"),
            continuity=ContinuitySpec(
                lighting="dawn", environment="SC01",
                previous_shot=previous, next_shot=nxt,
                motion_direction="toward_camera" if move == "dolly_in" else "away_from_camera"),
        )

    board = Storyboard(project_id="p", shots=[
        shot("S01", "ws", "dolly_in", None, "S02"),
        shot("S02", "ws", "dolly_out", "S01", None),
    ])
    codes = {issue.code for issue in check_continuity(board)}
    assert "same_shot_size" in codes
    assert "camera_vector_jump" in codes
