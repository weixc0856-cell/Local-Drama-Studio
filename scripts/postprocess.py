#!/usr/bin/env python3
"""
scripts/postprocess.py
Public Post-Processing Module for Local-Drama-Studio Image Pipelines.
1. Metadata stripping (sanitizes generation prompts and local machine paths)
2. Patreon Clean Raw export (preserves maximum dynamic range & resolution)
3. Social Web export (optimized for X / Xiaohongshu with high compression fidelity)
4. Multi-grid showcase collage with bilingual typography & color swatches
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent


def strip_metadata(img: Image.Image) -> Image.Image:
    """Create a clean copy of image without EXIF or ComfyUI metadata."""
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    return clean


def export_clean_raw(img_path: Path, output_dir: Path) -> Path:
    """Export clean raw image for Patreon / archival."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{img_path.stem}_clean.png"
    with Image.open(img_path) as img:
        clean = strip_metadata(img)
        clean.save(out_path, format="PNG", optimize=True)
    return out_path


def export_social_web(img_path: Path, output_dir: Path, max_dim: int = 2048, quality: int = 88) -> Path:
    """Export optimized web version for X / Xiaohongshu."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{img_path.stem}_web.jpg"
    with Image.open(img_path) as img:
        img_rgb = img.convert("RGB")
        w, h = img_rgb.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            img_rgb = img_rgb.resize(new_size, Image.Resampling.LANCZOS)
        clean = strip_metadata(img_rgb)
        clean.save(out_path, format="JPEG", quality=quality, optimize=True)
    return out_path


def extract_dominant_colors(img: Image.Image, count: int = 5) -> list[tuple[int, int, int]]:
    """Extract dominant palette colors using thumbnail quantization."""
    thumb = img.copy().resize((100, 100))
    result = thumb.convert("P", palette=Image.Palette.ADAPTIVE, colors=count)
    palette = result.getpalette()[:count * 3]
    colors = []
    for i in range(0, len(palette), 3):
        colors.append((palette[i], palette[i + 1], palette[i + 2]))
    return colors


def build_four_grid_board(
    image_paths: list[Path],
    title: str = "GLOBAL CANDID REALISM SHOWCASE",
    subtitle: str = "FLUX.3 Klein & Z-Image Turbo Dual-Engine Remaster",
    output_path: Path = None
) -> Path:
    """Generate professional 4-grid board with color swatches and typography."""
    if len(image_paths) < 4:
        raise ValueError(f"4-Grid requires at least 4 images, got {len(image_paths)}")

    output_path = output_path or (ROOT / "outputs" / "social_web" / "showcase_4grid.jpg")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    images = [Image.open(p).convert("RGB") for p in image_paths[:4]]
    
    # Target grid tile size
    tile_w, tile_h = 768, 1360
    resized = [img.resize((tile_w, tile_h), Image.Resampling.LANCZOS) for img in images]

    # Canvas dimensions
    margin = 40
    gap = 24
    header_h = 160
    footer_h = 100
    
    canvas_w = margin * 2 + tile_w * 2 + gap
    canvas_h = margin * 2 + header_h + tile_h * 2 + gap + footer_h
    
    # Background: Elegant deep slate
    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 20, 24))
    draw = ImageDraw.Draw(canvas)

    # Paste 4 images
    positions = [
        (margin, margin + header_h),
        (margin + tile_w + gap, margin + header_h),
        (margin, margin + header_h + tile_h + gap),
        (margin + tile_w + gap, margin + header_h + tile_h + gap),
    ]

    for img, pos in zip(resized, positions):
        canvas.paste(img, pos)

    # Title & Typography
    draw.text((margin, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin, margin + 70), subtitle, fill=(160, 165, 175))

    # Color Palette extraction from the first image
    swatches = extract_dominant_colors(images[0], count=5)
    swatch_y = canvas_h - margin - footer_h + 30
    swatch_x = margin
    for rgb in swatches:
        draw.rectangle([swatch_x, swatch_y, swatch_x + 36, swatch_y + 36], fill=rgb)
        swatch_x += 48

    draw.text((swatch_x + 20, swatch_y + 10), "Color Grade Palette | 35mm Candid Documentary Tone", fill=(130, 135, 145))

    canvas.save(output_path, format="JPEG", quality=92, optimize=True)
    print(f"[PostProcess] 4-Grid showcase saved: {output_path}")
    return output_path


def process_pipeline_outputs(raw_dir: Path, clean_dir: Path, web_dir: Path):
    """Batch process all generated images in raw directory."""
    raw_images = list(raw_dir.glob("*.png")) + list(raw_dir.glob("*.jpg"))
    if not raw_images:
        print(f"[PostProcess] No images found in {raw_dir}")
        return

    print(f"\n[PostProcess] Processing {len(raw_images)} images...")
    clean_paths = []
    web_paths = []
    for p in raw_images:
        cp = export_clean_raw(p, clean_dir)
        wp = export_social_web(p, web_dir)
        clean_paths.append(cp)
        web_paths.append(wp)
        print(f"  Processed: {p.name} -> Raw Clean & Web JPG")

    if len(web_paths) >= 4:
        grid_out = web_dir / "latest_showcase_4grid.jpg"
        build_four_grid_board(web_paths[:4], output_path=grid_out)


def main():
    parser = argparse.ArgumentParser(description="Image Post-Processing Suite")
    parser.add_argument("--raw-dir", type=str, default=str(ROOT / "outputs" / "raw"), help="Raw inputs")
    parser.add_argument("--clean-dir", type=str, default=str(ROOT / "outputs" / "raw_4k"), help="Patreon clean outputs")
    parser.add_argument("--web-dir", type=str, default=str(ROOT / "outputs" / "social_web"), help="Social web outputs")
    parser.add_argument("--build-grid", action="store_true", help="Build 4-grid board from first 4 web images")

    args = parser.parse_args()
    process_pipeline_outputs(Path(args.raw_dir), Path(args.clean_dir), Path(args.web_dir))


if __name__ == "__main__":
    main()
