from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_studio.domain.motion.camera import camera_chain
from drama_studio.domain.motion.spec import (
    CameraOverride,
    LocalMotionSpec,
    MaskSpec,
    MotionPlan,
    ShotSpec,
    TransitionSpec,
    resolve_camera,
)
from drama_studio.motion.transition import make_masks
from drama_studio.domain.style.presets import load_style_presets

ROOT = Path(__file__).resolve().parents[1]


def _shot(motion: str, *, duration: float = 5.0, camera: dict | None = None) -> ShotSpec:
    return ShotSpec(
        id="shot_001",
        source="still.png",
        duration_seconds=duration,
        motion=motion,
        camera=CameraOverride.model_validate(camera) if camera else None,
    )


def test_free_text_hint_resolves_to_style_policy() -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    camera = resolve_camera(_shot("slow push-in"), ink, (576, 1024))
    assert camera.move == "slow_push_in"
    assert camera.requested_move == "slow_push_in"
    assert camera.easing == "ease_in_out"
    assert camera.scale_start == 1.0
    # 0.008/s over 5 s = 4 %, inside the configured 3-6 % band.
    assert 1.03 <= camera.scale_end <= 1.06
    assert "zoompan" in camera_chain(camera)
    assert "pow(" in camera_chain(camera)


def test_pan_has_no_room_on_exact_9x16_still() -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    camera = resolve_camera(_shot("scroll pan"), ink, (576, 1024))
    assert camera.move == "slow_push_in"
    assert camera.requested_move == "scroll_pan"
    assert camera.fallback_reason and "无横移空间" in camera.fallback_reason


def test_pan_speed_comes_from_the_style_config() -> None:
    court = load_style_presets(ROOT).get("court_green_fine_line")
    camera = resolve_camera(_shot("scroll pan", duration=4.0), court, (1024, 1024))
    assert camera.move == "scroll_pan"
    assert camera.pan_range_px == 840
    assert camera.pan_end_px - camera.pan_start_px == pytest.approx(120, abs=1)
    assert "crop=1080:1920" in camera_chain(camera)


def test_disallowed_move_falls_back_and_records_why() -> None:
    court = load_style_presets(ROOT).get("court_green_fine_line")
    camera = resolve_camera(_shot("layered parallax"), court, (1024, 1024))
    assert camera.move == court.motion.camera.default
    assert camera.requested_move == "layered_parallax"
    assert camera.fallback_reason is not None


def test_explicit_override_wins_over_text() -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    camera = resolve_camera(
        _shot("static", camera={"move": "slow_pull_out", "scale_end": 1.05, "direction": "rtl"}),
        ink,
        (1024, 1024),
    )
    assert camera.move == "slow_pull_out"
    assert camera.scale_start == 1.05
    assert camera.scale_end == 1.0


def test_local_motion_needs_an_asset_for_petals() -> None:
    with pytest.raises(ValidationError, match="RGBA asset"):
        LocalMotionSpec(
            layer_id="petals",
            motion_type="petal_drift",
            mask=MaskSpec(y0=0.2, y1=0.5),
            amplitude=10,
            frequency=0.1,
        )


def test_plan_rejects_transition_on_first_shot() -> None:
    shot = ShotSpec(
        id="shot_001",
        source="a.png",
        duration_seconds=3,
        transition_in=TransitionSpec(type="crossfade", duration_s=0.8, feather=0.1),
    )
    with pytest.raises(ValidationError, match="first shot"):
        MotionPlan(style_id="ink_wash", shots=[shot])


def test_transition_masks_are_deterministic_and_monotonic(tmp_path: Path) -> None:
    spec = TransitionSpec(type="ink_dissolve", duration_s=1.0, feather=0.12, direction="ltr", seed=13)
    first = make_masks(spec, tmp_path / "a", 1.0, 24)
    second = make_masks(spec, tmp_path / "b", 1.0, 24)
    assert first["frames"] == second["frames"] == 24

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    for index in range(24):
        name = f"m_{index:04d}.png"
        assert digest(tmp_path / "a" / name) == digest(tmp_path / "b" / name)

    from PIL import Image, ImageStat

    start = ImageStat.Stat(Image.open(tmp_path / "a" / "m_0000.png")).mean[0]
    end = ImageStat.Stat(Image.open(tmp_path / "a" / "m_0023.png")).mean[0]
    assert start < 30
    assert end > 220


def test_local_policy_supplies_missing_amplitude_and_frequency(tmp_path: Path) -> None:
    from PIL import Image

    from drama_studio.motion.local import prepare_layers

    ink = load_style_presets(ROOT).get("ink_wash")
    spec = LocalMotionSpec(
        layer_id="water",
        motion_type="water_ripple",
        mask=MaskSpec(y0=0.8, y1=1.0),
        amplitude=None,
        frequency=None,
    )
    base = Image.new("RGB", (540, 960), (120, 130, 140))
    layer = prepare_layers(
        root=ROOT,
        base_half=base,
        gray_half=base.convert("L"),
        spec=spec,
        policy=ink.motion.local_policy["water_ripple"],
        out_dir=tmp_path,
        duration=2.0,
        fps=24,
    )
    assert layer.info["amplitude_requested"] is None
    assert layer.info["frequency_requested"] is None
    assert layer.info["amplitude_px"] == ink.motion.local_policy["water_ripple"].amplitude_px
    assert layer.info["frequency_hz"] == pytest.approx(
        1.0 / ink.motion.local_policy["water_ripple"].period_s, rel=1e-6
    )
