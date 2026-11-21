"""Tests for Z-Image Turbo Visual Style Atlas and 7-Dimension Prompt Engine."""

import pytest
from pathlib import Path
from drama_studio.domain.style.z_image_atlas import (
    ZImageStyleAtlas,
    ZImagePromptCompiler,
    ZImageBenchmarkSuite,
    ZImageStyle,
)


def test_z_image_atlas_load_all():
    atlas = ZImageStyleAtlas()
    # The atlas is meant to grow (38 core recipes + later additions such as cloud_palace_celestial).
    assert atlas.count() >= 38, f"Expected at least the 38 core styles, got {atlas.count()}"
    
    categories = atlas.list_categories()
    assert set(categories.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "T"}


def test_all_styles_have_7_dimensions():
    atlas = ZImageStyleAtlas()
    for s in atlas.list_styles():
        dims = s.dimensions
        assert dims.subject, f"{s.id} missing subject dimension"
        assert dims.scene, f"{s.id} missing scene dimension"
        assert dims.composition, f"{s.id} missing composition dimension"
        assert dims.lighting, f"{s.id} missing lighting dimension"
        assert dims.medium_style, f"{s.id} missing medium_style dimension"
        assert dims.color_texture, f"{s.id} missing color_texture dimension"
        assert dims.constraints, f"{s.id} missing constraints dimension"
        assert s.positive_prompt, f"{s.id} missing positive_prompt"


def test_atlas_lookup_by_id_and_code():
    atlas = ZImageStyleAtlas()
    
    # By ID
    s1 = atlas.get_style("editorial_fashion")
    assert s1.name == "高级时尚人像"
    assert s1.code == "01"
    
    # By Code
    s2 = atlas.get_style("01")
    assert s2.id == "editorial_fashion"
    
    # Song Aesthetics
    song = atlas.get_style("12")
    assert song.id == "song_aesthetics"
    assert song.name == "宋式美学"


def test_prompt_compiler_7_dimensions():
    atlas = ZImageStyleAtlas()
    compiler = ZImagePromptCompiler()
    
    style = atlas.get_style("editorial_fashion")
    compiled = compiler.compile(
        style=style,
        subject="a woman in red hanfu holding a round fan",
        scene="in an ancient courtyard with bamboo trees",
        text_quote="DRAMA STUDIO"
    )
    
    assert "a woman in red hanfu holding a round fan" in compiled
    assert "in an ancient courtyard with bamboo trees" in compiled
    assert '"DRAMA STUDIO"' in compiled
    # Verify no traditional tag spam
    assert "masterpiece" not in compiled.lower()
    assert "8k" not in compiled.lower()


def test_prompt_compiler_strips_tag_spam():
    compiler = ZImagePromptCompiler()
    dirty = "A woman, masterpiece, 8k, photorealistic, best quality, ultra-detailed, smiling softly"
    cleaned = compiler.clean_noisy_tags(dirty)
    assert "masterpiece" not in cleaned.lower()
    assert "8k" not in cleaned.lower()
    assert "photorealistic" not in cleaned.lower()
    assert "smiling softly" in cleaned


def test_benchmark_suite_generation():
    atlas = ZImageStyleAtlas()
    suite = ZImageBenchmarkSuite(atlas)
    matrix = suite.generate_benchmark_matrix()
    
    assert len(matrix) == 14
    first = matrix[0]
    assert "compiled_prompt" in first
    assert first["di_forward_steps"] == 8
    assert first["guidance_scale"] == 0.0
    assert first["base_subject_key"] == "portrait"
