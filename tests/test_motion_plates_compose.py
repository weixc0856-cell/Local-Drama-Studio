from __future__ import annotations

import pytest
from PIL import Image

from drama_studio.motion.plates import (
    CameraState,
    LoadedPlate,
    background_pan,
    background_scale,
    camera_window,
    compose,
    map_point,
    pan_window,
    plate_scale,
    sample,
)
from drama_studio.motion.spec import CameraSpec, PlateAnchor, PlateSpec

HASH = "0" * 64


def spec(plate_id: str, *, z_order: int, depth_alpha: float, coverage: str,
         anchor: tuple[float, float, float, float] | None = None) -> PlateSpec:
    return PlateSpec(
        id=plate_id,
        # a synthetic block is an independent asset, not a cut-out of a still
        source="generated_asset" if coverage == "partial" else "original",
        path=f"{plate_id}.png", sha256=HASH,
        z_order=z_order, depth_alpha=depth_alpha, coverage=coverage,
        anchor=PlateAnchor(x0=anchor[0], y0=anchor[1], x1=anchor[2], y1=anchor[3])
        if anchor else None,
    )


def camera(**kwargs) -> CameraSpec:
    base = dict(
        move="slow_push_in", requested_move="slow_push_in", duration_seconds=6.0,
        easing="ease_in_out", focus=(0.5, 0.48), scale_start=1.0, scale_end=1.048,
        source_size=(576, 1024),
    )
    base.update(kwargs)
    return CameraSpec(**base)


# ------------------------------------------------------------------ scale
def test_plate_scale_is_identity_at_scale_one():
    assert plate_scale(1.0, 0.49) == pytest.approx(1.0)


def test_background_plane_keeps_the_camera_scale():
    assert plate_scale(1.048, 1.0) == pytest.approx(1.048)


def test_nearer_plane_scales_more():
    """Matches the M8-A measurement: alpha 0.70 -> 1.070012 at bg 1.048."""
    assert plate_scale(1.048, 0.70) == pytest.approx(1.070012, abs=1e-5)
    assert plate_scale(1.048, 0.49) == pytest.approx(1.103111, abs=1e-5)
    assert plate_scale(1.048, 0.49) > plate_scale(1.048, 0.70) > plate_scale(1.048, 1.0)


@pytest.mark.parametrize("alpha", [0.0, -0.2])
def test_depth_alpha_must_be_positive(alpha):
    with pytest.raises(ValueError, match="depth_alpha"):
        plate_scale(1.05, alpha)


def test_background_scale_follows_zoompan_progress():
    cam = camera()
    assert background_scale(cam, 0, 144) == pytest.approx(1.0)
    assert background_scale(cam, 143, 144) == pytest.approx(1.048)
    mid = background_scale(cam, 71, 144)
    assert 1.0 < mid < 1.048


# ----------------------------------------------------------------- window
def test_window_at_scale_one_is_the_whole_frame():
    assert camera_window(1.0, (0.5, 0.48)) == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_window_matches_the_zoompan_rule():
    x0, y0, window, window_y = camera_window(1.048, (0.5, 0.48))
    assert window_y == pytest.approx(window)
    assert window == pytest.approx(1 / 1.048)
    assert x0 == pytest.approx(0.5 - 0.5 * window)
    assert y0 == pytest.approx(max(0.0, 0.48 - 0.5 * window))


def test_window_is_clamped_inside_the_plate():
    x0, y0, window, _ = camera_window(1.02, (0.02, 0.02))
    assert x0 == pytest.approx(0.0)
    assert y0 == pytest.approx(0.0)
    assert x0 + window <= 1.0 + 1e-9


def test_map_point_puts_focus_at_the_frame_centre():
    x, y = map_point((0.5, 0.48), camera_window(1.048, (0.5, 0.48)))
    assert x == pytest.approx(0.5)
    assert y == pytest.approx(0.5)


# ------------------------------------------------------------------ sample
def test_sample_at_scale_one_is_a_plain_resize():
    source = Image.new("RGBA", (576, 1024), (200, 40, 40, 255))
    out = sample(source, 1.0, (0.5, 0.48), (1080, 1920))
    assert out.size == (1080, 1920)
    assert out.getpixel((10, 10))[:3] == (200, 40, 40)


# ----------------------------------------------------------------- compose
def white_plate(width: int = 540, height: int = 960) -> Image.Image:
    return Image.new("RGBA", (width, height), (255, 255, 255, 255))


def red_block(size: int = 100) -> Image.Image:
    return Image.new("RGBA", (size, size), (255, 0, 0, 255))


def test_compose_places_a_partial_plate_at_its_anchor():
    stack = [
        LoadedPlate(spec("bg", z_order=0, depth_alpha=1.0, coverage="full_frame"), white_plate()),
        LoadedPlate(spec("dot", z_order=1, depth_alpha=1.0, coverage="partial",
                         anchor=(0.25, 0.25, 0.35, 0.35)), red_block()),
    ]
    frame = compose(stack, CameraState(), (1080, 1920))
    assert frame.getpixel((100, 100)) == (255, 255, 255)
    assert frame.getpixel((300, 500)) == (255, 0, 0)
    # outside the anchor, still background
    assert frame.getpixel((900, 1600)) == (255, 255, 255)


def test_compose_requires_a_full_frame_background():
    stack = [LoadedPlate(spec("dot", z_order=0, depth_alpha=1.0, coverage="partial",
                              anchor=(0.25, 0.25, 0.35, 0.35)), red_block())]
    with pytest.raises(ValueError, match="full_frame background"):
        compose(stack, CameraState(), (1080, 1920))


# --------------------------------------------------------------------- pan
def test_pan_keeps_planes_aligned_at_rest():
    for alpha in (1.0, 0.7, 0.49):
        x0, y0, span_x, span_y = pan_window(0.25, alpha, pan_start=0.25)
        assert (x0, y0, span_x, span_y) == pytest.approx((0.25, 0.0, 1.0, 1.0))


def test_nearer_plane_travels_farther_in_a_pan():
    far = pan_window(0.30, 1.0, pan_start=0.10)[0]
    mid = pan_window(0.30, 0.70, pan_start=0.10)[0]
    near = pan_window(0.30, 0.49, pan_start=0.10)[0]
    assert far == pytest.approx(0.30)
    assert mid == pytest.approx(0.10 + 0.20 / 0.70)
    assert near == pytest.approx(0.10 + 0.20 / 0.49)
    assert near > mid > far


def test_pan_window_span_is_the_frame_share_of_a_wide_plate():
    """A 9:16 frame covers only part of a wide plate's width."""
    _, _, span_x, span_y = pan_window(0.2, 1.0, span=0.36)
    assert span_x == pytest.approx(0.36)
    assert span_y == pytest.approx(1.0)


def test_pan_window_is_not_clamped():
    """Running out of plate is a defect the gate must see, not something to hide."""
    x0 = pan_window(0.95, 0.49, pan_start=0.0)[0]
    assert x0 > 1.0


def test_background_pan_follows_the_camera_span():
    cam = camera(pan_start_px=40.0, pan_end_px=220.0, scale_start=1.0, scale_end=1.0)
    assert background_pan(cam, 0, 144, panel_width=1080) == pytest.approx(40 / 1080)
    assert background_pan(cam, 143, 144, panel_width=1080) == pytest.approx(220 / 1080)


def test_compose_under_pan_moves_the_near_plane_by_one_over_alpha():
    """The near plane slides 1/alpha as far as the background does."""
    bg = Image.new("RGBA", (540, 960), (255, 255, 255, 255))
    fg = Image.new("RGBA", (540, 960), (0, 0, 0, 0))
    fg.paste((255, 0, 0, 255), (268, 200, 272, 400))  # marker on the near plane
    stack = [
        LoadedPlate(spec("bg", z_order=0, depth_alpha=1.0, coverage="full_frame"), bg),
        LoadedPlate(spec("near", z_order=1, depth_alpha=0.5, coverage="partial",
                         anchor=(0.0, 0.0, 1.0, 1.0)), fg),
    ]

    def red_center(image):
        row = [x for x in range(1080) if image.getpixel((x, 600))[0] > 200
               and image.getpixel((x, 600))[1] < 60]
        assert row, "near-plane marker not found"
        return sum(row) / len(row)

    rest = compose(stack, CameraState(mode="pan", pan=0.0, pan_start=0.0), (1080, 1920))
    moved = compose(stack, CameraState(mode="pan", pan=0.1, pan_start=0.0), (1080, 1920))
    shift = red_center(moved) - red_center(rest)
    # background travels 0.1 * 1080 = 108 px; alpha 0.5 doubles it.
    assert shift == pytest.approx(-216, abs=6)
