#!/usr/bin/env python3
"""
scripts/benchmark_aspect_ratios_16x9.py
Aspect Ratio Benchmark: 16:9 Cinematic Widescreen vs 9:16 Vertical Portrait.
Evaluates spatial composition, horizon perspective, and distortion resistance across 4 classic scenes:
1. Shanghai Late Autumn Street Candid (1360x768 16:9)
2. Kamakura Coastal Road Transparency (1360x768 16:9)
3. Haute Couture Celestial Muse (1360x768 16:9)
4. Contemporary Museum Heiress (1360x768 16:9)
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

BENCHMARK_DIR = ROOT / "outputs" / "aspect_ratio_benchmark"
RAW_DIR = BENCHMARK_DIR / "raw"
CLEAN_DIR = BENCHMARK_DIR / "clean_raw"
BOARDS_DIR = BENCHMARK_DIR / "comparison_boards"

WIDESCREEN_SCENES = [
    {
        "id": "scene01_shanghai_16x9",
        "title": "Scene 01 · Shanghai Autumn Street · 16:9 Cinematic Widescreen",
        "seed": 20266101,
        "width": 1360,
        "height": 768,
        "prompt": (
            "Cinematic 16:9 widescreen candid 35mm street photograph of a serene 21-year-old Chinese woman walking down Shanghai Julu Road in late golden autumn. "
            "Master widescreen environmental portrait framing: Wide street perspective with golden plane tree canopy extending across the upper third. "
            "Subject strolling gracefully on the right third of the frame, body turned at a three-quarter angle in motion. "
            "Holding a warm paper coffee cup, soft focused gaze with a gentle blooming micro-smile, authentic natural blemish-free translucent skin with realistic fine pores. "
            "Wearing an oversized oatmeal-beige cashmere turtleneck knit sweater and flowing charcoal grey tailored wool trousers. "
            "Dappled warm late-afternoon golden hour sunlight streaming through golden falling leaves, historic French concession villa facades and distant vintage bicycle in soft optical bokeh, Leica M11 35mm Summilux lens, iconic Wong Kar-wai documentary realism."
        )
    },
    {
        "id": "scene02_kamakura_16x9",
        "title": "Scene 02 · Kamakura Coastal Railway · 16:9 Cinematic Widescreen",
        "seed": 20266102,
        "width": 1360,
        "height": 768,
        "prompt": (
            "Authentic 16:9 cinematic Japanese 35mm film photograph of an extraordinarily charming 20-year-old Japanese young beauty walking along the Pacific coastal road in Kamakura. "
            "Expansive 16:9 horizon landscape framing: Emerald-blue Pacific ocean waves crashing gently on the left, coastal train crossing barrier in distance. "
            "Subject in relaxed mid-stride on the coastal sidewalk, holding a single canvas tote bag strap, turning back over her shoulder with an effortless candid smile. "
            "Soft dainty jawline, crystal-clear dark doe eyes, silky dark bob hair with wispy air bangs fluttering in ocean breeze. "
            "Wearing a clean white linen short-sleeved collared shirt and pleated navy skirt. "
            "Warm sparkling Pacific summer sunlight, authentic Fujifilm Pro 400H ocean palette, iconic Japanese youth cinema masterpiece."
        )
    },
    {
        "id": "scene03_celestial_muse_16x9",
        "title": "Scene 03 · Celestial Muse Runway · 16:9 Haute Couture Stage",
        "seed": 20266103,
        "width": 1360,
        "height": 768,
        "prompt": (
            "Breathtaking 16:9 widescreen haute couture runway photograph of a stunning 23-year-old East Asian supermodel walking down a grand international fashion gala catwalk. "
            "Epic 16:9 theatrical stage composition: Dramatic atmospheric blue and silver volumetric stage lighting beams cutting through runway haze. "
            "Model positioned centrally in commanding runway stride, wearing majestic shimmering mother-of-pearl crystalline angel wings spanning dramatically across the frame. "
            "Radiant porcelain cold-white luminous skin glowing under spotlights, refined elongated almond phoenix eyes, calm regal smile, flowing silver-white silk chiffon gown. "
            "Blurred front-row audience silhouettes and runway flashbulbs in background, 35mm documentary photography masterpiece."
        )
    },
    {
        "id": "scene04_museum_heiress_16x9",
        "title": "Scene 04 · Contemporary Museum Heiress · 16:9 Architectural Perspective",
        "seed": 20266104,
        "width": 1360,
        "height": 768,
        "prompt": (
            "High-fashion 16:9 editorial architectural portrait of an extraordinarily elegant 21-year-old Korean heiress descending minimalist granite steps of a contemporary art museum in Seoul. "
            "Expansive 16:9 architectural framing: Minimalist exposed concrete walls and bamboo grove filling the background in deep perspective. "
            "Subject walking in rule of thirds diagonal silhouette, carrying a petite black leather handbag, poised intelligent gaze with dewy petal-pink lips and translucent glass skin. "
            "Wearing an oversized tailored charcoal grey wool blazer over a black silk camisole. "
            "Golden hour ambient rim lighting, modern brutalist architecture in sharp focus, Vogue Korea luxury realism."
        )
    }
]


def create_widescreen_side_by_side_board(
    img_left_path: Path,
    title_left: str,
    subtitle_left: str,
    img_right_path: Path,
    title_right: str,
    subtitle_right: str,
    main_title: str,
    output_path: Path
) -> Path:
    """Build dedicated 16:9 widescreen side-by-side comparison board with strictly preserved aspect ratios."""
    img_left = Image.open(img_left_path).convert("RGB")
    img_right = Image.open(img_right_path).convert("RGB")

    # Native 16:9 widescreen tile size: 960x542 (exact 16:9 ratio, zero distortion)
    tile_w, tile_h = 960, 542
    left_resized = img_left.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
    right_resized = img_right.resize((tile_w, tile_h), Image.Resampling.LANCZOS)

    margin = 40
    gap = 30
    header_h = 130
    label_h = 55
    footer_h = 70

    canvas_w = margin * 2 + tile_w * 2 + gap
    canvas_h = margin * 2 + header_h + label_h + tile_h + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 20, 24))
    draw = ImageDraw.Draw(canvas)

    # Main Title
    draw.text((margin + 10, margin + 20), main_title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 70), "Local Drama Studio · 1360x768 Cinematic Landscape Comparison · Intel Arc A750", fill=(160, 165, 175))

    # Column Left (FLUX.3)
    x_left = margin
    y_content = margin + header_h
    draw.text((x_left + 8, y_content + 8), title_left, fill=(230, 235, 245))
    draw.text((x_left + 8, y_content + 30), subtitle_left, fill=(130, 140, 155))
    canvas.paste(left_resized, (x_left, y_content + label_h))

    # Column Right (Z-Image Turbo)
    x_right = margin + tile_w + gap
    draw.text((x_right + 8, y_content + 8), title_right, fill=(230, 235, 245))
    draw.text((x_right + 8, y_content + 30), subtitle_right, fill=(130, 140, 155))
    canvas.paste(right_resized, (x_right, y_content + label_h))

    # Footer
    foot_y = canvas_h - margin - footer_h + 25
    draw.text((margin + 10, foot_y), "Intel Arc A750 (8GB VRAM) · 64GB DDR5 · Windows PyTorch-XPU · Zero Distortion Preserved", fill=(110, 115, 125))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Widescreen] Side-by-side comparison saved: {output_path}")
    return output_path


def assemble_widescreen_4grid(image_paths: list[Path], title: str, subtitle: str, output_path: Path) -> Path:
    """Build dedicated 2x2 grid board for 16:9 widescreen images."""
    images = [Image.open(p).convert("RGB") for p in image_paths[:4]]
    # Resize 16:9 tiles to 680x384
    tile_w, tile_h = 680, 384
    resized = [img.resize((tile_w, tile_h), Image.Resampling.LANCZOS) for img in images]

    margin = 35
    gap_x = 25
    gap_y = 25
    header_h = 150
    footer_h = 80

    canvas_w = margin * 2 + tile_w * 2 + gap_x
    canvas_h = margin * 2 + header_h + tile_h * 2 + gap_y + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (14, 16, 20))
    draw = ImageDraw.Draw(canvas)

    draw.text((margin + 10, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 75), subtitle, fill=(160, 165, 175))

    positions = [
        (margin, margin + header_h),
        (margin + tile_w + gap_x, margin + header_h),
        (margin, margin + header_h + tile_h + gap_y),
        (margin + tile_w + gap_x, margin + header_h + tile_h + gap_y),
    ]

    for img, pos in zip(resized, positions):
        canvas.paste(img, pos)

    foot_y = canvas_h - margin - footer_h + 30
    draw.text((margin + 10, foot_y), "Local Drama Studio · 16:9 Cinematic Widescreen Benchmark · Intel Arc A750", fill=(120, 125, 135))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Widescreen] 2x2 Showcase board saved: {output_path}")
    return output_path


def run_widescreen_benchmark():
    print("=" * 75)
    print(" 16:9 Widescreen Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Testing 1360x768 Cinematic Landscape Framing across 4 Iconic Scenes")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    flux_outputs = []
    z_outputs = []

    for scene in WIDESCREEN_SCENES:
        sid = scene["id"]
        prompt = scene["prompt"]
        seed = scene["seed"]
        title = scene["title"]
        w = scene["width"]
        h = scene["height"]
        print(f"\n>>> Running Scenario: {title} ({w}x{h}) <<<")

        # 1. FLUX.3 Klein
        f_existing = list(RAW_DIR.glob(f"flux3_klein_{seed}_*.png"))
        if f_existing:
            f_raw = f_existing[0]
            print(f"  FLUX.3 already exists -> {f_raw.name}")
        else:
            print(f"  Generating: FLUX.3 Klein (16 steps, er_sde, CFG 1.0, girlslikeflux 0.70, {w}x{h})...")
            t0 = time.time()
            f_raw = run_generation(
                engine="flux3_klein",
                prompt=f"girlslikeflux_lyf5, {prompt}",
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"lora_name": "girlslikeflux_lyf5.safetensors", "lora_strength": 0.70, "steps": 16, "cfg": 1.0, "width": w, "height": h}
            )[0]
            print(f"  FLUX.3 done in {time.time() - t0:.2f}s -> {f_raw.name}")
        flux_outputs.append(f_raw)

        # 2. Z-Image Turbo
        z_existing = list(RAW_DIR.glob(f"z_image_turbo_{seed}_*.png"))
        if z_existing:
            z_raw = z_existing[0]
            print(f"  Z-Image already exists -> {z_raw.name}")
        else:
            print(f"  Generating: Z-Image Turbo (8 steps, euler, CFG 1.0, Native DiT, {w}x{h})...")
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

        # Generate SBS comparison board (widescreen preserved aspect ratio)
        sbs_path = BOARDS_DIR / f"{sid}_sbs_comparison.jpg"
        create_widescreen_side_by_side_board(
            img_left_path=f_raw,
            title_left=f"FLUX.3 Klein (16:9 1360x768)",
            subtitle_left="16 Steps | er_sde | girlslikeflux 0.70",
            img_right_path=z_raw,
            title_right=f"Z-Image Turbo (16:9 1360x768)",
            subtitle_right="8 Steps | euler | Zero LoRA Native DiT",
            main_title=f"16:9 Widescreen Comparison · {title}",
            output_path=sbs_path
        )

    # 4-Grid Showcases
    assemble_widescreen_4grid(
        image_paths=flux_outputs,
        title="FLUX.3 Klein · 16:9 Cinematic Widescreen Showcase",
        subtitle="1360x768 Environmental Landscape Composition: Shanghai, Kamakura, Runway, Museum",
        output_path=BOARDS_DIR / "widescreen_flux3_klein_4grid.jpg"
    )

    assemble_widescreen_4grid(
        image_paths=z_outputs,
        title="Z-Image Turbo · 16:9 Cinematic Widescreen Showcase",
        subtitle="1360x768 Environmental Landscape Composition: Shanghai, Kamakura, Runway, Museum",
        output_path=BOARDS_DIR / "widescreen_z_image_turbo_4grid.jpg"
    )

    print("\n[SUCCESS] 16:9 Widescreen Benchmark completed successfully!")


if __name__ == "__main__":
    run_widescreen_benchmark()
