#!/usr/bin/env python3
"""
scripts/benchmark_typography_composition.py
Typography, Complex Layout & Educational Courseware Benchmark Suite.
Tests FLUX.3 Klein and Z-Image Turbo across 3 Course-Ready Layout Scenarios:
1. Technical Infographic: Clear English labels, pointers, cross-section layout
2. 16:9 Widescreen Composition: Subject at right 60%, strict 40% clean negative space at left for titles/subtitles
3. Minimalist Clean White Illustration: Educational vector-style diagram for course slides
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generator import run_generation
from scripts.postprocess import export_clean_raw, export_social_web
from scripts.benchmark_model_comparison import create_side_by_side_board

BENCHMARK_DIR = ROOT / "outputs" / "typography_benchmark"
RAW_DIR = BENCHMARK_DIR / "raw"
CLEAN_DIR = BENCHMARK_DIR / "clean_raw"
BOARDS_DIR = BENCHMARK_DIR / "comparison_boards"

TYPOGRAPHY_CASES = [
    {
        "id": "typo01_technical_infographic",
        "title": "Case 01 · Technical Infographic · Precise Labels & Text Rendering",
        "seed": 20265101,
        "width": 768,
        "height": 1360,
        "prompt": (
            "Crisp high-resolution engineering infographic diagram explaining an advanced aerospace turbine engine cutaway. "
            "Clean dark slate background with precise technical typography. "
            "Accurate English annotation callout labels with thin pointer lines clearly pointing to specific mechanical assemblies: "
            "'AIR INTAKE', 'COMPRESSOR STAGE', 'COMBUSTION CHAMBER', 'TURBINE BLADES', 'EXHAUST NOZZLE'. "
            "Sharp readable sans-serif typography, zero spelling mistakes, zero garbled letters, pristine scientific textbook publication standard."
        )
    },
    {
        "id": "typo02_16x9_negative_space",
        "title": "Case 02 · 16:9 Widescreen Video Layout · 40% Negative Space for Subtitles",
        "seed": 20265102,
        "width": 1360,
        "height": 768,  # True 16:9 widescreen for video courseware
        "prompt": (
            "Cinematic 16:9 widescreen educational video presentation background. "
            "Strict rule of thirds asymmetrical framing: "
            "A sleek futuristic autonomous delivery drone hovers quietly on the right 50% of the frame, showing crisp carbon fiber rotors and glowing amber sensors. "
            "The entire left 40% of the frame is completely empty, clean, smooth dark-blue gradient negative space with soft subtle bokeh, perfectly reserved for multi-line lecture title and subtitle text overlays. "
            "Zero clutter, zero random floating objects in the left negative space, pristine 4K video courseware graphic design quality."
        )
    },
    {
        "id": "typo03_minimalist_white_illustration",
        "title": "Case 03 · Minimalist White Concept Illustration · Educational Slide Asset",
        "seed": 20265103,
        "width": 1024,
        "height": 1024,
        "prompt": (
            "Minimalist modern technical line illustration of a neural network data pipeline flow. "
            "Pure seamless solid white background (#FFFFFF) with zero texture and zero gray artifacts. "
            "Clean precise geometric vector-style lines in deep cobalt blue and graphite grey. "
            "Showing clean nodes connected by directional data flow arrows into a central processor core. "
            "High-contrast, elegant simplicity, sophisticated editorial graphic design for academic slide presentation, zero AI noise."
        )
    }
]


def assemble_typography_3grid(image_paths: list[Path], title: str, subtitle: str, output_path: Path) -> Path:
    """Build showcase board for typography and layout cases."""
    images = [Image.open(p).convert("RGB") for p in image_paths[:3]]
    # Normalize to uniform preview tiles
    tile_w, tile_h = 600, 600
    resized = [img.resize((tile_w, tile_h), Image.Resampling.LANCZOS) for img in images]

    margin = 35
    gap = 25
    header_h = 150
    footer_h = 80

    canvas_w = margin * 2 + tile_w * 3 + gap * 2
    canvas_h = margin * 2 + header_h + tile_h + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (16, 18, 22))
    draw = ImageDraw.Draw(canvas)

    draw.text((margin + 10, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 75), subtitle, fill=(160, 165, 175))

    for i, img in enumerate(resized):
        pos_x = margin + i * (tile_w + gap)
        pos_y = margin + header_h
        canvas.paste(img, (pos_x, pos_y))

    foot_y = canvas_h - margin - footer_h + 30
    draw.text((margin + 10, foot_y), "Local Drama Studio · Typography & Courseware Layout Benchmark · Intel Arc A750", fill=(120, 125, 135))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Typography] 3-Panel board saved: {output_path}")
    return output_path


def run_typography_benchmark():
    print("=" * 75)
    print(" Typography, Composition & Courseware Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Evaluating English Text Rendering, 16:9 Left 40% Negative Space, and White Vector Slides")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    flux_outputs = []
    z_outputs = []

    for case in TYPOGRAPHY_CASES:
        cid = case["id"]
        prompt = case["prompt"]
        seed = case["seed"]
        title = case["title"]
        w = case["width"]
        h = case["height"]
        print(f"\n>>> Running Scenario: {title} ({w}x{h}) <<<")

        # 1. FLUX.3 Klein
        f_existing = list(RAW_DIR.glob(f"flux3_klein_{seed}_*.png"))
        if f_existing:
            f_raw = f_existing[0]
            print(f"  FLUX.3 already exists -> {f_raw.name}")
        else:
            print(f"  Generating: FLUX.3 Klein (16 steps, er_sde, CFG 1.0, {w}x{h})...")
            t0 = time.time()
            f_raw = run_generation(
                engine="flux3_klein",
                prompt=prompt,
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"steps": 16, "cfg": 1.0, "use_lora": False, "width": w, "height": h}
            )[0]
            print(f"  FLUX.3 done in {time.time() - t0:.2f}s -> {f_raw.name}")
        flux_outputs.append(f_raw)

        # 2. Z-Image Turbo
        z_existing = list(RAW_DIR.glob(f"z_image_turbo_{seed}_*.png"))
        if z_existing:
            z_raw = z_existing[0]
            print(f"  Z-Image already exists -> {z_raw.name}")
        else:
            print(f"  Generating: Z-Image Turbo (8 steps, euler, CFG 1.0, {w}x{h})...")
            t0 = time.time()
            z_raw = run_generation(
                engine="z_image_turbo",
                prompt=prompt,
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"steps": 8, "cfg": 1.0, "use_lora": False, "width": w, "height": h}
            )[0]
            print(f"  Z-Image done in {time.time() - t0:.2f}s -> {z_raw.name}")
        z_outputs.append(z_raw)

        # Generate SBS comparison board
        sbs_path = BOARDS_DIR / f"{cid}_sbs_comparison.jpg"
        create_side_by_side_board(
            img_left_path=f_raw,
            title_left=f"FLUX.3 Klein ({w}x{h})",
            subtitle_left="16 Steps | er_sde | Native Base",
            img_right_path=z_raw,
            title_right=f"Z-Image Turbo ({w}x{h})",
            subtitle_right="8 Steps | euler | Native DiT",
            main_title=f"Typography & Layout · {title}",
            output_path=sbs_path
        )

    # 3-Panel Showcases
    assemble_typography_3grid(
        image_paths=flux_outputs,
        title="FLUX.3 Klein · Typography & Courseware Layout Showcase",
        subtitle="Technical Infographic, 16:9 Left 40% Negative Space, and Minimalist Slide Vector Asset",
        output_path=BOARDS_DIR / "typography_flux3_klein_3panel.jpg"
    )

    assemble_typography_3grid(
        image_paths=z_outputs,
        title="Z-Image Turbo · Typography & Courseware Layout Showcase",
        subtitle="Technical Infographic, 16:9 Left 40% Negative Space, and Minimalist Slide Vector Asset",
        output_path=BOARDS_DIR / "typography_z_image_turbo_3panel.jpg"
    )

    print("\n[SUCCESS] Typography & Courseware Benchmark completed successfully!")


if __name__ == "__main__":
    run_typography_benchmark()
