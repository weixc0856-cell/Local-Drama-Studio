"""Compile cinematic prompts from a storyboard shot (FILM_PRODUCTION_GUIDE §5)."""

from __future__ import annotations

from drama_studio.domain.film.schemas import CameraMove, ShotSize, ShotSpec, VisualBible

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
    CameraMove.CRANE: "camera rises or descends smoothly on a hidden rig, continuous speed, no equipment in frame",
    CameraMove.ORBIT: "slow orbit around the subject",
    CameraMove.HANDHELD: "subtle handheld camera",
}


# Wan needs camera motion, speed and viewpoint in the first tokens. The
# keyframe prompt uses CAMERA_TEXT; the video prompt uses this vocabulary.
CINEMATIC_VIDEO = {
    CameraMove.STATIC: "locked-off camera with continuous atmospheric motion only, no subject displacement",
    CameraMove.DOLLY_IN: "smooth forward camera dolly, slow steady push toward the subject, no drone or vehicle visible",
    CameraMove.DOLLY_OUT: "smooth backward camera dolly revealing the space, no machinery visible",
    CameraMove.TRACKING: "slow sweeping lateral tracking shot, steady speed, parallax between foreground and distance",
    CameraMove.PAN: "slow sweeping pan from a high vantage point, constant speed, horizon steady",
    CameraMove.TILT: "smooth camera tilt, continuous vertical reveal, no whip",
    CameraMove.CRANE: "smooth vertical camera descent on a hidden rig, continuous speed, no machinery visible",
    CameraMove.ORBIT: "slow cinematic orbit around the subject, constant radius",
    CameraMove.HANDHELD: "subtle handheld documentary camera, gentle breathing motion, no shake",
}

CAMERA_STILL = {
    CameraMove.STATIC: "locked-off view, balanced composition",
    CameraMove.DOLLY_IN: "view from a slightly elevated forward vantage",
    CameraMove.DOLLY_OUT: "wide vantage revealing layered depth",
    CameraMove.TRACKING: "lateral vantage with foreground, midground and distance",
    CameraMove.PAN: "wide panoramic vantage, horizon level",
    CameraMove.TILT: "low vantage looking upward through the space",
    CameraMove.CRANE: "high vantage looking down through layered space",
    CameraMove.ORBIT: "three-quarter vantage around the subject",
    CameraMove.HANDHELD: "eye-level documentary vantage",
}

# The storyboard stores code-like motion ids. Wan reads natural language and has
# interpreted ``camera_descent`` / ``crane`` as physical machinery, so every id
# is expanded before it reaches the model.
MOTION_PHRASE = {
    "camera_descent": "the camera descends slowly and continuously",
    "camera_push_in": "the camera pushes in slowly",
    "camera_pull_out": "the camera pulls back slowly",
    "camera_lateral": "the camera moves laterally at a steady speed",
    "camera_follow": "the camera follows the subject smoothly",
    "camera_tilt_up": "the camera tilts upward slowly",
    "camera_forward": "the camera advances smoothly",
    "environment_drift": "clouds and mist drift continuously; the camera is almost still",
}

FILM_NEGATIVE = (
    "construction crane, mechanical arm, metal pipes, machinery, industrial equipment, "
    "text, watermark, logo, deformed architecture, duplicated structures, flicker, morphing, warping"
)


def motion_phrase(value: str) -> str:
    return MOTION_PHRASE.get(value, value.replace("_", " "))

PHYSICAL_MOTION = (
    (("江", "河", "湖", "海", "水", "波", "浪", "流", "river", "water", "wave", "sea"),
     "river water flows downstream with visible ripples, current and moving reflections"),
    (("云", "雾", "霭", "烟", "cloud", "mist", "fog", "sky"),
     "cloud bands drift across the frame; mist curls, thins and dissipates"),
    (("风", "树", "木", "草", "竹", "柳", "枝", "wind", "tree", "branch", "reed"),
     "foliage and branches sway in a steady wind, robe hems lift slightly"),
    (("日", "月", "光", "晖", "阳", "sun", "light", "sunset"),
     "sunlight shifts across cloud edges and water, shadows lengthen slowly"),
    (("楼", "阁", "亭", "宫", "台", "栏", "tower", "pavilion", "eaves", "railing"),
     "camera glides along the eaves with parallax between railing and distant peaks"),
)


def physical_motion_for(shot: ShotSpec) -> str:
    """Explicit physical verbs for Wan, derived from the shot's own layers.

    A style prompt such as "ink diffusion" describes a look; Wan also needs to
    know what physically moves. These verbs are generic physics, not new style
    claims, and are capped to two so motion does not stack.
    """
    text = " ".join([
        shot.layers.foreground, shot.layers.midground, shot.layers.background,
        shot.motion.primary, " ".join(shot.motion.secondary),
    ])
    found = [phrase for words, phrase in PHYSICAL_MOTION
             if any(word in text for word in words)]
    return "; ".join(found[:2])


def cinematic_video_prefix(shot: ShotSpec) -> str:
    """First-token camera/speed/viewpoint phrase for a style-pack Wan prompt."""
    return CINEMATIC_VIDEO[shot.camera.move]


def build_keyframe_prompt(shot: ShotSpec, bible: VisualBible) -> str:
    """One still image prompt; composition, layers and light from the shot."""
    art = bible.art_direction
    parts = [
        f"{art.style}, {art.lighting}",
        SHOT_SIZE_TEXT[shot.shot_size],
        f"{CAMERA_STILL[shot.camera.move]}, {shot.camera.lens_mm}mm lens, {shot.camera.dof} depth of field, {shot.camera.angle} angle",
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
    parts.append("landscape 16:9 full-frame composition, no letterbox, no black bars")
    parts.append("no text, no watermark, no lettering")
    return ". ".join(parts)


def build_video_prompt(shot: ShotSpec, bible: VisualBible) -> str:
    """Wan motion prompt; one primary motion plus at most two secondaries."""
    parts = [
        CINEMATIC_VIDEO[shot.camera.move],
        SHOT_SIZE_TEXT[shot.shot_size],
        f"primary motion: {motion_phrase(shot.motion.primary)}",
    ]
    if shot.motion.secondary:
        parts.append("secondary motion: " + ", ".join(shot.motion.secondary))
    if shot.layers.foreground:
        parts.append(f"foreground: {shot.layers.foreground}")
    if shot.layers.background:
        parts.append(f"background: {shot.layers.background}")
    parts.append(f"lighting: {bible.art_direction.lighting}, consistent direction")
    physical = physical_motion_for(shot)
    if physical:
        parts.append(f"physical motion: {physical}")
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
