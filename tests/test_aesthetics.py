from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from drama_studio.domain.aesthetics import (
    build_variants,
    compile_prompt,
    design_for_quality,
    generate_plan,
    infer_base_design,
    load_plan,
    write_plan,
)
from drama_studio.application.quality import check_aesthetic_risk, check_color_continuity
from drama_studio.application.script_engine import ProductionScript
from drama_studio.domain.style.presets import load_style_presets

ROOT = Path(__file__).resolve().parents[1]


def _script(style_id: str, scenes: list[str]) -> ProductionScript:
    return ProductionScript.model_validate({
        "schema_version": "1.0",
        "title": "美学测试",
        "logline": "镜头美学数据结构测试。",
        "lines": [
            {"line_id": f"line_{index:03d}", "text": f"测试句{index}", "source_segment_id": f"sub_{index:03d}"}
            for index in range(1, len(scenes) + 1)
        ],
        "shots": [
            {"shot_id": f"shot_{index:03d}", "index": index, "type": "image",
             "duration_seconds": 3.0, "motion": "slow push-in",
             "scene_prompt": scene, "visual_prompt": scene, "negative_prompt": "",
             "line_ids": [f"line_{index:03d}"]}
            for index, scene in enumerate(scenes, start=1)
        ],
        "style_id": style_id,
        "style_sha256": "a" * 64,
        "package_sha256": "b" * 64,
        "model": "test",
        "generated_at": "2026-11-04T00:00:00+00:00",
    })


def test_both_styles_carry_six_dimension_profiles() -> None:
    registry = load_style_presets(ROOT)
    for preset in registry.styles.values():
        profile = preset.aesthetic_profile
        assert profile.composition.preferred_strategies
        assert profile.lighting.preferred
        assert profile.color.dominant_keys
        assert profile.depth.default_layers in (1, 2, 3)
        assert profile.mise_en_scene.positive_constraints
        assert profile.storytelling.emotion_vocabulary
    ink = registry.get("ink_wash").aesthetic_profile
    court = registry.get("court_green_fine_line").aesthetic_profile
    assert ink.color.continuity_group != court.color.continuity_group
    assert ink.lighting.default_direction == "diffuse"
    assert court.lighting.default_direction == "side_left"


def test_plan_variants_change_exactly_one_axis() -> None:
    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["远山与江面", "月轮与云海"])
    plan = generate_plan(script, preset, axes={"shot_001": "composition", "shot_002": "lighting"})
    for shot_set in plan.shots:
        a, b = shot_set.variants
        assert a.changed_axis == b.changed_axis == shot_set.axis
        left = a.design.model_dump(exclude={shot_set.axis})
        right = b.design.model_dump(exclude={shot_set.axis})
        assert left == right
        assert a.design.model_dump()[shot_set.axis] != b.design.model_dump()[shot_set.axis]


def test_color_axis_uses_two_palette_dominants() -> None:
    preset = load_style_presets(ROOT).get("court_green_fine_line")
    script = _script("court_green_fine_line", ["楼阁与江流"])
    plan = generate_plan(script, preset, axes={"shot_001": "color"})
    a, b = plan.shots[0].variants
    assert a.design.color.dominant != b.design.color.dominant
    for variant in (a, b):
        for key in [variant.design.color.dominant, *variant.design.color.secondary,
                    *variant.design.color.accent]:
            assert key in preset.color_palette


def test_prompt_order_and_negative_capability() -> None:
    preset = load_style_presets(ROOT).get("court_green_fine_line")
    script = _script("court_green_fine_line", ["宋代楼阁与江流"])
    plan = generate_plan(script, preset, axes={"shot_001": "composition"})
    shot = plan.shots[0]
    compiled = compile_prompt(shot, shot.variants[0], preset, negative_supported=False)
    assert list(compiled.sections) == [
        "subject", "composition", "environment", "lighting", "color", "style", "material"
    ]
    assert compiled.prompt.startswith(compiled.sections["subject"])
    assert "横屏16:9构图" in compiled.prompt
    assert "宋代院体青绿工笔" in compiled.prompt
    assert compiled.negative_supported is False
    assert compiled.negative_prompt
    assert compiled.positive_constraints
    assert compiled.spec_sha256 and compiled.prompt_sha256


def test_unknown_color_key_is_rejected_by_compiler() -> None:
    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["远山与江面"])
    plan = generate_plan(script, preset, axes={"shot_001": "composition"})
    shot = plan.shots[0]
    broken = shot.variants[0].design.model_copy(deep=True)
    broken.color.dominant = "不存在的颜色"
    from drama_studio.domain.aesthetics import ShotVariant

    variant = ShotVariant(
        variant_id="A", label="x", rationale="x", changed_axis="composition", design=broken
    )
    with pytest.raises(ValueError, match="not in style palette"):
        compile_prompt(shot, variant, preset)


def test_plan_roundtrip(tmp_path: Path) -> None:
    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["远山与江面", "月夜与云海"])
    plan = generate_plan(script, preset)
    path = tmp_path / "plan.json"
    write_plan(plan, path)
    again = load_plan(path)
    assert again.model_dump() == plan.model_dump()


def test_aesthetic_risk_localises_a_subject(tmp_path: Path) -> None:
    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["中心主体"])
    plan = generate_plan(script, preset, axes={"shot_001": "composition"})
    design = design_for_quality(plan.shots[0], "A")["design"]

    centered = Image.new("L", (576, 1024), 30)
    centered.paste(220, (200, 380, 376, 644))
    centered_path = tmp_path / "centered.png"
    centered.convert("RGB").save(centered_path)
    left = Image.new("L", (576, 1024), 30)
    left.paste(220, (20, 380, 196, 644))
    left_path = tmp_path / "left.png"
    left.convert("RGB").save(left_path)

    risk_center = check_aesthetic_risk(centered_path, design, preset.color_palette)
    risk_left = check_aesthetic_risk(left_path, design, preset.color_palette)
    assert risk_center["aesthetic_status"] == "PENDING_HUMAN_REVIEW"
    assert risk_center["composition"]["centroid"][0] > risk_left["composition"]["centroid"][0]
    assert risk_center["composition"]["placement_error"] < 0.3


def test_color_continuity_flags_a_jump(tmp_path: Path) -> None:
    same_a = tmp_path / "a.png"
    same_b = tmp_path / "b.png"
    Image.new("RGB", (64, 64), (120, 120, 120)).save(same_a)
    Image.new("RGB", (64, 64), (122, 122, 122)).save(same_b)
    dark = tmp_path / "dark.png"
    Image.new("RGB", (64, 64), (10, 10, 10)).save(dark)
    ok = check_color_continuity([{"id": "a", "path": same_a}, {"id": "b", "path": same_b}])
    assert ok["status"] == "OK"
    jump = check_color_continuity([{"id": "a", "path": same_a}, {"id": "b", "path": dark}])
    assert jump["status"] == "RISK"


def test_snapshot_is_never_overwritten(tmp_path: Path) -> None:
    from drama_studio.application.production import build_aesthetic_jobs

    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["远山与江面"])
    plan = generate_plan(script, preset)
    snapshot = tmp_path / "snapshot"
    result = build_aesthetic_jobs(plan, root=ROOT, snapshot_dir=snapshot, variant_id="A")
    assert result["jobs_count"] == 1
    manifest = json.loads((snapshot / "jobs_A.json").read_text(encoding="utf-8"))
    assert manifest[0]["id"] == "shot_001_A"
    provenance = json.loads((snapshot / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["negative_supported"] is False
    with pytest.raises(Exception, match="not empty"):
        build_aesthetic_jobs(plan, root=ROOT, snapshot_dir=snapshot, variant_id="A")


def test_non_center_base_keeps_a_side() -> None:
    preset = load_style_presets(ROOT).get("court_green_fine_line")
    script = _script("court_green_fine_line", ["建筑细节"])
    base = infer_base_design(script.shots[0], preset)
    base = base.model_copy(update={
        "composition": base.composition.model_copy(update={"subject_position": "right_third"})
    })
    a, b = build_variants(base, "composition", preset)
    assert a.design.composition.subject_position == "right_third"
    assert b.design.composition.subject_position == "left_third"


def test_lab_mean_is_normalised(tmp_path: Path) -> None:
    from drama_studio.application.quality import image_metrics

    path = tmp_path / "white.png"
    Image.new("RGB", (64, 64), (245, 245, 240)).save(path)
    metrics = image_metrics(path)
    assert 85 < metrics["lab_mean"][0] <= 100
    assert abs(metrics["lab_mean"][1]) < 12
    assert abs(metrics["lab_mean"][2]) < 12


def test_dynamic_aesthetic_report_writes_and_flags_nothing(tmp_path: Path) -> None:
    from drama_studio.application.quality import check_dynamic_aesthetics

    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    Image.new("RGB", (64, 64), (120, 120, 120)).save(a)
    Image.new("RGB", (64, 64), (122, 122, 120)).save(b)
    manifest = {
        "shots": [
            {"id": "shot_001", "camera": {"move": "static"},
             "sample_frames": [{"name": "first", "path": str(a)}],
             "region_checks": {"isolates_local_motion": True,
                               "structure_bands": [{"band": "sky_top", "mean_abs_diff": 0.001}]},
             "layers": [{"layer_id": "cloud"}]},
            {"id": "shot_002", "camera": {"move": "static"},
             "sample_frames": [{"name": "first", "path": str(b)}],
             "region_checks": {"isolates_local_motion": True,
                               "structure_bands": [{"band": "sky_top", "mean_abs_diff": 0.002}]},
             "layers": []},
        ]
    }
    path = tmp_path / "motion_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    report = check_dynamic_aesthetics(path)
    assert report["risk_severity"] == "ok"
    assert report["aesthetic_status"] == "PENDING_HUMAN_REVIEW"
    assert (tmp_path / "dynamic_aesthetic_report.json").is_file()
    assert report["continuity"]["pairs"][0]["delta_e"] < 15


def test_plan_rejects_mixed_continuity_groups() -> None:
    from pydantic import ValidationError

    from drama_studio.domain.aesthetics import AestheticPlan

    preset = load_style_presets(ROOT).get("ink_wash")
    script = _script("ink_wash", ["远山与江面"])
    data = generate_plan(script, preset).model_dump()
    data["shots"][0]["variants"][0]["design"]["color"]["continuity_group"] = "other_style"
    with pytest.raises(ValidationError) as exc:
        AestheticPlan.model_validate(data)
    # Either invariant may fire first; both reject the mixed continuity group.
    assert "continuity_group" in str(exc.value) or "A/B differ outside" in str(exc.value)
