"""Storyboard planning from authored beats (FILM_PRODUCTION_GUIDE §4–§5)."""

from __future__ import annotations

from typing import Any

from .schemas import (
    CameraSpec,
    ContinuitySpec,
    Layers,
    MotionSpec,
    ShotSpec,
    Storyboard,
    VisualBible,
)

REQUIRED_BEAT_KEYS = ("scene_id", "duration_seconds", "shot_size", "motion_primary")


def _require(beat: dict[str, Any], key: str, index: int) -> Any:
    if key not in beat:
        raise ValueError(f"beat {index}: missing required key {key!r}")
    return beat[key]


def plan_storyboard(project_id: str, beats: list[dict[str, Any]], bible: VisualBible) -> Storyboard:
    """Turn authored beats into a validated storyboard.

    Beats are the director's decisions; this function only enforces the contract,
    fills continuity defaults and chains previous/next shot ids.
    """
    if not beats:
        raise ValueError("at least one beat is required")

    default_lighting = bible.art_direction.lighting
    default_environment = (
        bible.environment.landscape or bible.environment.architecture or bible.art_direction.style
    )
    previous_lighting = default_lighting
    previous_environment = default_environment
    previous_state = "none"

    shots: list[ShotSpec] = []
    for index, beat in enumerate(beats, start=1):
        _require(beat, "scene_id", index)
        _require(beat, "duration_seconds", index)
        _require(beat, "shot_size", index)
        _require(beat, "motion_primary", index)

        lighting = str(beat.get("lighting") or previous_lighting)
        environment = str(beat.get("environment") or previous_environment)
        character_state = str(beat.get("character_state") or previous_state)

        shot = ShotSpec(
            shot_id=f"S{index:02d}",
            scene_id=str(beat["scene_id"]),
            narration_ids=[str(item) for item in beat.get("narration_ids", [])],
            character_in_frame=bool(beat.get("character_in_frame", True)),
            keyframe_note=beat.get("keyframe_note"),
            duration_seconds=float(beat["duration_seconds"]),
            shot_size=beat["shot_size"],
            camera=CameraSpec(
                move=beat.get("move", "static"),
                angle=str(beat.get("angle", "eye")),
                lens_mm=int(beat.get("lens_mm", 35)),
                dof=beat.get("dof", "deep"),
            ),
            layers=Layers(
                foreground=str(beat.get("foreground", "")),
                midground=str(beat.get("midground", "")),
                background=str(beat.get("background", "")),
            ),
            motion=MotionSpec(
                primary=str(beat["motion_primary"]),
                secondary=[str(item) for item in beat.get("secondary", [])],
            ),
            continuity=ContinuitySpec(
                lighting=lighting,
                environment=environment,
                character_state=character_state,
                motion_direction=beat.get("motion_direction", "static"),
                match_cut_to=beat.get("match_cut_to"),
            ),
        )
        shots.append(shot)
        previous_lighting, previous_environment, previous_state = lighting, environment, character_state

    chained: list[ShotSpec] = []
    for index, shot in enumerate(shots):
        continuity = shot.continuity.model_copy(
            update={
                "previous_shot": shots[index - 1].shot_id if index > 0 else None,
                "next_shot": shots[index + 1].shot_id if index + 1 < len(shots) else None,
            }
        )
        chained.append(shot.model_copy(update={"continuity": continuity}))

    return Storyboard(project_id=project_id, shots=chained)
