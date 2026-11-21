"""Tests for the cinematic title-card renderer and the vetted OFL font registry."""

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERER = REPO_ROOT / "scripts" / "render_title_card.py"
MANIFEST = REPO_ROOT / "assets" / "fonts" / "font_manifest.json"


def load_renderer():
    spec = importlib.util.spec_from_file_location("title_renderer", RENDERER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r = load_renderer()
FONTS_PRESENT = all(spec["path"].exists() for spec in r.FONTS.values()) and \
    all(spec["path"].exists() for spec in r.LATIN_FONTS.values())
needs_fonts = pytest.mark.skipif(not FONTS_PRESENT, reason="font binaries not fetched")


def test_manifest_records_every_renderer_font():
    """Every font the renderer can use must be registered with a checksum and a licence."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = {w["file"] for f in data["fonts"] for w in f["selected_weights"]}
    for spec in list(r.FONTS.values()) + list(r.LATIN_FONTS.values()):
        rel = spec["path"].relative_to(REPO_ROOT).as_posix()
        assert rel in registered, f"{rel} is used by the renderer but absent from the font manifest"


def test_every_registered_font_declares_ofl():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for f in data["fonts"]:
        lic = f["license"]
        # Older Adobe entries store a dict; newer OFL entries store a descriptive string.
        text = lic.get("name", "") if isinstance(lic, dict) else lic
        assert "OFL" in text.upper() or "OPEN FONT LICENSE" in text.upper(),             f"{f['asset_id']} has no OFL licence recorded"


@needs_fonts
def test_ofl_texts_are_present_and_genuine():
    for folder in ("lxgw-wenkai", "zhuque-fangsong", "cinzel", "cormorantgaramond",
                   "marcellus", "playfairdisplay"):
        base = REPO_ROOT / "assets" / "fonts" / folder
        texts = list(base.glob("OFL.txt")) + list(base.glob("LICENSE.txt"))
        assert texts, f"{folder} has no licence text"
        assert any("SIL OPEN FONT LICENSE" in t.read_text(encoding="utf-8", errors="ignore")
                   for t in texts), f"{folder} licence text is not the OFL"


@needs_fonts
@pytest.mark.parametrize("font_key", list(r.FONTS))
def test_title_renders_for_every_cjk_font(tmp_path, font_key):
    out = r.render_title_card(tmp_path / f"{font_key}.png", font_key=font_key,
                              width=832, height=480, title_size=76)
    im = Image.open(out)
    assert im.size == (832, 480)
    # The title band must contain bright glyph pixels, not an empty background.
    band = im.crop((0, 150, 832, 300)).convert("L")
    assert max(band.get_flattened_data()) > 180, f"{font_key} rendered no visible title"


@needs_fonts
def test_cjk_title_has_no_missing_glyph_boxes(tmp_path):
    """A missing glyph renders as a hollow rectangle; all four characters must differ."""
    out = r.render_title_card(tmp_path / "glyphs.png", font_key="lxgw_wenkai_medium",
                              width=1664, height=960, title_size=150)
    im = Image.open(out).convert("L")
    # Split the title band into four equal cells and require distinct ink patterns.
    band = im.crop((440, 320, 1230, 470))
    w = band.width // 4
    cells = [band.crop((i * w, 0, (i + 1) * w, band.height)) for i in range(4)]
    signatures = [sum(c.get_flattened_data()) for c in cells]
    assert all(s > 0 for s in signatures), "a title character rendered blank"
    assert len(set(signatures)) == 4, "two title characters rendered identically (tofu boxes)"


@needs_fonts
def test_latin_weight_axis_actually_changes_rendering(tmp_path):
    a = r.render_title_card(tmp_path / "w400.png", latin_key="cinzel", latin_weight=400,
                            width=832, height=480, title_size=76)
    b = r.render_title_card(tmp_path / "w500.png", latin_key="cinzel", latin_weight=500,
                            width=832, height=480, title_size=76)
    assert Image.open(a).tobytes() != Image.open(b).tobytes(), \
        "Cinzel weight 400 and 500 rendered identically; the variation axis is not applied"


@needs_fonts
def test_gradient_fill_is_lighter_at_the_top(tmp_path):
    out = r.render_title_card(tmp_path / "grad.png", width=1664, height=960, title_size=150)
    im = Image.open(out).convert("RGB")
    # Sample inside the glyph band: the warm gradient runs light -> darker downward.
    top = im.crop((460, 340, 1220, 360))
    bottom = im.crop((460, 430, 1220, 450))

    def bright_glyph_pixels(box):
        px = [p for p in box.get_flattened_data() if sum(p) > 420]
        return sum(sum(p) for p in px) / len(px) if px else 0

    assert bright_glyph_pixels(top) > bright_glyph_pixels(bottom)


@needs_fonts
def test_rule_fades_at_both_ends(tmp_path):
    out = r.render_title_card(tmp_path / "rule.png", width=1664, height=960, title_size=150)
    im = Image.open(out).convert("L")
    # Locate the rule row: the brightest row in the band below the subtitle.
    band = im.crop((700, 590, 970, 640))
    rows = [sum(band.crop((0, y, band.width, y + 1)).get_flattened_data())
            for y in range(band.height)]
    y = rows.index(max(rows))
    row = band.crop((0, y, band.width, y + 1))
    vals = list(row.get_flattened_data())
    centre = max(vals[len(vals) // 2 - 10:len(vals) // 2 + 10])
    assert centre > vals[0], "rule does not fade at the left end"
    assert centre > vals[-1], "rule does not fade at the right end"


@needs_fonts
def test_flat_fill_and_hard_rule_options_still_work(tmp_path):
    out = r.render_title_card(tmp_path / "flat.png", gradient=False, fade_rule=False,
                              width=832, height=480, title_size=76)
    assert Image.open(out).size == (832, 480)