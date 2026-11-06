"""Compile cinematic prompts from a storyboard shot (FILM_PRODUCTION_GUIDE §5)."""

from __future__ import annotations

from .schemas import CameraMove, ShotSize, ShotSpec, VisualBible

SHOT_SIZE_TEXT: dict[ShotSize, str] = {
    ShotSize.EWS: "extreme wide establishing shot",
    ShotSize.WS: "wide shot",
    ShotSize.FS: "full shot of the subject in the environment",
    ShotSize.MS: "medium shot",
    ShotSize.MCU: "medium close-up",
    ShotSize.CU: "close-up",
    ShotSize.ECU: "extreme close-up",
    ShotSize.OTS: "over-the-shoulder shot",
}

CAMERA_TEXT: dict[CameraMove, str] = {
    CameraMove.STATIC: "locked-off camera, no camera movement",
    CameraMove.DOLLY_IN: "slow physical dolly forward toward the subject",
    CameraMove.DOLLY_OUT: "slow physical dolly backward, revealing the space",
    CameraMove.TRACKING: "smooth lateral tracking move",
    CameraMove.PAN: "slow pan following the gaze",
    CameraMove.TILT: "slow tilt revealing height",
    CameraMove.CRANE: "crane move through the space",
    CameraMove.ORBIT: "slow orbit around the subject",
    CameraMove.HANDHELD: "subtle handheld camera",
}


def build_keyframe_prompt(shot: ShotSpec, bible: VisualBible) -> str:
    """One still image prompt; composition, layers and light from the shot."""
    art = bible.art_direction
    parts = [
        f"{art.style}, {art.lighting}",
        SHOT_SIZE_TEXT[shot.shot_size],
        f"{shot.camera.lens_mm}mm lens, {shot.camera.dof} depth of field, {shot.camera.angle} angle",
        f"scene {shot.scene_id}",
    ]
    if shot.layers.foreground:
        parts.append(f"foreground: {shot.layers.foreground}")
    if shot.layers.midground:
        parts.append(f"midground: {shot.layers.midground}")
    if shot.layers.background:
        parts.append(f"background: {shot.layers.background}")
    if art.palette:
        parts.append("palette: " + ", ".join(art.palette))
    if shot.character_in_frame and bible.protagonist.identity:
        parts.append(
            "protagonist: "
            + ", ".join(
                item for item in (
                    bible.protagonist.identity,
                    bible.protagonist.clothing,
                    bible.protagonist.color,
                    bible.protagonist.hair,
                ) if item
            )
        )
    if not shot.character_in_frame:
        parts.append("no people, empty landscape")
    if shot.keyframe_note:
        parts.append(shot.keyframe_note)
    parts.append("portrait 9:16 full-frame composition, no letterbox, no black bars")
    parts.append("no text, no watermark, no lettering")
    return ". ".join(parts)


def build_video_prompt(shot: ShotSpec, bible: VisualBible) -> str:
    """Wan motion prompt; one primary motion plus at most two secondaries."""
    parts = [
        SHOT_SIZE_TEXT[shot.shot_size],
        CAMERA_TEXT[shot.camera.move],
        f"primary motion: {shot.motion.primary}",
    ]
    if shot.motion.secondary:
        parts.append("secondary motion: " + ", ".join(shot.motion.secondary))
    if shot.layers.foreground:
        parts.append(f"foreground: {shot.layers.foreground}")
    if shot.layers.background:
        parts.append(f"background: {shot.layers.background}")
    parts.append(f"lighting: {bible.art_direction.lighting}, consistent direction")
    parts.append(
        "smooth continuous motion, physically plausible, no abrupt changes, "
        "preserve composition and structure, no new characters, no scene transformation"
    )
    return ". ".join(parts)


def compile_shot_prompts(shot: ShotSpec, bible: VisualBible) -> dict[str, str]:
    return {
        "keyframe_prompt": build_keyframe_prompt(shot, bible),
        "video_prompt": build_video_prompt(shot, bible),
    }
