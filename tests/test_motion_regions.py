from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from drama_studio.motion.local import LayerRefused, effective_exclusions, prepare_layers
from drama_studio.domain.motion.spec import (
    Box,
    LocalMotionSpec,
    MaskSpec,
    RegionSpec,
    ShotSpec,
)
from drama_studio.production import ProductionError, _load_regions
from drama_studio.domain.style.presets import load_style_presets

ROOT = Path(__file__).resolve().parents[1]


def region(region_id: str, role: str, permission: str, box: tuple[float, float, float, float],
           **kwargs) -> RegionSpec:
    return RegionSpec(
        id=region_id,
        role=role,
        permission=permission,
        box=Box(x0=box[0], y0=box[1], x1=box[2], y1=box[3]),
        **kwargs,
    )


BOAT_BOX = (0.36, 0.45, 0.62, 0.60)
REFLECTION_BOX = (0.30, 0.60, 0.68, 0.72)
WATER_BOX = (0.0, 0.50, 1.0, 0.80)


def base_regions() -> list[RegionSpec]:
    return [
        region("boat", "rigid_object", "locked", BOAT_BOX),
        region("reflection", "reflection", "controlled", REFLECTION_BOX, follows="boat"),
        region("water", "fluid_surface", "controlled", WATER_BOX, max_amplitude_px=4.0),
    ]


def water_layer(**kwargs) -> LocalMotionSpec:
    payload = dict(
        layer_id="water",
        motion_type="water_ripple",
        mask=MaskSpec(y0=0.50, y1=0.80),
        region_id="water",
        amplitude=2.5,
        frequency=0.1,
    )
    payload.update(kwargs)
    return LocalMotionSpec(**payload)


def prepare(tmp_path: Path, layer: LocalMotionSpec, regions: list[RegionSpec]):
    from PIL import Image

    ink = load_style_presets(ROOT).get("ink_wash")
    policy = ink.motion.local_policy.get(layer.motion_type)
    base = Image.new("RGB", (540, 960), (200, 200, 200))
    return prepare_layers(
        root=ROOT,
        base_half=base,
        gray_half=base.convert("L"),
        spec=layer,
        policy=policy,
        out_dir=tmp_path,
        duration=2.0,
        fps=24,
        regions=regions,
    )


def test_rigid_object_must_be_locked_or_hard_excluded() -> None:
    with pytest.raises(ValidationError, match="rigid_object"):
        region("boat", "rigid_object", "controlled", BOAT_BOX)


def test_reflection_needs_a_followed_subject() -> None:
    with pytest.raises(ValidationError, match="follows"):
        region("reflection", "reflection", "controlled", REFLECTION_BOX)


def test_reflection_follows_must_be_rigid_object() -> None:
    with pytest.raises(ValidationError, match="rigid_object"):
        ShotSpec(
            id="shot_001",
            source="a.png",
            duration_seconds=2,
            regions=[
                region("water", "fluid_surface", "controlled", WATER_BOX),
                region("reflection", "reflection", "controlled", REFLECTION_BOX,
                       follows="water"),
            ],
        )


def test_locked_region_cannot_be_animated() -> None:
    with pytest.raises(ValidationError, match="禁止"):
        ShotSpec(
            id="shot_001",
            source="a.png",
            duration_seconds=2,
            regions=base_regions(),
            local_motion=[water_layer(region_id="boat")],
        )


def test_unknown_region_reference_is_rejected() -> None:
    with pytest.raises(ValidationError, match="未知区域"):
        ShotSpec(
            id="shot_001",
            source="a.png",
            duration_seconds=2,
            regions=base_regions(),
            local_motion=[water_layer(region_id="ghost")],
        )


def test_reflection_layer_must_use_reflection_distortion() -> None:
    layer = LocalMotionSpec(
        layer_id="reflection",
        motion_type="water_ripple",
        mask=MaskSpec(y0=0.60, y1=0.72),
        region_id="reflection",
        amplitude=1.0,
        frequency=0.1,
    )
    with pytest.raises(ValidationError, match="不在区域.*允许的类型"):
        ShotSpec(
            id="shot_001",
            source="a.png",
            duration_seconds=2,
            regions=base_regions(),
            local_motion=[layer],
        )


def test_reflection_distortion_needs_a_reflection_region() -> None:
    layer = LocalMotionSpec(
        layer_id="reflection",
        motion_type="reflection_distortion",
        mask=MaskSpec(y0=0.60, y1=0.72),
        amplitude=1.0,
        frequency=0.1,
    )
    with pytest.raises(ValidationError, match="必须绑定"):
        ShotSpec(
            id="shot_001",
            source="a.png",
            duration_seconds=2,
            regions=base_regions(),
            local_motion=[layer],
        )


def test_missing_mask_is_rejected() -> None:
    with pytest.raises(ValidationError, match="mask"):
        LocalMotionSpec(layer_id="water", motion_type="water_ripple", amplitude=2.0,
                        frequency=0.1)


def test_water_exclusions_include_locked_subject_and_reflection() -> None:
    exclusions = effective_exclusions(water_layer(), base_regions())
    assert {item.id for item in exclusions} == {"boat", "reflection"}


def test_water_alpha_is_zero_inside_locked_boat_and_reflection(tmp_path: Path) -> None:
    layer = prepare(tmp_path, water_layer(), base_regions())
    assert set(layer.info["protection"]["excluded_regions"]) == {"boat", "reflection"}
    assert layer.info["protection"]["alpha_coverage"] > 0.01
    first = Path(layer.info["frames_dir"]) / "f_0000.png"
    with Image.open(first) as image:
        alpha = image.getchannel("A")
        width, height = alpha.size

        def core(box):
            x0, y0, x1, y1 = box
            # stay outside the exclusion feather (25 px at half resolution ->
            # 12 px; a 40 px inset lands in the hard core of the hole)
            return alpha.crop((int(x0 * (width - 1)) + 40, int(y0 * (height - 1)) + 40,
                               int(x1 * (width - 1)) - 40, int(y1 * (height - 1)) - 40))

        assert core(BOAT_BOX).getextrema()[1] == 0
        assert core(REFLECTION_BOX).getextrema()[1] == 0


def test_reflection_layer_is_not_excluded_by_itself(tmp_path: Path) -> None:
    layer = LocalMotionSpec(
        layer_id="reflection",
        motion_type="reflection_distortion",
        mask=MaskSpec(y0=0.60, y1=0.72),
        region_id="reflection",
        amplitude=1.2,
        frequency=0.14,
    )
    exclusions = effective_exclusions(layer, base_regions())
    assert "reflection" not in {item.id for item in exclusions}
    rendered = prepare(tmp_path, layer, base_regions())
    assert rendered.info["protection"]["region_id"] == "reflection"
    assert rendered.info["protection"]["role"] == "reflection"
    assert rendered.info["alpha_coverage"] > 0.005


def test_fully_excluded_mask_is_refused(tmp_path: Path) -> None:
    layer = LocalMotionSpec(
        layer_id="water",
        motion_type="water_ripple",
        mask=MaskSpec(kind="box", x0=0.38, y0=0.47, x1=0.60, y1=0.58),
        amplitude=2.5,
        frequency=0.1,
    )
    with pytest.raises(LayerRefused, match="mask_fully_excluded"):
        prepare(tmp_path, layer, base_regions())


def test_amplitude_above_region_cap_is_refused(tmp_path: Path) -> None:
    regions = base_regions()
    regions[-1] = region("water", "fluid_surface", "controlled", WATER_BOX,
                         max_amplitude_px=1.0)
    with pytest.raises(LayerRefused, match="amplitude_exceeds_region_cap"):
        prepare(tmp_path, water_layer(amplitude=3.0), regions)


def test_no_regions_keeps_legacy_layers_working(tmp_path: Path) -> None:
    layer = LocalMotionSpec(
        layer_id="water",
        motion_type="water_ripple",
        mask=MaskSpec(y0=0.50, y1=0.80),
        amplitude=2.5,
        frequency=0.1,
    )
    rendered = prepare(tmp_path, layer, [])
    assert rendered.info["protection"]["region_id"] is None
    assert rendered.info["protection"]["excluded_regions"] == []


def test_region_file_supports_legacy_and_semantic_formats(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"shots": {"shot_001": [
        {"layer_id": "water", "motion_type": "water_ripple",
         "mask": {"y0": 0.5, "y1": 0.8}}
    ]}}), encoding="utf-8")
    loaded = _load_regions(legacy)
    assert loaded["shot_001"]["model"] == "legacy"
    assert loaded["shot_001"]["regions"] == []
    assert len(loaded["shot_001"]["layers"]) == 1

    semantic = tmp_path / "semantic.json"
    semantic.write_text(json.dumps({"shots": {"shot_001": {
        "regions": [{"id": "boat", "role": "rigid_object", "permission": "locked",
                     "box": {"x0": 0.3, "y0": 0.4, "x1": 0.6, "y1": 0.6}}],
        "layers": [{"layer_id": "water", "motion_type": "water_ripple",
                    "mask": {"y0": 0.5, "y1": 0.8}}],
    }}}), encoding="utf-8")
    loaded = _load_regions(semantic)
    assert loaded["shot_001"]["model"] == "semantic"
    assert loaded["shot_001"]["regions"][0]["id"] == "boat"
    assert len(loaded["shot_001"]["layers"]) == 1


def test_region_file_rejects_unknown_fields(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"shots": {"shot_001": {"regions": [], "layers": [],
                                                      "whatever": []}}}),
                   encoding="utf-8")
    with pytest.raises(ProductionError, match="未知字段"):
        _load_regions(bad)
