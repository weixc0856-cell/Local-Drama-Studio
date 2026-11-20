#!/usr/bin/env python3
"""
scripts/benchmark_runway_angels.py
Supermodel Runway Angels 6-Pack Benchmark & A/B Comparison Suite.
Compares FLUX.3 Klein and Z-Image Turbo across 6 Iconic Haute Couture Archetypes:
1. Brazil: Gisele & Lima (Amber Bronze Goddess)
2. South Africa: Candice Swanepoel (Blonde Angelic Muse)
3. Slavic: Irina Shayk (Emerald Siren)
4. East Asia: Sui He & Liu Wen (Celestial Muse)
5. Nordic: Ice Blue Goddess
6. Mediterranean: Velvet Siren
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
from scripts.benchmark_model_comparison import create_side_by_side_board

RUNWAY_DIR = ROOT / "outputs" / "runway_angels_benchmark"
RAW_DIR = RUNWAY_DIR / "raw"
CLEAN_DIR = RUNWAY_DIR / "clean_raw"
BOARDS_DIR = RUNWAY_DIR / "comparison_boards"

ANGEL_CASES = [
    {
        "id": "angel01_brazil_bronze",
        "title": "Angel 01: South America · Amber Bronze Goddess",
        "seed": 20262101,
        "prompt": (
            "Breathtaking cinematic 35mm photograph of an extraordinarily gorgeous Brazilian supermodel, capturing the legendary runway power of Gisele Bündchen and the fierce feline sensuality of Adriana Lima (维密巴西天神超模、吉赛尔邦辰台步气场、利马美洲豹般野性迷人、黄金微晒古铜肌、九头身顶级比例、绝无浓妆假面). "
            "Sculpted European-Latina bone structure, noble straight high nasal bridge, deep alluring dark hazel eyes with intense magnetic gaze, natural full hydrated lips. "
            "Glowing sun-kissed honey-bronze skin with natural micro-texture and subtle body shimmer, toned athletic abdomen and slender sculpted collarbones. "
            "Voluminous sun-bleached golden-brown beach waves violently whipped by runway wind machines with glowing backlit highlights. "
            "Wearing an unbuttoned champagne-gold liquid satin dressing robe over an exquisite golden crystal lingerie set, backstage golden runway light beams cutting through atmospheric haze, shot on Hasselblad H6D-100c 100mm lens, Vogue runway editorial masterpiece."
        )
    },
    {
        "id": "angel02_candice_blonde",
        "title": "Angel 02: South Africa · Blonde Angelic Muse",
        "seed": 20262102,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily stunning South African Victoria's Secret Angel, embodying the iconic beauty of Candice Swanepoel (维密经典糖糖天使、黄金腰臀比、芭比般精致无暇神颜、绝顶超模身材、绝非浓妆). "
            "Flawless clear porcelain skin with luminous natural glow, completely blemish-free and zero freckles. "
            "Exquisite feminine bone structure, tiny sculpted waist, long graceful swan neck, sparkling ice-blue doe eyes filled with playful coquettish warmth, sweet dimpled natural smile with softly parted pink lips. "
            "Cascading honey-butter blonde voluminous curls bouncing with runway motion. "
            "Wearing an unbuttoned signature pink-and-white striped silk backstage robe over a delicate baby-pink French lace corset, backstage dressing room with Hollywood bulb vanity mirrors, soft warm ring-light reflections, 35mm prime documentary photography."
        )
    },
    {
        "id": "angel03_slavic_emerald",
        "title": "Angel 03: Slavic · Emerald Siren",
        "seed": 20262103,
        "prompt": (
            "Striking high-fashion 35mm editorial photograph of an arresting 23-year-old Slavic high-fashion supermodel, blending the razor-sharp cheekbones of Irina Shayk and the haunting baby-doll allure of Natalia Vodianova. "
            "High razor-sharp cheekbones, intense piercing emerald-green cat eyes, full sultry lips, flawless alabaster skin with fine natural pores. "
            "Sleek center-parted dark espresso hair tucked behind ears, wearing a structured midnight-black silk satin dressing robe with dramatic sheer lace sleeves. "
            "Backstage dark velvet curtain background, dramatic rim lighting, shot on Leica Noctilux 50mm f/0.95, Paris Fashion Week haute couture."
        )
    },
    {
        "id": "angel04_suihe_celestial",
        "title": "Angel 04: East Asia · Celestial Muse",
        "seed": 20262104,
        "prompt": (
            "Ethereal candid 35mm photograph of a breathtaking 23-year-old Chinese supermodel, embodying the radiant porcelain luminosity of Sui He and the regal commanding aura of Liu Wen (何穗发光冷白皮仙姑、流光双翼天使、东方高级脸大女主、气场全开). "
            "Luminous translucent milky-white skin glowing from within under runway spotlights, smooth elegant jawline, captivating elongated dark almond phoenix eyes, calm blooming smile with natural rosy lips. "
            "Silky obsidian black hair falling in cascading waves, wearing shimmering iridescent mother-of-pearl crystalline angel wings and a flowing silver-white silk chiffon robe. "
            "Backstage runway entrance with dramatic blue and silver haze, Kodak Portra 400 aesthetic, iconic Victoria's Secret haute couture."
        )
    },
    {
        "id": "angel05_nordic_ice",
        "title": "Angel 05: Nordic · Ice Blue Goddess",
        "seed": 20262105,
        "prompt": (
            "Regal candid 35mm film photograph of a majestic 22-year-old Scandinavian Nordic supermodel standing backstage at an international high couture gala. "
            "Aristocratic sculpted bone structure, glacial crystalline light-blue eyes, naturally plump rose lips, pristine porcelain fair skin with delicate natural micro-texture. "
            "Long platinum silver-blonde hair cascading down her shoulders in loose waves, wearing an ice-blue liquid silk gown with crystal shoulder accents. "
            "Cool atmospheric ambient lighting with warm backstage incandescent highlights, Contax T2 35mm f/2.8 lens, legendary high-fashion magazine documentary."
        )
    },
    {
        "id": "angel06_mediterranean_velvet",
        "title": "Angel 06: Mediterranean · Velvet Siren",
        "seed": 20262106,
        "prompt": (
            "Sensational candid 35mm editorial portrait of a stunning 24-year-old Mediterranean Italian supermodel embodying the timeless sultry allure of Monica Bellucci. "
            "Deep sculpted Mediterranean bone structure, large soulful dark brown almond eyes, rich crimson lips in confident relaxed smile, warm golden-olive skin with natural fine pores. "
            "Rich voluminous dark chestnut curls framing her collarbones, wearing a black velvet robe over a vintage corsetry. "
            "Gilded baroque mirror background with warm amber candlelight, timeless cinematic realism, Vogue Italia cover quality."
        )
    }
]


def assemble_runway_6grid_board(image_paths: list[Path], title: str, subtitle: str, output_path: Path) -> Path:
    """Build dedicated 6-grid board (2 columns x 3 rows) for Runway Angels."""
    if len(image_paths) < 6:
        print(f"Warning: Need 6 images for 6-grid, got {len(image_paths)}. Falling back to available.")
    
    images = [Image.open(p).convert("RGB") for p in image_paths[:6]]
    tile_w, tile_h = 576, 1024
    resized = [img.resize((tile_w, tile_h), Image.Resampling.LANCZOS) for img in images]

    margin = 35
    gap_x = 25
    gap_y = 25
    header_h = 160
    footer_h = 90

    canvas_w = margin * 2 + tile_w * 2 + gap_x
    canvas_h = margin * 2 + header_h + tile_h * 3 + gap_y * 2 + footer_h

    # Deep obsidian satin background
    canvas = Image.new("RGB", (canvas_w, canvas_h), (16, 18, 22))
    draw = ImageDraw.Draw(canvas)

    draw.text((margin + 10, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 75), subtitle, fill=(160, 165, 175))

    positions = [
        (margin, margin + header_h),
        (margin + tile_w + gap_x, margin + header_h),
        (margin, margin + header_h + tile_h + gap_y),
        (margin + tile_w + gap_x, margin + header_h + tile_h + gap_y),
        (margin, margin + header_h + (tile_h + gap_y) * 2),
        (margin + tile_w + gap_x, margin + header_h + (tile_h + gap_y) * 2),
    ]

    for img, pos in zip(resized, positions):
        canvas.paste(img, pos)

    foot_y = canvas_h - margin - footer_h + 30
    draw.text((margin + 10, foot_y), "Local Drama Studio · Runway Angels 6-Pack Series · Intel Arc A750 Benchmark", fill=(120, 125, 135))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Runway] 6-Grid board generated: {output_path}")
    return output_path


def run_runway_benchmark_suite():
    print("=" * 75)
    print(" Runway Angels 6-Pack Systematic Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Architecture: Arc A750 8GB VRAM Isolation + Dynamic API Decoupling")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    flux_outputs = []
    z_outputs = []

    for case in ANGEL_CASES:
        cid = case["id"]
        prompt = case["prompt"]
        seed = case["seed"]
        print(f"\n>>> Running Angel: {case['title']} <<<")

        # 1. FLUX.3 Klein: use film foto LoRA for runway editorial, or girlslikeflux for East Asian
        if "east_asia" in cid:
            chosen_lora = "girlslikeflux_lyf5.safetensors"
            lora_str = 0.70
            run_prompt = f"girlslikeflux_lyf5, {prompt}"
        else:
            chosen_lora = "flux_film_foto.safetensors"
            lora_str = 0.65
            run_prompt = prompt

        print(f"  Generating: FLUX.3 Klein (16 steps, er_sde, CFG 1.0, LoRA: {chosen_lora} {lora_str})...")
        t0 = time.time()
        f_raw = run_generation(
            engine="flux3_klein",
            prompt=run_prompt,
            seed=seed,
            batch_count=1,
            output_dir=RAW_DIR,
            overrides={"lora_name": chosen_lora, "lora_strength": lora_str, "steps": 16, "cfg": 1.0}
        )[0]
        f_latency = time.time() - t0
        flux_outputs.append(f_raw)

        # 2. Z-Image Turbo (Native 8-Step High-Fidelity DiT)
        print("  Generating: Z-Image Turbo (8 steps, euler, CFG 1.0, Native DiT)...")
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
        z_outputs.append(z_raw)

        # Generate Individual Side-by-Side Board
        sbs_board = BOARDS_DIR / f"{cid}_sbs_comparison.jpg"
        create_side_by_side_board(
            img_left_path=f_raw,
            title_left="FLUX.3 Klein + Realism LoRA (0.35)",
            subtitle_left=f"16 Steps | er_sde | Latency: {f_latency:.1f}s",
            img_right_path=z_raw,
            title_right="Z-Image Turbo (Native 6B DiT)",
            subtitle_right=f"8 Steps | euler | Latency: {z_latency:.1f}s",
            main_title=f"{case['title']} · A/B COMPARISON",
            output_path=sbs_board
        )

    # Build 6-Grid Boards for both
    if len(flux_outputs) >= 6:
        board_f = BOARDS_DIR / "runway_angels_flux3_klein_6grid.jpg"
        assemble_runway_6grid_board(
            flux_outputs[:6],
            title="RUNWAY ANGELS · HAUTE COUTURE 6-PACK",
            subtitle="FLUX.3 Klein + Realism LoRA (0.35) · 35mm Backstage & Runway Lighting",
            output_path=board_f
        )

    if len(z_outputs) >= 6:
        board_z = BOARDS_DIR / "runway_angels_z_image_turbo_6grid.jpg"
        assemble_runway_6grid_board(
            z_outputs[:6],
            title="RUNWAY ANGELS · HAUTE COUTURE 6-PACK",
            subtitle="Z-Image Turbo Native 6B DiT · Natural Skin Micro-Texture & Air-Flow Bokeh",
            output_path=board_z
        )

    print("\n" + "=" * 75)
    print(" Runway Angels Benchmark Suite Completed Successfully!")
    print(f" Boards Output Directory: {BOARDS_DIR}")
    print("=" * 75)


if __name__ == "__main__":
    run_runway_benchmark_suite()
