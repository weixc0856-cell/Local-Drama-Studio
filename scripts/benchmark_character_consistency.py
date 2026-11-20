#!/usr/bin/env python3
"""
scripts/benchmark_character_consistency.py
Character Consistency & Narrative Storyboard Benchmark Suite.
Compares FLUX.3 Klein and Z-Image Turbo across a 4-Act Cinematic Sequence:
Character: "Lin" (22yo East Asian protagonist, collarbone wavy hair, subtle beauty mark beneath left eye)
Shots:
  Shot 01: Morning Cafe · Close-up Window Portrait
  Shot 02: Urban Street · Dynamic Profile Walking Shot
  Shot 03: Rainy Night · Mood Car Window Silhouette
  Shot 04: Art Gallery · Wide Narrative Full Shot
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generator import run_generation
from scripts.postprocess import export_clean_raw, export_social_web, extract_dominant_colors, build_four_grid_board
from scripts.benchmark_model_comparison import create_side_by_side_board

BENCHMARK_DIR = ROOT / "outputs" / "character_consistency_benchmark"
RAW_DIR = BENCHMARK_DIR / "raw"
CLEAN_DIR = BENCHMARK_DIR / "clean_raw"
BOARDS_DIR = BENCHMARK_DIR / "comparison_boards"

# Fixed fictional character specification
CHARACTER_BASE = (
    "the exact same 22-year-old East Asian woman named Lin, "
    "distinctive subtle tiny beauty mark beneath her left eye, "
    "natural soft feminine oval face with delicate straight nose and poised gentle eyes, "
    "shoulder-length dark espresso wavy lob hair with soft wispy curtain bangs, "
    "minimalist tiny silver wire huggie earrings, completely blemish-free translucent skin with realistic fine pores, "
    "natural understated elegance, zero heavy makeup, zero plastic doll look"
)

STORY_SHOTS = [
    {
        "id": "shot01_morning_cafe_closeup",
        "title": "Act I · Morning Cafe · Intimate Close-up",
        "seed": 20263101,
        "prompt": (
            f"Cinematic candid 35mm intimate close-up portrait of {CHARACTER_BASE}. "
            "Sitting by a sunlit wooden cafe table in early morning, holding a minimalist white ceramic coffee mug with both hands. "
            "Soft 45-degree morning sunlight filtering through sheer curtains, gentle natural micro-smile looking directly at the camera, "
            "subtle beauty mark under left eye clearly visible, wearing an oatmeal-beige oversized ribbed cashmere knit sweater. "
            "Shallow depth of field with warm bokeh cafe interior, 50mm f/1.4 prime lens documentary realism."
        )
    },
    {
        "id": "shot02_urban_street_profile",
        "title": "Act II · Urban Street · Dynamic Walking Profile",
        "seed": 20263102,
        "prompt": (
            f"Cinematic 35mm candid medium profile photograph of {CHARACTER_BASE}. "
            "Mid-stride crossing a tree-lined city crosswalk in crisp late autumn golden hour, graceful 45-degree three-quarter profile turning back toward camera. "
            "Autum wind gently lifting loose strands of her shoulder-length dark espresso hair, tiny beauty mark beneath left eye distinct in warm side-light. "
            "Wearing a tailored charcoal-grey double-breasted wool trench coat over a cream mock-neck top, holding a black leather tote bag. "
            "Dappled golden sunlight through golden foliage, motion blur in distant urban traffic, Leica M11 50mm Summilux aesthetic."
        )
    },
    {
        "id": "shot03_rainy_night_mood",
        "title": "Act III · Rainy Night · Melancholic Window Reflection",
        "seed": 20263103,
        "prompt": (
            f"Atmospheric 35mm cinematic photograph of {CHARACTER_BASE}. "
            "Sitting inside a quiet late-night city tram or car, head resting thoughtfully against the rain-streaked windowpane. "
            "Cool blue interior vehicle lighting blended with warm amber and magenta neon city lights refracted through raindrops on the glass. "
            "Pensive quiet gaze looking out at the rainy metropolis, distinctive beauty mark beneath her left eye catching soft neon specular reflection. "
            "Wearing a structured black turtleneck sweater, rich cinematic grain, Wong Kar-wai moody color palette, 35mm f/1.2 lens."
        )
    },
    {
        "id": "shot04_art_gallery_wide",
        "title": "Act IV · Art Gallery · Minimalist Narrative Full Shot",
        "seed": 20263104,
        "prompt": (
            f"Editorial 35mm narrative full-body photograph of {CHARACTER_BASE}. "
            "Standing in a high-ceilinged contemporary art gallery between stark white concrete exhibition walls and a monumental minimalist sculpture. "
            "Body poised in elegant walking posture, pausing and glancing back over her shoulder with an intelligent poised expression. "
            "Her distinctive facial features, shoulder-length dark espresso lob hair, and subtle beauty mark under left eye clearly recognizable. "
            "Wearing tailored wide-leg black trousers and a minimalist slate-blue silk shirt, clean architectural lines and diffused gallery skylight, 35mm documentary photography."
        )
    }
]


def assemble_storyboard_4grid(image_paths: list[Path], title: str, subtitle: str, output_path: Path) -> Path:
    """Build a cinematic horizontal 4-panel storyboard board."""
    images = [Image.open(p).convert("RGB") for p in image_paths[:4]]
    panel_w, panel_h = 512, 910
    resized = [img.resize((panel_w, panel_h), Image.Resampling.LANCZOS) for img in images]

    margin = 35
    gap = 20
    header_h = 140
    footer_h = 80

    canvas_w = margin * 2 + panel_w * 4 + gap * 3
    canvas_h = margin * 2 + header_h + panel_h + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (14, 16, 20))
    draw = ImageDraw.Draw(canvas)

    draw.text((margin + 10, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 70), subtitle, fill=(160, 165, 175))

    for i, img in enumerate(resized):
        pos_x = margin + i * (panel_w + gap)
        pos_y = margin + header_h
        canvas.paste(img, (pos_x, pos_y))

    foot_y = canvas_h - margin - footer_h + 30
    draw.text((margin + 10, foot_y), "Local Drama Studio · Character Consistency Benchmark · 4-Act Narrative Sequence", fill=(120, 125, 135))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Consistency] Storyboard saved: {output_path}")
    return output_path


def run_consistency_benchmark():
    print("=" * 75)
    print(" Character Consistency Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Testing Character 'Lin' across 4 Sequential Cinematic Acts")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    flux_outputs = []
    z_outputs = []

    for shot in STORY_SHOTS:
        sid = shot["id"]
        prompt = shot["prompt"]
        seed = shot["seed"]
        title = shot["title"]
        print(f"\n>>> Running Shot: {title} <<<")

        # 1. FLUX.3 Klein
        f_existing = list(RAW_DIR.glob(f"flux3_klein_{seed}_*.png"))
        if f_existing:
            f_raw = f_existing[0]
            print(f"  FLUX.3 already exists -> {f_raw.name}")
        else:
            print("  Generating: FLUX.3 Klein (16 steps, er_sde, CFG 1.0, girlslikeflux 0.70)...")
            t0 = time.time()
            f_raw = run_generation(
                engine="flux3_klein",
                prompt=f"girlslikeflux_lyf5, {prompt}",
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"lora_name": "girlslikeflux_lyf5.safetensors", "lora_strength": 0.70, "steps": 16, "cfg": 1.0}
            )[0]
            print(f"  FLUX.3 done in {time.time() - t0:.2f}s -> {f_raw.name}")
        flux_outputs.append(f_raw)

        # 2. Z-Image Turbo
        z_existing = list(RAW_DIR.glob(f"z_image_turbo_{seed}_*.png"))
        if z_existing:
            z_raw = z_existing[0]
            print(f"  Z-Image already exists -> {z_raw.name}")
        else:
            print("  Generating: Z-Image Turbo (8 steps, euler, CFG 1.0, Native DiT)...")
            t0 = time.time()
            z_raw = run_generation(
                engine="z_image_turbo",
                prompt=prompt,
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"steps": 8, "cfg": 1.0, "use_lora": False}
            )[0]
            print(f"  Z-Image done in {time.time() - t0:.2f}s -> {z_raw.name}")
        z_outputs.append(z_raw)

        # Generate per-shot Side-by-Side comparison board
        sbs_path = BOARDS_DIR / f"{sid}_sbs_comparison.jpg"
        create_side_by_side_board(
            img_left_path=f_raw,
            title_left="FLUX.3 Klein (+0.70 LoRA)",
            subtitle_left="16 Steps | er_sde | girlslikeflux_lyf5",
            img_right_path=z_raw,
            title_right="Z-Image Turbo (Native DiT)",
            subtitle_right="8 Steps | euler | Zero LoRA Native",
            main_title=f"Character Consistency · {title}",
            output_path=sbs_path
        )

    # Generate complete 4-panel storyboard for each engine
    assemble_storyboard_4grid(
        image_paths=flux_outputs,
        title="FLUX.3 Klein · 4-Act Character Continuity Storyboard",
        subtitle="Evaluating cross-shot consistency for 'Lin' with girlslikeflux_lyf5 LoRA across 4 narrative scenes",
        output_path=BOARDS_DIR / "character_consistency_flux3_klein_4panel.jpg"
    )

    assemble_storyboard_4grid(
        image_paths=z_outputs,
        title="Z-Image Turbo · 4-Act Character Continuity Storyboard",
        subtitle="Evaluating cross-shot consistency for 'Lin' with Native 8-Step DiT across 4 narrative scenes",
        output_path=BOARDS_DIR / "character_consistency_z_image_turbo_4panel.jpg"
    )

    print("\n[SUCCESS] Character Consistency Benchmark completed successfully!")


if __name__ == "__main__":
    run_consistency_benchmark()
