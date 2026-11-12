from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.config import find_project_root
from drama_studio.domain.style.presets import (
    STYLE_ENTITY_FIELDS,
    load_style_presets,
)
from drama_studio.infrastructure.storage.store import STYLE_FIELDS

ROOT = Path(__file__).resolve().parents[1]
CORE_STYLES = {"court_green_fine_line", "ink_wash"}

# Same guard as tests/test_no_hardcoded_works.py: production config must not
# name a specific work or poem.
FORBIDDEN = ("春江", "洛神", "曹植", "山海经", "山海經", "翩若")


def test_exactly_two_core_styles() -> None:
    registry = load_style_presets(ROOT)
    core = {p.id for p in registry.styles.values() if p.category == "core"}
    assert core == CORE_STYLES
    assert registry.schema_version
    assert registry.get("shinkai_scenery").category == "scene"
    assert registry.get("ghibli_scenery").category == "scene"


def test_presets_are_partial_until_a_full_film_exists() -> None:
    registry = load_style_presets(ROOT)
    for preset in registry.styles.values():
        if preset.category == "core":
            assert preset.validation_status == "PARTIAL"
        else:
            assert preset.validation_status in ("NOT_RUN", "PARTIAL")


def test_presets_carry_required_visual_contract() -> None:
    registry = load_style_presets(ROOT)
    for preset in registry.styles.values():
        assert preset.name and preset.name_en
        assert preset.visual_language
        assert preset.positive_prompt
        assert preset.negative_prompt
        assert preset.color_palette
        assert all(color.startswith("#") and len(color) == 7 for color in preset.color_palette.values())
        assert preset.aspect_ratio == "9:16"
        assert preset.applicable_content_types
        assert preset.source_files and all((ROOT / rel).is_file() for rel in preset.source_files)
        for rel in preset.reference_assets:
            assert (ROOT / rel).is_file()
        texture_asset = preset.compositing.texture.asset
        assert texture_asset is None or (ROOT / texture_asset).is_file()
        assert preset.motion.primary
        assert preset.compositing.primitives
        assert 0.0 <= preset.compositing.texture.opacity <= 0.3
        assert preset.motion.camera.default in preset.motion.camera.allowed
        assert 1.0 < preset.motion.camera.push_scale_max <= 1.2
        assert preset.motion.local_policy
        assert preset.motion.transition.type in (
            "crossfade", "ink_dissolve", "ink_reveal", "ink_spread"
        )
        assert 0.0 < preset.motion.transition.max_fraction <= 0.5


def test_style_entity_matches_workspace_schema() -> None:
    # A preset must be usable with WorkspaceStore.create_style without a
    # translation table that could drift.
    assert STYLE_ENTITY_FIELDS == tuple(STYLE_FIELDS)
    preset = load_style_presets(ROOT).get("ink_wash")
    entity = preset.as_style_entity()
    assert set(entity) == set(STYLE_FIELDS)
    assert "motion" not in entity and "compositing" not in entity and "material" not in entity


def test_style_specific_animation_routes() -> None:
    registry = load_style_presets(ROOT)
    court = registry.get("court_green_fine_line")
    ink = registry.get("ink_wash")
    assert {"scroll_pan", "line_reveal"} <= set(court.compositing.primitives)
    assert {"ink_matte", "ink_diffusion"} <= set(ink.compositing.primitives)
    assert "scroll_pan" in court.motion.primary
    assert "ink_diffusion" in ink.motion.primary
    # The two styles keep independent mechanical policies, selected by config
    # rather than by a style branch in code.
    assert court.motion.camera.default == "scroll_pan"
    assert ink.motion.camera.default == "slow_push_in"
    assert court.motion.transition.type == "crossfade"
    assert ink.motion.transition.type == "ink_dissolve"
    assert court.motion.local_policy["ink_diffusion"].enabled is False
    assert ink.motion.local_policy["ink_diffusion"].enabled is True
    for preset in (court, ink):
        assert preset.motion.wan.allowed is True
        # Layered 2.5D is now permitted, and each style names the shot types it
        # permits instead of leaving the policy unimplemented.
        assert preset.compositing.parallax.allowed is True
        assert preset.compositing.parallax.camera_moves
    assert "scroll_pan" in court.compositing.parallax.camera_moves
    assert "scroll_pan" not in ink.compositing.parallax.camera_moves
    # A pan walks the window across the plate; a dolly does not.
    assert (court.compositing.parallax.background_margin
            > ink.compositing.parallax.background_margin)


def test_no_work_names_in_production_config() -> None:
    hits: list[str] = []
    for path in sorted((ROOT / "config").glob("*.yaml")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for word in FORBIDDEN:
            if word in text:
                hits.append(f"{path.name}: {word}")
    assert not hits, "specific works leaked into production config: " + "; ".join(hits)


def test_unknown_preset_is_rejected() -> None:
    registry = load_style_presets(ROOT)
    with pytest.raises(KeyError):
        registry.get("no_such_style")


def test_find_project_root_still_locates_config() -> None:
    assert find_project_root(ROOT) == ROOT.resolve()


def test_production_baselines_record_the_approved_ab_choice() -> None:
    registry = load_style_presets(ROOT)
    assert set(registry.production_baselines) == CORE_STYLES
    court = registry.production_baselines["court_green_fine_line"]
    ink = registry.production_baselines["ink_wash"]
    assert {key: value.variant for key, value in court.shots.items()} == {
        "shot_001": "A", "shot_002": "A"}
    assert {key: value.variant for key, value in ink.shots.items()} == {
        "shot_001": "B", "shot_002": "A"}
    for baseline in (court, ink):
        for shot in baseline.shots.values():
            assert shot.prompt
            assert shot.prompt_sha256
            assert shot.rationale


def test_four_styles_are_negatively_isolated() -> None:
    registry = load_style_presets(ROOT)
    assert set(registry.ids()) == CORE_STYLES | {"shinkai_scenery", "ghibli_scenery"}
    negative = {preset.id: preset.negative_prompt for preset in registry.styles.values()}
    # Each style explicitly rejects the other visual languages.
    assert "水墨" in negative["court_green_fine_line"]
    assert "动漫" in negative["ink_wash"]
    assert "水墨" in negative["shinkai_scenery"]
    assert "水墨" in negative["ghibli_scenery"]
    assert len(set(negative.values())) == 4
