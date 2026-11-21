#!/usr/bin/env python3
"""scripts/render_title_card.py
Reusable cinematic title-card renderer for Oriental / narrative video openings.

Why this exists: the style atlas measurements showed Z-Image renders unspecified
lettering as garbled glyphs, so on-screen titles must be composited, never generated.
This renders them deterministically with vetted OFL fonts.

Typography choices (all measured against a plain printed-Song baseline):
  * tracking      ~0.30 em on the CJK title, so four characters breathe instead of
                  sitting like a newspaper headline
  * fill          vertical warm-gold gradient (#F7F1E3 -> #D8C39E) instead of flat white,
                  so the glyphs sit *in* the dark background rather than on top of it
  * glow          a very soft warm bloom under the glyphs, same hue as the fill
  * latin sub     Cinzel (OFL) with wide tracking, lighter optical weight than the title

Fonts (all SIL OFL 1.1, verified from the upstream repos; see assets/fonts/*/):
  lxgw_wenkai        霞鹜文楷  — rounded kaishu warmth, the general-purpose choice
  lxgw_wenkai_light  霞鹜文楷 Light — airier, more 仙气 at large sizes
  zhuque_fangsong    朱雀仿宋  — slender literati fangsong, quiet and refined
  source_han_serif   思源宋体 Bold — the printed-Song baseline, kept for comparison

Usage:
  python scripts/render_title_card.py --preview           # render every font side by side
  python scripts/render_title_card.py --font lxgw_wenkai --out card.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = REPO_ROOT / "assets" / "fonts"

FONTS = {
    "source_han_serif": {
        "path": FONT_DIR / "source-han-serif-cn" / "SourceHanSerifCN-Bold.otf",
        "label": "思源宋体 Bold（原基线）",
        "license": "SIL OFL 1.1",
    },
    "lxgw_wenkai": {
        "path": FONT_DIR / "lxgw-wenkai" / "LXGWWenKai-Regular.ttf",
        "label": "霞鹜文楷 Regular",
        "license": "SIL OFL 1.1",
    },
    "lxgw_wenkai_medium": {
        "path": FONT_DIR / "lxgw-wenkai" / "LXGWWenKai-Medium.ttf",
        "label": "霞鹜文楷 Medium",
        "license": "SIL OFL 1.1",
    },
    "lxgw_wenkai_light": {
        "path": FONT_DIR / "lxgw-wenkai" / "LXGWWenKai-Light.ttf",
        "label": "霞鹜文楷 Light",
        "license": "SIL OFL 1.1",
    },
    "zhuque_fangsong": {
        "path": FONT_DIR / "zhuque-fangsong" / "extracted" / "ZhuqueFangsong-Regular.ttf",
        "label": "朱雀仿宋 Regular",
        "license": "SIL OFL 1.1",
    },
}

LATIN_FONTS = {
    "cinzel": {
        "path": FONT_DIR / "cinzel" / "Cinzel.ttf",
        "label": "Cinzel",
        "variable": True,
        "default_weight": 500,
        "note": "Roman inscriptional capitals; widest horizontal tension, epic film feel",
    },
    "cormorant": {
        "path": FONT_DIR / "cormorantgaramond" / "CormorantGaramond.ttf",
        "label": "Cormorant Garamond",
        "variable": True,
        "default_weight": 600,
        "note": "High-contrast classical serif; lighter, more literary. Avoid 300 on dark backgrounds",
    },
    "marcellus": {
        "path": FONT_DIR / "marcellus" / "Marcellus-Regular.ttf",
        "label": "Marcellus",
        "variable": False,
        "default_weight": 400,
        "note": "Minimal flared serif; closest in temperament to the rounded kaishu title",
    },
    "playfair": {
        "path": FONT_DIR / "playfairdisplay" / "PlayfairDisplay.ttf",
        "label": "Playfair Display",
        "variable": True,
        "default_weight": 500,
        "note": "Strong thick/thin contrast; stays legible at small mobile playback sizes",
    },
}

BG = (13, 19, 31)
GRAD_TOP = (247, 241, 227)
GRAD_BOTTOM = (216, 195, 158)
GLOW = (216, 195, 158)
SUB_COLOR = (200, 176, 133)      # champagne gold, echoing the title gradient
RULE_COLOR = (200, 176, 133)


def _latin_font(key: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    spec = LATIN_FONTS[key]
    font = _font(spec["path"], size)
    if spec["variable"]:
        w = weight or spec["default_weight"]
        try:
            font.set_variation_by_axes([w])
        except Exception:
            pass  # static fallback keeps rendering rather than failing the whole card
    return font


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"font missing: {path} (run the font fetch step)")
    return ImageFont.truetype(str(path), size)


def _tracked_width(draw, text: str, font, tracking_px: float) -> float:
    if not text:
        return 0.0
    return sum(draw.textlength(c, font=font) for c in text) + tracking_px * (len(text) - 1)


def _draw_tracked(mask_draw, xy, text: str, font, tracking_px: float, fill=255) -> None:
    x, y = xy
    for ch in text:
        mask_draw.text((x, y), ch, font=font, fill=fill)
        x += draw_advance(font, ch) + tracking_px


def draw_advance(font, ch: str) -> float:
    return font.getlength(ch)


def _gradient_band(size, top_y: int, bottom_y: int) -> Image.Image:
    """Vertical warm-gold gradient spanning the glyph box, clamped outside it."""
    w, h = size
    band = Image.new("RGB", (w, h), GRAD_BOTTOM)
    px = band.load()
    span = max(1, bottom_y - top_y)
    for y in range(h):
        t = min(1.0, max(0.0, (y - top_y) / span))
        r = round(GRAD_TOP[0] + (GRAD_BOTTOM[0] - GRAD_TOP[0]) * t)
        g = round(GRAD_TOP[1] + (GRAD_BOTTOM[1] - GRAD_TOP[1]) * t)
        b = round(GRAD_TOP[2] + (GRAD_BOTTOM[2] - GRAD_TOP[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return band


def render_title_card(
    out_path: Path,
    *,
    title: str = "云上天宫",
    subtitle: str = "CLOUD PALACE",
    font_key: str = "lxgw_wenkai_medium",
    latin_key: str = "cinzel",
    latin_weight: int | None = None,
    width: int = 1664,
    height: int = 960,
    title_size: int = 150,
    tracking_em: float = 0.34,
    subtitle_tracking_em: float = 0.30,
    subtitle_scale: float = 0.29,
    glow_strength: float = 0.22,
    gradient: bool = True,
    fade_rule: bool = True,
    label: str | None = None,
) -> Path:
    spec = FONTS[font_key]
    title_font = _font(spec["path"], title_size)
    sub_size = max(18, int(title_size * subtitle_scale))
    sub_font = _latin_font(latin_key, sub_size, latin_weight)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Horizon glow, ramping up downward from zero so there is no seam at its top edge.
    glow_h = int(height * 0.23)
    for i in range(glow_h):
        a = int(30 * (i / glow_h) ** 1.6)
        draw.line([(0, height - glow_h + i), (width, height - glow_h + i)],
                  fill=(BG[0] + a, BG[1] + a, BG[2] + a))

    tracking = title_size * tracking_em
    title_w = _tracked_width(draw, title, title_font, tracking)
    title_x = (width - title_w) / 2
    title_y = height / 2 - title_size * 1.15

    mask = Image.new("L", (width, height), 0)
    _draw_tracked(ImageDraw.Draw(mask), (title_x, title_y), title, title_font, tracking)

    bbox = mask.getbbox() or (0, int(title_y), width, int(title_y + title_size))

    if glow_strength > 0:
        bloom = mask.filter(ImageFilter.GaussianBlur(radius=title_size * 0.18))
        bloom = bloom.point(lambda v: int(v * glow_strength))
        glow_layer = Image.new("RGB", (width, height), GLOW)
        img = Image.composite(glow_layer, img, bloom)

    fill_layer = _gradient_band((width, height), bbox[1], bbox[3]) if gradient \
        else Image.new("RGB", (width, height), GRAD_TOP)
    img = Image.composite(fill_layer, img, mask)

    draw = ImageDraw.Draw(img)
    sub_tracking = sub_size * subtitle_tracking_em
    sub_w = _tracked_width(draw, subtitle, sub_font, sub_tracking)
    sub_y = title_y + title_size * 1.42
    x = (width - sub_w) / 2
    for ch in subtitle:
        draw.text((x, sub_y), ch, font=sub_font, fill=SUB_COLOR)
        x += draw_advance(sub_font, ch) + sub_tracking

    rule_y = int(sub_y + sub_size * 1.9)
    rule_w = 240
    if fade_rule:
        # Two-ended fade so the rule dissolves into the background instead of being
        # cut off square, matching the soft bloom around the glyphs.
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        x0 = int(width / 2 - rule_w / 2)
        for i in range(rule_w):
            t = i / (rule_w - 1)
            alpha = int(255 * (1 - abs(2 * t - 1)) ** 0.8)
            od.point((x0 + i, rule_y), fill=(*RULE_COLOR, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        # alpha_composite returns a NEW image; the old Draw handle points at the
        # discarded one, so anything drawn after this must use a fresh handle.
        draw = ImageDraw.Draw(img)
    else:
        draw.line([(width / 2 - rule_w / 2, rule_y), (width / 2 + rule_w / 2, rule_y)],
                  fill=RULE_COLOR, width=1)

    if label:
        lab_font = _font(FONTS["lxgw_wenkai"]["path"], 26)
        draw.text((28, 24), label, font=lab_font, fill=(150, 162, 180))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def render_preview(out_path: Path, **kwargs) -> Path:
    """One board comparing every candidate font under identical typography."""
    keys = list(FONTS)
    card_w, card_h = 832, 480
    cols = 2
    rows = (len(keys) + cols - 1) // cols
    pad, banner = 16, 70
    board = Image.new("RGB", (cols * card_w + pad * (cols + 1),
                              banner + rows * card_h + pad * (rows + 1)), (18, 20, 24))
    d = ImageDraw.Draw(board)
    d.text((pad + 6, 18), "片头字体对比 · 云上天宫", font=_font(FONTS["lxgw_wenkai"]["path"], 30),
           fill=(240, 240, 240))
    d.text((pad + 6, 52), "统一字距 0.30em · 暖金渐变填充 · 柔光晕 · Cinzel 英文副标题",
           font=_font(FONTS["lxgw_wenkai"]["path"], 18), fill=(150, 162, 180))

    for i, key in enumerate(keys):
        r, c = divmod(i, cols)
        tmp = out_path.parent / f"_cmp_{key}.png"
        render_title_card(tmp, font_key=key, width=card_w, height=card_h,
                          title_size=76, label=FONTS[key]["label"], **kwargs)
        board.paste(Image.open(tmp), (pad + c * (card_w + pad), banner + pad + r * (card_h + pad)))
        tmp.unlink()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_path, quality=94)
    return out_path


LATIN_CANDIDATES = [
    ("cinzel", 400, "Cinzel 400（原基线）"),
    ("cinzel", 500, "Cinzel 500（推荐·史诗）"),
    ("cormorant", 600, "Cormorant Garamond 600（书卷仙气）"),
    ("marcellus", 400, "Marcellus 400（新中式温润）"),
    ("playfair", 500, "Playfair Display 500（小屏锐利）"),
]


def render_latin_preview(out_path: Path, **kwargs) -> Path:
    """Same CJK title, five Latin subtitle treatments, identical everything else."""
    card_w, card_h = 832, 480
    cols = 2
    rows = (len(LATIN_CANDIDATES) + cols - 1) // cols
    pad, banner = 16, 70
    board = Image.new("RGB", (cols * card_w + pad * (cols + 1),
                              banner + rows * card_h + pad * (rows + 1)), (18, 20, 24))
    d = ImageDraw.Draw(board)
    lab = _font(FONTS["lxgw_wenkai"]["path"], 30)
    d.text((pad + 6, 18), "英文副标题字体对比 · CLOUD PALACE", font=lab, fill=(240, 240, 240))
    d.text((pad + 6, 52), "中文固定霞鹜文楷 Medium · 香槟金 #C8B085 · 副标题放大 · 横线两端渐隐",
           font=_font(FONTS["lxgw_wenkai"]["path"], 18), fill=(150, 162, 180))

    for i, (key, weight, label) in enumerate(LATIN_CANDIDATES):
        r, c = divmod(i, cols)
        tmp = out_path.parent / f"_latin_{key}_{weight}.png"
        render_title_card(tmp, width=card_w, height=card_h, title_size=76,
                          latin_key=key, latin_weight=weight, label=label, **kwargs)
        board.paste(Image.open(tmp), (pad + c * (card_w + pad), banner + pad + r * (card_h + pad)))
        tmp.unlink()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_path, quality=94)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Render a cinematic title card with vetted OFL fonts")
    ap.add_argument("--font", choices=list(FONTS), default="lxgw_wenkai_medium")
    ap.add_argument("--latin", choices=list(LATIN_FONTS), default="cinzel")
    ap.add_argument("--latin-weight", type=int, default=None)
    ap.add_argument("--title", default="云上天宫")
    ap.add_argument("--subtitle", default="CLOUD PALACE")
    ap.add_argument("--width", type=int, default=1664)
    ap.add_argument("--height", type=int, default=960)
    ap.add_argument("--size", type=int, default=150)
    ap.add_argument("--tracking", type=float, default=0.34)
    ap.add_argument("--glow", type=float, default=0.22)
    ap.add_argument("--flat", action="store_true", help="Use flat fill instead of the gold gradient")
    ap.add_argument("--preview", action="store_true", help="Comparison board of the CJK title fonts")
    ap.add_argument("--latin-preview", action="store_true", help="Comparison board of the Latin subtitle fonts")
    ap.add_argument("--hard-rule", action="store_true", help="Use a solid rule instead of the faded one")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    common = dict(tracking_em=args.tracking, glow_strength=args.glow,
                  gradient=not args.flat, fade_rule=not args.hard_rule,
                  title=args.title, subtitle=args.subtitle)
    if args.latin_preview:
        render_latin_preview(out, **common)
    elif args.preview:
        render_preview(out, **common)
    else:
        render_title_card(out, font_key=args.font, latin_key=args.latin,
                          latin_weight=args.latin_weight, width=args.width,
                          height=args.height, title_size=args.size, **common)
    print(f"[TitleCard] {out}")


if __name__ == "__main__":
    main()