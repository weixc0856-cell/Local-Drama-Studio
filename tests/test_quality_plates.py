from __future__ import annotations

import hashlib
import json

import pytest
from PIL import Image

from drama_studio.application.motion.plates import camera_window
from drama_studio.application.quality import (
    REVEAL_THRESHOLDS,
    _placed_alpha,
    _plate_scale_at,
    check_plate_bounds,
    check_plate_reveal,
)

CAMERA = {
    "move": "slow_push_in", "duration_seconds": 6.0, "easing": "ease_in_out",
    "focus": [0.5, 0.48], "scale_start": 1.0, "scale_end": 1.048,
    "source_size": [576, 1024],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ helpers
def test_plate_scale_follows_the_renderer():
    assert _plate_scale_at(CAMERA, 1.0, 0.0) == pytest.approx(1.0)
    assert _plate_scale_at(CAMERA, 1.0, 1.0) == pytest.approx(1.048)
    near = _plate_scale_at(CAMERA, 0.49, 1.0)
    mid = _plate_scale_at(CAMERA, 0.70, 1.0)
    assert near > mid > 1.048


def test_placed_alpha_uses_the_anchor():
    asset = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
    alpha = _placed_alpha(asset, {"x0": 0.25, "y0": 0.25, "x1": 0.35, "y1": 0.35},
                          camera_window(1.0, (0.5, 0.48)))
    assert alpha.size == (1920, 1080)
    assert alpha.getpixel((550, 320)) == 255      # inside the anchor
    assert alpha.getpixel((1600, 900)) == 0       # far outside


# ------------------------------------------------------------------- repair
def textured(size=(1920, 1080), flat_box=None):
    """A plate with high-frequency paint everywhere, optionally flat in a box."""
    image = Image.effect_noise(size, 90).convert("RGB")
    if flat_box:
        pixels = image.load()
        for y in range(flat_box[1], flat_box[3]):
            for x in range(flat_box[0], flat_box[2]):
                pixels[x, y] = (200, 200, 200)
    return image


def write_shot(tmp_path, *, repair_box, exposure_of_repair, flat_inside):
    hole = Image.new("L", (1920, 1080), 0)
    hole.paste(255, repair_box)
    hole_path = tmp_path / "hole.png"
    hole.save(hole_path)

    plate = textured(flat_box=repair_box if flat_inside else None)
    plate_path = tmp_path / "bg.png"
    plate.save(plate_path)

    # A mover that leaves `exposure_of_repair` of the repair uncovered: a small
    # opaque block that covers the rest.
    mover = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    covered = int((repair_box[2] - repair_box[0]) * (1 - exposure_of_repair))
    mover.paste((0, 0, 0, 255), (repair_box[0], repair_box[1],
                                 repair_box[0] + covered, repair_box[3]))
    mover_path = tmp_path / "mover.png"
    mover.save(mover_path)

    return {
        "id": "shot_001", "camera": CAMERA, "duration_seconds": 2.0,
        "plates": [
            {"id": "bg", "source": "inpainted", "path": str(plate_path),
             "sha256": digest(plate_path), "z_order": 0, "depth_alpha": 1.0,
             "coverage": "full_frame",
             "provenance": {"mask": str(hole_path), "mask_sha256": digest(hole_path),
                            "mask_coverage": 0.05}},
            {"id": "mover", "source": "generated_asset", "path": str(mover_path),
             "sha256": digest(mover_path), "z_order": 1, "depth_alpha": 1.0,
             "coverage": "partial",
             "anchor": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0}},
        ],
    }


REPAIR_BOX = (530, 450, 1240, 675)


def test_flat_repair_that_is_barely_exposed_passes(tmp_path):
    """A patch nobody sees cannot be wrong."""
    shot = write_shot(tmp_path, repair_box=REPAIR_BOX, exposure_of_repair=0.0,
                      flat_inside=True)
    report = check_plate_reveal(shot, root=tmp_path)
    assert report["status"] == "PASS", json.dumps(report, ensure_ascii=False)
    assert report["plates"][0]["note"] == "补底未被显著露出"


def test_flat_repair_exposed_to_the_viewer_fails(tmp_path):
    shot = write_shot(tmp_path, repair_box=REPAIR_BOX, exposure_of_repair=0.5,
                      flat_inside=True)
    report = check_plate_reveal(shot, root=tmp_path)
    assert report["status"] == "FAIL"
    assert report["code"] == "PLATE_REPAIR_VIOLATION"
    assert report["plates"][0]["energy_ratio"] < 0.5


def test_textured_repair_survives_exposure(tmp_path):
    shot = write_shot(tmp_path, repair_box=REPAIR_BOX, exposure_of_repair=0.5,
                      flat_inside=False)
    report = check_plate_reveal(shot, root=tmp_path)
    assert report["status"] == "PASS", json.dumps(report, ensure_ascii=False)
    assert report["plates"][0]["energy_ratio"] > 0.9


def test_shot_without_plates_is_a_no_op():
    report = check_plate_reveal({"id": "shot_001"})
    assert report["code"] == "NO_PLATES"


def test_background_without_repair_is_a_no_op(tmp_path):
    shot = {
        "id": "shot_001", "camera": CAMERA, "duration_seconds": 2.0,
        "plates": [{"id": "bg", "source": "original", "path": "bg.png",
                    "sha256": "0" * 64, "z_order": 0, "depth_alpha": 1.0,
                    "coverage": "full_frame"}],
    }
    report = check_plate_reveal(shot, root=tmp_path)
    assert report["code"] == "NO_REPAIR"


# ------------------------------------------------------------------- bounds
def test_bounds_pass_for_a_window_inside_the_plate(tmp_path):
    path = tmp_path / "bg.png"
    Image.new("RGB", (3200, 1600), (200, 200, 200)).save(path)
    shot = {
        "id": "shot_001", "duration_seconds": 4.0,
        "camera": dict(CAMERA, move="scroll_pan", pan_start_px=60.0, pan_end_px=200.0),
        "plates": [{"id": "bg", "source": "generated_background", "path": str(path),
                    "sha256": "0" * 64, "z_order": 0, "depth_alpha": 1.0,
                    "coverage": "full_frame"}],
    }
    report = check_plate_bounds(shot, root=tmp_path)
    assert report["status"] == "PASS", json.dumps(report, ensure_ascii=False)
    assert report["worst_window"]["x1"] <= 1.0 + 1e-6


def test_bounds_fail_when_the_pan_walks_off_the_plate(tmp_path):
    path = tmp_path / "bg.png"
    Image.new("RGB", (3200, 1600), (200, 200, 200)).save(path)
    shot = {
        "id": "shot_001", "duration_seconds": 4.0,
        # travel far past the plate's right edge
        "camera": dict(CAMERA, move="scroll_pan", pan_start_px=900.0, pan_end_px=1200.0),
        "plates": [{"id": "bg", "source": "generated_background", "path": str(path),
                    "sha256": "0" * 64, "z_order": 0, "depth_alpha": 1.0,
                    "coverage": "full_frame"}],
    }
    report = check_plate_bounds(shot, root=tmp_path)
    assert report["status"] == "FAIL"
    assert report["code"] == "PLATE_OUT_OF_BOUNDS"
