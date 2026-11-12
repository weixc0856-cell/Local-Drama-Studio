"""Compile FLUX and Wan prompts from a Style Pack (VISUAL_STYLE_ENGINE §5)."""

from __future__ import annotations

from .schemas import StylePack

CAMERA_TEXT = {
    "static": "locked-off camera",
    "dolly_in": "slow physical dolly forward",
    "dolly_out": "slow physical dolly backward",
    "tracking": "smooth lateral tracking move",
    "pan": "slow pan",
    "tilt": "slow tilt",
    "crane": "camera rises or descends smoothly on a hidden rig, continuous speed, no equipment in frame",
    "orbit": "slow orbit around the subject",
    "handheld": "subtle handheld camera",
}


def require_camera(pack: StylePack, move: str) -> str:
    if move not in pack.camera.allowed_moves:
        raise ValueError(
            f"{pack.identity.id}: camera move {move!r} is not allowed; "
            f"use one of {pack.camera.allowed_moves}"
        )
    return CAMERA_TEXT.get(move, move.replace("_", " "))


def compile_image_prompt(
    pack: StylePack,
    *,
    subject: str,
    layers: dict[str, str],
    camera_move: str,
    extra_note: str | None = None,
) -> str:
    camera = require_camera(pack, camera_move)
    parts = [
        subject,
        pack.image.identity,
        pack.image.medium,
        "composition: " + ", ".join(pack.image.composition),
        f"lighting: {pack.lighting.key}, {pack.lighting.temperature} temperature, {pack.lighting.contrast} contrast",
        "materials: " + ", ".join(pack.material.materials),
        f"camera: {camera}, {pack.camera.preferred_lens_mm}mm lens, {pack.camera.dof_strategy} depth of field",
    ]
    for key in ("foreground", "midground", "background"):
        value = layers.get(key)
        if value:
            parts.append(f"{key}: {value}")
    parts.extend(pack.image.positive_anchors)
    if extra_note:
        parts.append(extra_note)
    parts.append("portrait 9:16 full-frame composition, no letterbox, no black bars")
    parts.append("unmarked surfaces, no lettering, no watermark")
    prompt = ". ".join(part.rstrip(".") for part in parts if part)
    if "#" in prompt:
        raise ValueError("hex colour leaked into a prompt; keep hex in color_profile.yaml only")
    return prompt


def compile_video_prompt(
    pack: StylePack,
    *,
    camera_move: str,
    primary_motion: str,
    secondary_motions: list[str] | None = None,
    layers: dict[str, str] | None = None,
) -> str:
    camera = require_camera(pack, camera_move)
    secondary = list(secondary_motions or [])
    if len(secondary) > pack.motion.secondary_limit:
        raise ValueError(
            f"{pack.identity.id}: {len(secondary)} secondary motions exceed limit {pack.motion.secondary_limit}"
        )
    parts = [
        camera,
        f"primary motion: {primary_motion}",
        "style motion: " + ", ".join(pack.video.motion_vocabulary),
        "preserve: " + ", ".join(pack.video.preserve),
        f"lighting: {pack.lighting.key}, consistent direction",
    ]
    if secondary:
        parts.append("secondary motion: " + ", ".join(secondary))
    if layers:
        for key in ("foreground", "background"):
            if layers.get(key):
                parts.append(f"{key}: {layers[key]}")
    parts.append(
        "smooth continuous motion, physically plausible, no abrupt changes, "
        "preserve composition and structure, no new characters, no scene transformation"
    )
    return ". ".join(part.rstrip(".") for part in parts if part)


def motion_allowed(pack: StylePack, primary: str) -> bool:
    return primary in pack.motion.primary_motions
