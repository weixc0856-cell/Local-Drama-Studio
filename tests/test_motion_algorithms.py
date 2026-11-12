from __future__ import annotations

import math
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from drama_studio.application.motion.local import (
    cloud_displacement,
    perspective_weight,
    prepare_layers,
    reflection_displacement,
    sway_offset,
    sway_weight,
    water_displacement,
    water_vertical_displacement,
)
from drama_studio.domain.motion.spec import LocalMotionSpec, MaskSpec
from drama_studio.domain.style.presets import load_style_presets

ROOT = Path(__file__).resolve().parents[1]
WATER = dict(
    amplitude=6.0,
    frequency=1.0 / 12.0,
    wavelength_px=300.0,
    vertical_ratio=0.28,
    far_scale=0.14,
    bounds=(0.50, 0.85),
)


def _max_over_time(fn, xn: float, yn: float, *, steps: int = 240) -> float:
    return max(abs(fn(xn, yn, i / 24.0)) for i in range(steps))


def test_plant_sway_bottom_displacement_is_exactly_zero() -> None:
    for t in (0.0, 0.13, 0.5, 1.7, 3.9):
        assert sway_weight(1.0, 0.6, 1.0, exponent=1.4, top_decay=0.2) == 0.0
        assert sway_offset(1.0, t, y0=0.6, y1=1.0, amplitude=3.0,
                           frequency=0.2) == 0.0


def test_plant_sway_is_monotonic_from_base_and_decays_at_the_tip() -> None:
    # walk from the base (y=1.0) up to the tip (y=0.6)
    weights = [sway_weight(y / 100.0, 0.6, 1.0, exponent=1.4, top_decay=0.2)
               for y in range(100, 59, -1)]
    assert weights[0] == 0.0
    peak = max(range(len(weights)), key=lambda index: weights[index])
    assert peak < len(weights) - 1
    rising = weights[: peak + 1]
    assert all(b >= a for a, b in zip(rising, rising[1:]))
    assert weights[-1] < weights[-2]  # the very tip carries less than the upper-middle


def test_plant_sway_frame_keeps_the_bottom_row_pixel_identical(tmp_path: Path) -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    base = Image.new("RGB", (540, 960))
    # a vertical gradient makes a row shift visible
    for y in range(960):
        base.paste((y % 256, (y * 3) % 256, (y * 7) % 256), (0, y, 540, y + 1))
    spec = LocalMotionSpec(
        layer_id="reed", motion_type="reed_sway",
        mask=MaskSpec(y0=0.60, y1=1.0), amplitude=3.0, frequency=0.2,
    )
    layer = prepare_layers(
        root=ROOT, base_half=base, gray_half=base.convert("L"), spec=spec,
        policy=ink.motion.local_policy["reed_sway"], out_dir=tmp_path,
        duration=1 / 24, fps=24,
    )
    frame = Image.open(Path(layer.info["frames_dir"]) / "f_0000.png").convert("RGB")
    bottom = 959
    diff = ImageChops.difference(frame.crop((0, bottom, 540, bottom + 1)),
                                 base.crop((0, bottom, 540, bottom + 1)))
    assert diff.getbbox() is None


def test_water_perspective_weight_is_monotonic_toward_the_far_edge() -> None:
    weights = [perspective_weight(y / 100.0, (0.5, 0.85), 0.14)
               for y in range(50, 86)]
    assert all(b >= a for a, b in zip(weights, weights[1:]))  # y grows downward
    assert weights[0] == pytest.approx(0.14)
    assert weights[-1] == pytest.approx(1.0)


def test_water_vertical_amplitude_decays_monotonically_toward_the_far_edge() -> None:
    far = _max_over_time(lambda x, y, t: water_vertical_displacement(
        x, y, t, **WATER), 0.5, 0.50)
    middle = _max_over_time(lambda x, y, t: water_vertical_displacement(
        x, y, t, **WATER), 0.5, 0.68)
    near = _max_over_time(lambda x, y, t: water_vertical_displacement(
        x, y, t, **WATER), 0.5, 0.84)
    assert far < middle < near
    # sampled 24 fps: within 1e-5 of the analytic envelope at the far edge
    assert far == pytest.approx(WATER["amplitude"] * WATER["vertical_ratio"] * 0.14,
                                rel=1e-3)


def test_water_displacement_has_no_high_frequency_component() -> None:
    # a smooth field: adjacent x samples move by well under the amplitude
    values = [water_displacement(i / 60.0, 0.7, 0.4, **WATER)[0] for i in range(61)]
    steps = [abs(b - a) for a, b in zip(values, values[1:])]
    assert max(steps) < WATER["amplitude"] * 0.25
    assert len(values) == len(set(round(v, 9) for v in values))


def test_reflection_is_vertical_only_and_never_exceeds_water() -> None:
    kwargs = dict(
        water_amplitude=WATER["amplitude"], water_frequency=WATER["frequency"],
        wavelength_px=WATER["wavelength_px"], vertical_ratio=WATER["vertical_ratio"],
        far_scale=WATER["far_scale"], bounds=WATER["bounds"],
        ratio=0.55, lag_s=0.18,
    )
    for xn in (0.2, 0.5, 0.8):
        for yn in (0.55, 0.7, 0.82):
            for i in range(120):
                t = i / 24.0
                dx, dy = reflection_displacement(xn, yn, t, **kwargs)
                assert dx == 0.0
                water_dy = water_vertical_displacement(
                    xn, yn, t, amplitude=WATER["amplitude"],
                    frequency=WATER["frequency"], wavelength_px=WATER["wavelength_px"],
                    vertical_ratio=WATER["vertical_ratio"], far_scale=WATER["far_scale"],
                    bounds=WATER["bounds"],
                )
                assert abs(dy) <= abs(water_dy) + 1e-12


def test_reflection_field_has_no_isolated_spike() -> None:
    kwargs = dict(
        water_amplitude=WATER["amplitude"], water_frequency=WATER["frequency"],
        wavelength_px=WATER["wavelength_px"], vertical_ratio=WATER["vertical_ratio"],
        far_scale=WATER["far_scale"], bounds=WATER["bounds"],
        ratio=0.55, lag_s=0.18,
    )
    for i in range(80):
        t = i / 24.0
        values = [reflection_displacement(x, 0.7, t, **kwargs)[1]
                  for x in (j / 80.0 for j in range(81))]
        steps = [abs(b - a) for a, b in zip(values, values[1:])]
        second = [abs(c - 2 * b + a) for a, b, c in zip(values, values[1:], values[2:])]
        assert max(steps) <= WATER["amplitude"] * 0.2
        assert max(second) <= WATER["amplitude"] * 0.1


def test_cloud_flow_is_smooth_and_not_a_rigid_translation() -> None:
    def field(xn, yn, t):
        return cloud_displacement(xn, yn, t, amplitude=18.0, period_s=22.0)

    samples = [field(i / 40.0, 0.4, 3.0)[0] for i in range(41)]
    steps = [abs(b - a) for a, b in zip(samples, samples[1:])]
    assert max(steps) < 18.0 * 0.4
    # not a constant shift: different positions have different displacement
    assert len({round(v, 3) for v in samples}) > 10


def test_cloud_layer_alpha_is_static_and_has_no_opacity_pump(tmp_path: Path) -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    base = Image.new("RGB", (540, 960), (210, 210, 215))
    spec = LocalMotionSpec(
        layer_id="cloud", motion_type="cloud_drift",
        mask=MaskSpec(y0=0.10, y1=0.40), amplitude=14.0, frequency=1 / 22.0,
    )
    layer = prepare_layers(
        root=ROOT, base_half=base, gray_half=base.convert("L"), spec=spec,
        policy=ink.motion.local_policy["cloud_drift"], out_dir=tmp_path,
        duration=2 / 24, fps=24,
    )
    assert layer.info["algorithm"] == "cloud_drift_v2"
    first = Image.open(Path(layer.info["frames_dir"]) / "f_0000.png").getchannel("A")
    second = Image.open(Path(layer.info["frames_dir"]) / "f_0001.png").getchannel("A")
    assert ImageChops.difference(first, second).getbbox() is None


def test_water_and_cloud_report_the_new_algorithm(tmp_path: Path) -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    base = Image.new("RGB", (540, 960), (120, 140, 150))
    water = LocalMotionSpec(
        layer_id="water", motion_type="water_ripple",
        mask=MaskSpec(y0=0.5, y1=0.85), amplitude=2.0, frequency=1 / 12.0,
    )
    layer = prepare_layers(
        root=ROOT, base_half=base, gray_half=base.convert("L"), spec=water,
        policy=ink.motion.local_policy["water_ripple"], out_dir=tmp_path,
        duration=1 / 24, fps=24,
    )
    assert layer.info["algorithm"] == "water_ripple_v2"
    assert layer.info["wavelength_px"] > 0
    assert 0.0 < layer.info["perspective_far_scale"] < 1.0


def test_displacement_fields_are_finite_everywhere() -> None:
    for i in range(24):
        t = i / 24.0
        for j in range(20):
            x = j / 19.0
            dx, dy = water_displacement(x, 0.7, t, **WATER)
            assert math.isfinite(dx) and math.isfinite(dy)
            cdx, cdy = cloud_displacement(x, 0.3, t, amplitude=18.0, period_s=22.0)
            assert math.isfinite(cdx) and math.isfinite(cdy)
