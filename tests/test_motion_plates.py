from __future__ import annotations

import pytest
from pydantic import ValidationError

from drama_studio.application.motion.plates import enforce_policy
from drama_studio.domain.motion.spec import (
    Box,
    PlateAnchor,
    PlateProvenance,
    PlateSpec,
    RegionSpec,
    ShotSpec,
)

HASH = "0" * 64


def box(values: tuple[float, float, float, float]) -> Box:
    return Box(x0=values[0], y0=values[1], x1=values[2], y1=values[3])


def anchor(values: tuple[float, float, float, float]) -> PlateAnchor:
    return PlateAnchor(x0=values[0], y0=values[1], x1=values[2], y1=values[3])


def plate(plate_id: str, *, source: str = "original", z_order: int = 0,
          depth_alpha: float = 1.0, coverage: str = "full_frame",
          anchor: tuple[float, float, float, float] | None = None,
          provenance: PlateProvenance | None = None,
          hole_mask: bool = True) -> PlateSpec:
    # A plate cut from the still must declare the hole it left behind; a
    # generated asset was never part of the painting, so it has no hole.
    needs_hole = hole_mask and source == "original" and coverage == "partial"
    return PlateSpec(
        id=plate_id,
        source=source,
        path=f"experiments/plates/{plate_id}.png",
        sha256=HASH,
        z_order=z_order,
        depth_alpha=depth_alpha,
        coverage=coverage,
        anchor=PlateAnchor(x0=anchor[0], y0=anchor[1], x1=anchor[2], y1=anchor[3])
        if anchor else None,
        hole_mask=f"experiments/plates/mask_{plate_id}.png" if needs_hole else None,
        hole_mask_sha256=HASH if needs_hole else None,
        provenance=provenance,
    )


def shot(plates=None, regions=None, depth_exceptions=None) -> ShotSpec:
    return ShotSpec(
        id="shot_001",
        source="experiments/still.png",
        duration_seconds=6.0,
        plates=plates or [],
        regions=regions or [],
        depth_exceptions=depth_exceptions or {},
    )


def three_planes() -> list[PlateSpec]:
    return [
        plate("bg", z_order=0, depth_alpha=1.0),
        plate("boat", z_order=1, depth_alpha=0.70, coverage="partial",
              anchor=(0.30, 0.455, 0.632, 0.612)),
        plate("reeds", source="generated_asset", z_order=2, depth_alpha=0.49,
              coverage="partial", anchor=(0.24, 0.58, 0.57, 1.02)),
    ]


# --------------------------------------------------------------- happy path
def test_three_source_planes_parse():
    spec = shot(three_planes())
    assert [item.id for item in spec.plates] == ["bg", "boat", "reeds"]
    assert spec.plates[2].source == "generated_asset"


def test_shot_without_plates_is_unchanged():
    """The layered path is opt-in; existing single-plane shots must still parse."""
    spec = shot()
    assert spec.plates == []
    assert spec.depth_exceptions == {}


# ----------------------------------------------------- per-plate invariants
def test_generated_asset_cannot_be_the_background():
    with pytest.raises(ValidationError, match="generated_asset 必须是 partial"):
        plate("fg", source="generated_asset", coverage="full_frame")


def test_partial_plate_needs_an_anchor():
    with pytest.raises(ValidationError, match="partial 图层必须给出 anchor"):
        plate("boat", z_order=1, depth_alpha=0.7, coverage="partial")


def test_full_frame_plate_rejects_anchor():
    with pytest.raises(ValidationError, match="full_frame 图层不接受 anchor"):
        plate("bg", coverage="full_frame", anchor=(0.0, 0.0, 1.0, 1.0))


def test_paint_repair_needs_provenance():
    with pytest.raises(ValidationError, match="补底图层必须记录 provenance"):
        plate("bg", source="inpainted")


def test_paint_repair_size_is_recorded_not_policed():
    """Mask size alone says nothing about the product; the reveal gate judges
    what the viewer can actually see, so a large repair is allowed here."""
    wide = PlateProvenance(mask_coverage=0.09, mask="masks/tree.png")
    assert plate("bg", source="inpainted", provenance=wide).provenance.mask_coverage == 0.09


# ------------------------------------------------- shot-level invariants (R1-R5)
def test_exactly_one_background_is_required():
    with pytest.raises(ValidationError, match="必须恰好有一层 full_frame 背景"):
        shot([plate("boat", z_order=1, depth_alpha=0.7, coverage="partial",
                    anchor=(0.3, 0.4, 0.6, 0.6))])

    with pytest.raises(ValidationError, match="必须恰好有一层 full_frame 背景"):
        shot([plate("bg", z_order=0), plate("bg2", z_order=1, depth_alpha=0.7)])


def test_background_must_be_farthest():
    with pytest.raises(ValidationError, match="背景必须是最远层"):
        shot([plate("boat", z_order=0, depth_alpha=0.7, coverage="partial",
                    anchor=(0.3, 0.4, 0.6, 0.6)),
              plate("bg", z_order=1, depth_alpha=1.0)])


def test_paint_repair_only_on_the_background():
    repaired = PlateProvenance(mask_coverage=0.02, mask="m.png")
    with pytest.raises(ValidationError, match="补底只允许出现在背景层"):
        shot([plate("bg", z_order=0),
              plate("boat", source="inpainted", z_order=1, depth_alpha=0.7,
                    coverage="partial", anchor=(0.3, 0.4, 0.6, 0.6),
                    provenance=repaired)])


def test_depth_alpha_must_decrease_with_z():
    with pytest.raises(ValidationError, match="depth_alpha"):
        shot([plate("bg", z_order=0, depth_alpha=1.0),
              plate("boat", z_order=1, depth_alpha=1.0, coverage="partial",
                    anchor=(0.30, 0.45, 0.62, 0.60))])


def test_depth_exception_needs_a_reason():
    plates = [plate("bg", z_order=0, depth_alpha=1.0),
              plate("reflection", z_order=1, depth_alpha=1.0, coverage="partial",
                    anchor=(0.30, 0.60, 0.68, 0.72))]
    spec = shot(plates, depth_exceptions={"reflection": "倒影与背景同深度平面"})
    assert spec.depth_exceptions == {"reflection": "倒影与背景同深度平面"}

    with pytest.raises(ValidationError, match="必须写明理由"):
        shot([plate("bg", z_order=0, depth_alpha=1.0),
              plate("reflection", z_order=1, depth_alpha=1.0, coverage="partial",
                    anchor=(0.30, 0.60, 0.68, 0.72))],
             depth_exceptions={"reflection": " "})


def test_depth_exception_must_reference_a_known_plate():
    with pytest.raises(ValidationError, match="引用了未知图层"):
        shot([plate("bg", z_order=0)], depth_exceptions={"ghost": "不存在"})


def test_locked_region_may_sit_under_a_nearer_plate():
    """A subject partly hidden by a nearer plate is a composition, not an error.
    The rigidity gate measures the visible part and reports the occlusion."""
    locked = RegionSpec(id="boat_lock", role="rigid_object", permission="locked",
                        box=box((0.20, 0.50, 0.70, 0.70)))
    plates = [plate("bg", z_order=0),
              plate("reeds", source="generated_asset", z_order=1, depth_alpha=0.49,
                    coverage="partial", anchor=(0.24, 0.58, 0.57, 1.02))]
    assert shot(plates, regions=[locked]).plates


def test_duplicate_z_order_is_rejected():
    with pytest.raises(ValidationError, match="duplicate plate z_order"):
        shot([plate("bg", z_order=0), plate("boat", z_order=0, depth_alpha=0.7)])


# --------------------------------------------------------------- hole masks
def test_cut_out_plate_must_declare_its_hole():
    with pytest.raises(ValidationError, match="必须给出 hole_mask"):
        plate("boat", z_order=1, depth_alpha=0.7, coverage="partial",
              anchor=(0.30, 0.45, 0.62, 0.60), hole_mask=False)


def test_generated_asset_needs_no_hole():
    spec = plate("reeds", source="generated_asset", z_order=1, depth_alpha=0.49,
                 coverage="partial", anchor=(0.24, 0.58, 0.57, 1.02))
    assert spec.hole_mask is None


def test_background_cannot_have_a_hole_mask():
    with pytest.raises(ValidationError, match="背景层没有 hole_mask"):
        PlateSpec(id="bg", source="original", path="bg.png", sha256=HASH, z_order=0,
                  depth_alpha=1.0, coverage="full_frame",
                  hole_mask="mask.png", hole_mask_sha256=HASH)


def test_region_plate_id_must_reference_a_plate():
    locked = RegionSpec(id="boat_lock", role="rigid_object", permission="locked",
                        box=box((0.30, 0.45, 0.62, 0.60)), plate_id="ghost")
    with pytest.raises(ValidationError, match="引用了未知图层"):
        shot(three_planes(), regions=[locked])


def test_region_plate_id_without_plates_is_rejected():
    locked = RegionSpec(id="boat_lock", role="rigid_object", permission="locked",
                        box=box((0.30, 0.45, 0.62, 0.60)), plate_id="boat")
    with pytest.raises(ValidationError, match="镜头没有图层"):
        shot(regions=[locked])


# ------------------------------------------------------------ style policy
class Policy:
    allowed = True
    camera_moves = ["slow_push_in"]
    max_plates = 3
    depth_alpha_min = 0.45
    depth_alpha_max = 0.85


def test_policy_allows_a_matching_shot():
    enforce_policy(Policy, shot_id="shot_001", move="slow_push_in", plates=three_planes())


def test_policy_refuses_a_style_without_parallax():
    class Off(Policy):
        allowed = False
    with pytest.raises(ValueError, match="未允许分层"):
        enforce_policy(Off, shot_id="shot_001", move="slow_push_in", plates=three_planes())


def test_policy_refuses_an_unlisted_camera_move():
    with pytest.raises(ValueError, match="不在该风格允许的分层镜头类型"):
        enforce_policy(Policy, shot_id="shot_001", move="scroll_pan", plates=three_planes())


def test_policy_refuses_too_many_plates():
    class Tight(Policy):
        max_plates = 2
    with pytest.raises(ValueError, match="层超过上限"):
        enforce_policy(Tight, shot_id="shot_001", move="slow_push_in", plates=three_planes())


def test_policy_checks_alpha_only_for_inner_planes():
    """The background defines the reference distance, so alpha 1.0 is always fine."""
    class Narrow(Policy):
        depth_alpha_min = 0.6
        depth_alpha_max = 0.8
    with pytest.raises(ValueError, match="depth_alpha"):
        enforce_policy(Narrow, shot_id="shot_001", move="slow_push_in", plates=three_planes())


def test_parallax_spec_requires_moves_when_allowed():
    from drama_studio.domain.style.presets import ParallaxSpec
    with pytest.raises(ValidationError, match="必须声明 camera_moves"):
        ParallaxSpec(allowed=True)
    assert ParallaxSpec(allowed=True, camera_moves=["slow_push_in"]).allowed
