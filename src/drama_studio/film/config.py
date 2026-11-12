"""Film production settings read from ``project.json``.

Defaults are deliberately conservative: 24 fps matches Wan and the R3 motion
renderer, 1080x1920 is the vertical delivery size, and every shot must carry
motion unless the project explicitly disables it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# styles.yaml preset ids that the deterministic motion renderer understands.
# Style packs use a *narrative* camera vocabulary (dolly_in, tracking, ...),
# while drama_studio.motion uses mechanical moves (slow_push_in, ...).
STYLE_PACK_MOTION_PRESET: dict[str, str] = {
    "ink_wash": "ink_wash",
    "oriental.ink_wash": "ink_wash",
    "court_green_fine_line": "court_green_fine_line",
    "oriental.gongbi": "court_green_fine_line",
    "artistic.japanese_soft": "shinkai_scenery",
    "shinkai_scenery": "shinkai_scenery",
    "ghibli_scenery": "ghibli_scenery",
    "animation.ghibli": "ghibli_scenery",
}

# Storyboard camera move -> motion renderer move. The renderer still applies the
# style preset's allowed list and records a fallback reason when a move cannot
# be honoured (for example a lateral track on a still with no horizontal room).
CAMERA_MOVE: dict[str, str] = {
    # A locked-off still for five seconds is a frozen frame, which is exactly
    # the PPT look the film chain exists to remove. Keep the authored intent
    # but render a very slow 2% push instead.
    "static": "slow_push_in",
    "dolly_in": "slow_push_in",
    "dolly_out": "slow_pull_out",
    "tracking": "slow_lateral_track",
    "pan": "scroll_pan",
    "tilt": "slow_push_in",
    "crane": "slow_push_in",
    "orbit": "slow_push_in",
    "handheld": "slow_push_in",
}


class MotionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    preset: str | None = None
    # When the style pack has no styles.yaml preset, the still falls back to the
    # r3_build Ken Burns path instead of silently borrowing another style.
    allow_kenburns_fallback: bool = True


class EnhancementSettings(BaseModel):
    """Optional enhancement layer; Lanczos remains the production default.

    The nested shape exists so spatial SR, temporal processing, denoise and
    resize are independently replaceable. Learned backends are opt-in because
    per-frame SR has no temporal model and can flicker.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    profile: str = "conservative_1080p"
    spatial_backend: Literal["lanczos", "realesrgan-ncnn", "realesrnet-ncnn"] = "lanczos"
    model: str = "realesrnet-x4plus"
    scale: int = Field(default=4, ge=1, le=4)
    tile_size: int = Field(default=128, ge=0, le=1024)
    temporal_backend: Literal["none", "hqdn3d"] = "none"
    denoise: bool = False
    output_width: int = Field(default=1080, ge=256, le=2160)
    output_height: int = Field(default=1920, ge=256, le=3840)
    fallback: Literal["explicit_manual_approval"] = "explicit_manual_approval"


class ProductionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=1080, ge=256, le=2160)
    height: int = Field(default=1920, ge=256, le=3840)
    fps: int = Field(default=24, ge=12, le=60)
    content_type: Literal["poetry", "narration", "mixed"] = "poetry"
    leading_silence_ms: int = Field(default=300, ge=0, le=5000)
    narration_tail_ms: int = Field(default=500, ge=0, le=5000)
    min_shot_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    no_narration_seconds: float = Field(default=3.0, gt=0.0, le=30.0)
    max_shot_seconds: float = Field(default=12.0, gt=0.0, le=60.0)
    tail_seconds: float = Field(default=1.0, ge=0.0, le=10.0)
    bgm_asset_id: str | None = None
    ambience_asset_id: str | None = None
    ambience_gain_db: float = Field(default=-26.0, ge=-60.0, le=0.0)
    clip_extend_policy: Literal["hold_last", "slow", "trim"] = "hold_last"
    transition_on_scene_change: bool = True
    crossfade_seconds: float = Field(default=0.5, ge=0.0, le=1.5)
    upscale_backend: Literal["lanczos", "realesrgan-ncnn"] = "lanczos"
    upscale_denoise: bool = True
    voice_allow_noncommercial: bool = False
    enhancement: EnhancementSettings = Field(default_factory=EnhancementSettings)
    motion: MotionSettings = Field(default_factory=MotionSettings)


def load_production(meta: dict[str, Any]) -> ProductionSettings:
    raw = meta.get("production") or {}
    return ProductionSettings.model_validate(raw)


def motion_preset_for(style_id: str | None, settings: MotionSettings) -> str | None:
    if settings.preset:
        return settings.preset
    if not style_id:
        return None
    return STYLE_PACK_MOTION_PRESET.get(style_id)


def mechanical_camera(move: str) -> str:
    return CAMERA_MOVE.get(move, "slow_push_in")


def load_project_meta(root: Path, project_id: str) -> dict[str, Any]:
    import json

    path = root / "projects" / project_id / "project.json"
    return json.loads(path.read_text(encoding="utf-8"))
