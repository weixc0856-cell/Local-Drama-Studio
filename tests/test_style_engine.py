"""Visual Style Engine: registry, compiler, consistency."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from drama_studio.config import find_project_root
from drama_studio.style_engine import (
    check_image,
    check_sequence,
    compile_image_prompt,
    compile_video_prompt,
    get_pack,
    list_packs,
    load_all,
)

ROOT = find_project_root()


def test_all_packs_load_and_validate() -> None:
    packs = load_all(ROOT)
    assert len(packs) == 21
    assert {"retro.collage", "retro.synthwave", "retro.pop_art", "retro.y2k"} <= set(packs)
    assert {"oriental.modern_chinese", "oriental.gongbi", "oriental.ink_wash"} <= set(packs)
    assert len(list_packs(ROOT, "artistic")) == 5
    for pack in packs.values():
        assert pack.identity.version == "1.0.0"
        assert pack.video.secondary_limit <= 2


def test_unknown_style_is_rejected() -> None:
    with pytest.raises(KeyError):
        get_pack(ROOT, "oriental.nope")


def test_image_prompt_uses_pack_and_never_leaks_hex() -> None:
    pack = get_pack(ROOT, "oriental.ink_wash")
    prompt = compile_image_prompt(
        pack, subject="a vast ancient river landscape",
        layers={"foreground": "near rocks", "background": "distant peaks"},
        camera_move="dolly_in",
    )
    assert "traditional Chinese ink wash painting" in prompt
    assert "xuan paper" in prompt
    assert "#" not in prompt
    assert "no letterbox" in prompt


def test_camera_move_must_be_allowed_by_style() -> None:
    pack = get_pack(ROOT, "oriental.gongbi")
    with pytest.raises(ValueError, match="not allowed"):
        compile_image_prompt(pack, subject="tower", layers={}, camera_move="orbit")


def test_video_prompt_respects_secondary_limit() -> None:
    pack = get_pack(ROOT, "retro.synthwave")
    prompt = compile_video_prompt(
        pack, camera_move="orbit", primary_motion="grid advancing",
        secondary_motions=["neon pulse", "cloud drift"],
    )
    assert "style motion" in prompt and "grid advancing" in prompt
    with pytest.raises(ValueError, match="secondary"):
        compile_video_prompt(
            pack, camera_move="orbit", primary_motion="grid advancing",
            secondary_motions=["a", "b", "c"],
        )


def test_check_image_flags_high_saturation_for_ink(tmp_path: Path) -> None:
    pack = get_pack(ROOT, "oriental.ink_wash")
    neon = Image.new("RGB", (576, 1024), (255, 40, 200))
    path = tmp_path / "neon.png"
    neon.save(path)
    issues = check_image(path, pack)
    assert any(item.code == "saturation_out_of_range" for item in issues)


def test_check_image_flags_letterbox(tmp_path: Path) -> None:
    pack = get_pack(ROOT, "oriental.ink_wash")
    image = Image.new("RGB", (576, 1024), (230, 226, 214))
    for y in range(0, 120):
        for x in range(0, 576):
            image.putpixel((x, y), (0, 0, 0))
    path = tmp_path / "bars.png"
    image.save(path)
    issues = check_image(path, pack)
    assert any(item.code == "letterbox" and item.level == "error" for item in issues)


def test_check_sequence_flags_luma_drift(tmp_path: Path) -> None:
    pack = get_pack(ROOT, "oriental.ink_wash")
    dark = tmp_path / "dark.png"
    light = tmp_path / "light.png"
    Image.new("RGB", (64, 64), (30, 30, 30)).save(dark)
    Image.new("RGB", (64, 64), (220, 220, 220)).save(light)
    issues = check_sequence([dark, light], pack)
    assert any(item.code == "luma_drift" for item in issues)
