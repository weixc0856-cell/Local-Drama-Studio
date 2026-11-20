#!/usr/bin/env python3
"""
scripts/benchmark_model_comparison.py
Systematic Model Benchmark & A/B Comparison Suite for Local-Drama-Studio.
Compares FLUX.3 Klein and Z-Image Turbo under identical configurations:
1. Zero-LoRA Native Baseline Comparison (Raw foundation capabilities)
2. Tailored-LoRA Production Comparison (Model-specific optimization)
Generates side-by-side comparison boards with typography and color swatches.
"""

import os
import sys
import time
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generator import run_generation
from scripts.postprocess import export_clean_raw, export_social_web, extract_dominant_colors, build_four_grid_board

BENCHMARK_DIR = ROOT / "outputs" / "model_benchmark"
RAW_DIR = BENCHMARK_DIR / "raw"
CLEAN_DIR = BENCHMARK_DIR / "clean_raw"
BOARDS_DIR = BENCHMARK_DIR / "comparison_boards"

# Benchmark Prompts: Day 01 Global Candid Realism Quartet
BENCHMARK_CASES = [
    {
        "id": "case01_shanghai_candid",
        "title": "Day 01 · 01: Shanghai Julu Road · Golden Autumn Candid",
        "description": "Tests East Asian facial bone structure, skin micro-pores, and golden hour dappled light.",
        "seed": 20261101,
        "prompt": (
            "Award-winning candid 35mm environmental street photograph of a serene 21-year-old Chinese woman walking down Shanghai Julu Road in late golden autumn. "
            "Master environmental walking framing: Walking along a sidewalk covered in golden plane tree leaves, turning her body gently back over her shoulder at a 35-degree angle. "
            "Holding a takeaway paper cup of warm latte naturally with both hands. "
            "Pristine East Asian bone structure, quiet soulful dark almond eyes with gentle warmth, naturally blooming rose lips in soft calm breathing repose, authentic translucent porcelain skin with realistic fine micro-pores and zero fake makeup. "
            "Silky dark raven hair drifting gently across her cheek in the breeze, wearing an oversized cream-beige soft cashmere knit sweater. "
            "Historic brick villa facades and warm golden autumn afternoon sunlight filtering through tree canopy with creamy bokeh, cinematic realism documentary."
        ),
    },
    {
        "id": "case02_paris_leftbank",
        "title": "Day 01 · 02: Paris Saint-Germain · French Sidewalk Bistro",
        "description": "Tests European bone structure, golden hour rim light, and relaxed candid posture.",
        "seed": 20261102,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 21-year-old French woman sitting at an outdoor Parisian sidewalk bistro in Saint-Germain. "
            "Master candid cafe framing: Leaning sideways at a 45-degree angle against a small round green marble bistro table, chin resting casually on one palm, fingers softly curled. "
            "Captivating large sparkling grey-green doe eyes gazing with warm relaxed curiosity, a subtle tender blooming smile with relaxed lips, smooth blemish-free porcelain skin with authentic micro-pores and zero heavy freckles. "
            "Tousled wavy honey-blonde hair catching warm afternoon rim light, wearing an unbuttoned vintage light-blue soft denim shirt with sleeves rolled to the elbows. "
            "Woven rattan green bistro chairs and historic Haussmannian Parisian stone facade in golden afternoon sunlight, Contax T2 35mm f/2.8 lens, legendary French cinema documentary."
        ),
    },
    {
        "id": "case03_kamakura_transparency",
        "title": "Day 01 · 03: Kamakura Coastal Road · Sea Breeze Transparency",
        "description": "Tests Japanese delicate transparency, air bangs, ocean mist, and youthful cure smile.",
        "seed": 20261103,
        "prompt": (
            "Authentic candid Japanese 35mm film photograph of an extraordinarily adorable 20-year-old Japanese young beauty walking along the coastal road in Kamakura. "
            "Master candid walking composition: Strolling beside the green coastal road barrier overlooking the sparkling blue ocean, turning back over her shoulder at a three-quarter angle. "
            "Single cream canvas tote bag slung over one shoulder, one hand holding the tote strap, relaxed breezy posture. "
            "Dainty delicate feminine features, soft smooth jawline, large clear dark doe eyes with crystal-clear catchlights, naturally plump glossy peach lips slightly parted in soft breathing repose, pristine translucent fair skin with natural soft flush on cheeks and realistic fine skin pores. "
            "Dark silky bob hair with wispy air bangs dancing in the Pacific ocean breeze, wearing a clean white linen short-sleeved collared shirt and high-waist navy blue pleated skirt. "
            "Sparkling azure Pacific sea waves and coastal railway crossing in warm afternoon summer sunlight, authentic Fujifilm Pro 400H colors, iconic Japanese youth film aesthetics."
        ),
    },
    {
        "id": "case04_seoul_hannam_chic",
        "title": "Day 01 · 04: Seoul Hannam-dong · Contemporary Heiress",
        "description": "Tests Korean clean jawline, porcelain glass skin, minimalist luxury, and urban twilight tones.",
        "seed": 20261104,
        "prompt": (
            "High-fashion candid 35mm editorial portrait of an extraordinarily beautiful 21-year-old Korean heiress descending the granite steps of a contemporary art museum in Hannam-dong, Seoul. "
            "Master architectural portrait framing: Descending minimalist grey granite museum steps, body turned at an elegant 35-degree three-quarter silhouette, rule of thirds diagonal line. "
            "Carrying a petite minimalist black leather handbag in one hand, slender waist accentuated by tailored fit. "
            "Impeccably proportioned soft feminine oval face, full youthful cheeks without harsh angles, delicate straight nose, captivating dark almond eyes with poised intelligent warmth, naturally plump dewy petal-pink lips in soft breathing repose, luminous translucent glass skin with realistic micro-pores under soft daylight. "
            "Glossy dark espresso hair cascading smoothly down her back, wearing an oversized tailored charcoal grey wool blazer over a black silk camisole. "
            "Modern exposed concrete architecture, bamboo grove and distant city skyline in warm golden hour light, Leica M11 50mm Summilux lens, Vogue Korea luxury realism."
        ),
    }
]


def create_side_by_side_board(
    img_left_path: Path,
    title_left: str,
    subtitle_left: str,
    img_right_path: Path,
    title_right: str,
    subtitle_right: str,
    main_title: str,
    output_path: Path
) -> Path:
    """Build a professional side-by-side comparison board with metadata."""
    img_left = Image.open(img_left_path).convert("RGB")
    img_right = Image.open(img_right_path).convert("RGB")

    target_w, target_h = 768, 1360
    left_resized = img_left.resize((target_w, target_h), Image.Resampling.LANCZOS)
    right_resized = img_right.resize((target_w, target_h), Image.Resampling.LANCZOS)

    margin = 40
    gap = 30
    header_h = 160
    footer_h = 120

    canvas_w = margin * 2 + target_w * 2 + gap
    canvas_h = margin * 2 + header_h + target_h + footer_h

    # Slate gray minimalist background
    canvas = Image.new("RGB", (canvas_w, canvas_h), (20, 22, 26))
    draw = ImageDraw.Draw(canvas)

    # Header
    draw.text((margin, margin + 20), main_title, fill=(245, 245, 248))
    draw.text((margin, margin + 70), "Intel Arc A750 (8GB VRAM) Rigorous Empirical Benchmark", fill=(150, 155, 165))

    # Place Images
    pos_left = (margin, margin + header_h)
    pos_right = (margin + target_w + gap, margin + header_h)
    canvas.paste(left_resized, pos_left)
    canvas.paste(right_resized, pos_right)

    # Image Sub-labels
    draw.text((margin, margin + header_h - 45), title_left, fill=(220, 225, 235))
    draw.text((margin, margin + header_h - 22), subtitle_left, fill=(130, 140, 150))

    draw.text((margin + target_w + gap, margin + header_h - 45), title_right, fill=(220, 225, 235))
    draw.text((margin + target_w + gap, margin + header_h - 22), subtitle_right, fill=(130, 140, 150))

    # Footer Swatches from both images
    swatches_left = extract_dominant_colors(left_resized, count=4)
    swatches_right = extract_dominant_colors(right_resized, count=4)

    swatch_y = canvas_h - margin - footer_h + 35
    sx = margin
    for rgb in swatches_left:
        draw.rectangle([sx, swatch_y, sx + 32, swatch_y + 32], fill=rgb)
        sx += 40

    draw.text((sx + 10, swatch_y + 8), f"Palette: {title_left.split(':')[0]}", fill=(130, 135, 145))

    sx = margin + target_w + gap
    for rgb in swatches_right:
        draw.rectangle([sx, swatch_y, sx + 32, swatch_y + 32], fill=rgb)
        sx += 40

    draw.text((sx + 10, swatch_y + 8), f"Palette: {title_right.split(':')[0]}", fill=(130, 135, 145))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=92, optimize=True)
    print(f"[Benchmark] Comparison board generated: {output_path}")
    return output_path


def run_benchmark_suite(target_case_id: str = None):
    """Run full matrix: Zero-LoRA vs Zero-LoRA, then LoRA vs LoRA."""
    print("=" * 75)
    print(" Systematic Multi-Model Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Architecture: Arc A750 8GB VRAM Isolation + Dynamic API Decoupling")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    cases = [c for c in BENCHMARK_CASES if target_case_id is None or c["id"] == target_case_id]

    for case in cases:
        cid = case["id"]
        prompt = case["prompt"]
        seed = case["seed"]
        print(f"\n>>>>>>>>>>>>>>> Running Benchmark Case: {case['title']} <<<<<<<<<<<<<<<")

        # ---------------------------------------------------------
        # Phase 1: Zero-LoRA Native Baseline Comparison
        # ---------------------------------------------------------
        print("\n--- [Phase 1: Zero-LoRA Native Baseline] ---")
        
        # 1A. FLUX.3 Klein (Zero-LoRA)
        print("  Generating: FLUX.3 Klein [Zero-LoRA, 16 steps, CFG 1.0]...")
        t0 = time.time()
        flux_raw = run_generation(
            engine="flux3_klein",
            prompt=prompt,
            seed=seed,
            batch_count=1,
            output_dir=RAW_DIR,
            overrides={"lora_name": "", "lora_strength": 0.0, "steps": 16, "cfg": 1.0}
        )[0]
        flux_latency = time.time() - t0

        # 1B. Z-Image Turbo (Zero-LoRA)
        print("  Generating: Z-Image Turbo [Zero-LoRA, 8 steps, CFG 1.0]...")
        t0 = time.time()
        z_raw = run_generation(
            engine="z_image_turbo",
            prompt=prompt,
            seed=seed,
            batch_count=1,
            output_dir=RAW_DIR,
            overrides={"lora_name": "", "lora_strength": 0.0, "steps": 8, "cfg": 1.0}
        )[0]
        z_latency = time.time() - t0

        board_zero = BOARDS_DIR / f"{cid}_zero_lora_comparison.jpg"
        create_side_by_side_board(
            img_left_path=flux_raw,
            title_left="FLUX.3 Klein (Native Zero-LoRA)",
            subtitle_left=f"16 Steps | CFG 1.0 | er_sde | Latency: {flux_latency:.1f}s",
            img_right_path=z_raw,
            title_right="Z-Image Turbo (Native Zero-LoRA)",
            subtitle_right=f"8 Steps | CFG 1.0 | euler | Latency: {z_latency:.1f}s",
            main_title=f"{case['title']} · ZERO-LORA BASELINE COMPARISON",
            output_path=board_zero
        )

        # ---------------------------------------------------------
        # Phase 2: Tailored-LoRA Optimization Comparison
        # ---------------------------------------------------------
        print("\n--- [Phase 2: Tailored-LoRA Optimization Comparison] ---")
        
        # 2A. FLUX.3 Klein (With Realism LoRA)
        print("  Generating: FLUX.3 Klein + Realism LoRA (0.35)...")
        t0 = time.time()
        flux_lora_raw = run_generation(
            engine="flux3_klein",
            prompt=prompt,
            seed=seed,
            batch_count=1,
            output_dir=RAW_DIR,
            overrides={"lora_name": "flux_realism_xlabs.safetensors", "lora_strength": 0.35, "steps": 16, "cfg": 1.0}
        )[0]
        flux_lora_latency = time.time() - t0

        # 2B. Z-Image Turbo (Native / Dedicated LoRA)
        # Note: Z-Image achieves peak performance on pure native DiT for candid realism
        print("  Generating: Z-Image Turbo (Native High-Fidelity 8-Step Mode)...")
        t0 = time.time()
        z_opt_raw = run_generation(
            engine="z_image_turbo",
            prompt=prompt,
            seed=seed,
            batch_count=1,
            output_dir=RAW_DIR,
            overrides={"lora_name": "", "lora_strength": 0.0, "steps": 8, "cfg": 1.0}
        )[0]
        z_opt_latency = time.time() - t0

        board_tailored = BOARDS_DIR / f"{cid}_tailored_optimization_comparison.jpg"
        create_side_by_side_board(
            img_left_path=flux_lora_raw,
            title_left="FLUX.3 Klein + Realism LoRA (0.35)",
            subtitle_left=f"16 Steps | CFG 1.0 | Realism XLabs | Latency: {flux_lora_latency:.1f}s",
            img_right_path=z_opt_raw,
            title_right="Z-Image Turbo (Native High-Fidelity)",
            subtitle_right=f"8 Steps | CFG 1.0 | Qwen3-4B Spatial Logic | Latency: {z_opt_latency:.1f}s",
            main_title=f"{case['title']} · TAILORED-LORA & OPTIMIZATION COMPARISON",
            output_path=board_tailored
        )

    # ---------------------------------------------------------
    # Phase 3: Build 4-Grid Showcase Boards for Both Models
    # ---------------------------------------------------------
    flux_tailored_imgs = list(sorted(RAW_DIR.glob("flux3_klein_*00002_.png")))
    z_tailored_imgs = list(sorted(RAW_DIR.glob("z_image_turbo_*00002_.png")))

    if len(flux_tailored_imgs) >= 4:
        grid_flux = BOARDS_DIR / "day01_flux3_klein_showcase_4grid.jpg"
        build_four_grid_board(
            flux_tailored_imgs[:4],
            title="GLOBAL CANDID REALISM · DAY 01 SHOWCASE",
            subtitle="FLUX.3 Klein + Realism LoRA (0.35) · 35mm Master Film Aesthetics",
            output_path=grid_flux
        )

    if len(z_tailored_imgs) >= 4:
        grid_z = BOARDS_DIR / "day01_z_image_turbo_showcase_4grid.jpg"
        build_four_grid_board(
            z_tailored_imgs[:4],
            title="GLOBAL CANDID REALISM · DAY 01 SHOWCASE",
            subtitle="Z-Image Turbo Native 6B DiT · Qwen3-4B Spatial Logic & Candid Realism",
            output_path=grid_z
        )

    print("\n" + "=" * 75)
    print(" Benchmark Suite Completed Successfully!")
    print(f" Boards Output Directory: {BOARDS_DIR}")
    print("=" * 75)


if __name__ == "__main__":
    case_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_benchmark_suite(case_arg)
