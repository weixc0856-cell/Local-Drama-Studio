"""Shot continuity checks (FILM_PRODUCTION_GUIDE §6)."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import Narration, Storyboard


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    shot_id: str
    message: str


def check_continuity(storyboard: Storyboard, narration: Narration | None = None) -> list[Issue]:
    issues: list[Issue] = []
    known_narration = narration.ids() if narration is not None else None

    for shot in storyboard.shots:
        if known_narration is not None:
            for item in shot.narration_ids:
                if item not in known_narration:
                    issues.append(Issue("error", "narration_missing", shot.shot_id,
                                        f"narration id {item!r} not found in narration.json"))
        if shot.continuity.match_cut_to is not None and shot.continuity.match_cut_to not in storyboard.ids():
            issues.append(Issue("error", "match_cut_unknown", shot.shot_id,
                                f"match_cut_to {shot.continuity.match_cut_to!r} is not a known shot"))
        if shot.motion.primary == "camera_zoom":
            issues.append(Issue("error", "fake_camera_move", shot.shot_id,
                                "digital zoom is not a cinematic camera move; use dolly_in/out"))

    by_scene: dict[str, list] = {}
    for shot in storyboard.shots:
        by_scene.setdefault(shot.scene_id, []).append(shot)
    for scene_id, shots in by_scene.items():
        lighting = {shot.continuity.lighting for shot in shots}
        environment = {shot.continuity.environment for shot in shots}
        if len(lighting) > 1:
            issues.append(Issue("error", "lighting_drift", shots[0].shot_id,
                                f"scene {scene_id} mixes lighting {sorted(lighting)}"))
        if len(environment) > 1:
            issues.append(Issue("error", "environment_drift", shots[0].shot_id,
                                f"scene {scene_id} mixes environments {sorted(environment)}"))

    for previous, current in zip(storyboard.shots, storyboard.shots[1:]):
        left = previous.continuity.motion_direction
        right = current.continuity.motion_direction
        if {left, right} == {"left_to_right", "right_to_left"} and current.continuity.match_cut_to is None:
            issues.append(Issue("warning", "motion_flip", current.shot_id,
                                f"motion direction flips {left} -> {right} without a match cut"))
        if previous.shot_size == current.shot_size and current.continuity.match_cut_to is None:
            issues.append(Issue(
                "warning", "same_shot_size", current.shot_id,
                f"adjacent shots are both {current.shot_size.value}; use a size ladder or a match cut"))
        left_move = previous.camera.move.value
        right_move = current.camera.move.value
        if (left_move, right_move) in (("dolly_in", "dolly_out"), ("dolly_out", "dolly_in"),
                                       ("pan", "pan"), ("tracking", "tracking")):
            if current.continuity.match_cut_to is None and left == right:
                pass
            elif current.continuity.match_cut_to is None:
                issues.append(Issue(
                    "warning", "camera_vector_jump", current.shot_id,
                    f"camera vector changes {left_move} -> {right_move} without a match cut"))
        if previous.continuity.character_state != current.continuity.character_state \
                and previous.scene_id == current.scene_id:
            issues.append(Issue("warning", "character_state_jump", current.shot_id,
                                f"character_state changes {previous.continuity.character_state!r} -> "
                                f"{current.continuity.character_state!r} inside scene {current.scene_id}"))

    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(item.level == "error" for item in issues)
