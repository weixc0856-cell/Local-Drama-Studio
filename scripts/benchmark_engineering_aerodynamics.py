#!/usr/bin/env python3
"""
scripts/benchmark_engineering_aerodynamics.py
Engineering, Mechanical & Scientific Accuracy Benchmark Suite.
Tests FLUX.3 Klein and Z-Image Turbo across 3 Rigorous Engineering Scenarios:
1. Automotive Product Photography: Metallic paint, ceramic brakes, intricate mechanical realism
2. Automotive Wind Tunnel Test: Physical aerodynamics, smoke streamlines, wind tunnel nozzle structure
3. Fluid Dynamics (CFD) Scientific Diagram: Pressure gradient heatmap, streamline vortex, technical clarity
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

BENCHMARK_DIR = ROOT / "outputs" / "engineering_benchmark"
RAW_DIR = BENCHMARK_DIR / "raw"
CLEAN_DIR = BENCHMARK_DIR / "clean_raw"
BOARDS_DIR = BENCHMARK_DIR / "comparison_boards"

ENGINEERING_CASES = [
    {
        "id": "eng01_automotive_product",
        "title": "Case 01 · Automotive Product Photography · Mechanical Realism",
        "seed": 20264101,
        "prompt": (
            "Hyper-realistic professional studio photograph of a sleek modern high-performance supercar parked in a minimalist dark concrete photography studio. "
            "Master automotive commercial framing: Three-quarter front low-angle hero perspective. "
            "Flawless liquid metallic titanium-silver automotive paint reflecting crisp overhead softbox studio light panels. "
            "Intricately detailed mechanical components: Cross-drilled carbon-ceramic brake rotors, forged aluminum multi-spoke dark alloy wheels, vibrant yellow Brembo brake calipers with accurate bolts, functional carbon-fiber aerodynamic front splitter and honeycomb radiator intake grille. "
            "Perfect physical proportions, authentic headlight optical LED lens refraction, zero impossible fictional parts. Hasselblad H6D-100c 80mm lens, flawless commercial catalog quality."
        )
    },
    {
        "id": "eng02_wind_tunnel_aerodynamics",
        "title": "Case 02 · Automotive Wind Tunnel Test · Physical Aerodynamics",
        "seed": 20264102,
        "prompt": (
            "Authentic industrial engineering documentary photograph of a sleek aerodynamic sports car undergoing full-scale aerodynamic smoke flow testing inside a cutting-edge automotive wind tunnel laboratory. "
            "Crisp white laminar smoke streamlines injected from calibrated nozzle probes, flowing smoothly over the aerodynamic hood, adhering seamlessly across the curved windscreen, and detaching into controlled vortices behind the rear spoiler. "
            "Industrial environment: Massive steel honeycomb airflow nozzle visible in background, textured turntable floor with aerodynamic boundary-layer suction plates, scientific observation lighting with precise high-speed flash freezing smoke tracer particles. "
            "Accurate fluid flow physics, zero surreal artifacts, professional automotive engineering review masterpiece, 35mm prime lens."
        )
    },
    {
        "id": "eng03_cfd_fluid_dynamics_diagram",
        "title": "Case 03 · Computational Fluid Dynamics (CFD) · Scientific Visualization",
        "seed": 20264103,
        "prompt": (
            "High-resolution scientific computational fluid dynamics (CFD) simulation visualization illustrating aerodynamic pressure and velocity distribution around an airfoil and streamlined vehicle profile. "
            "Clear technical engineering graphics: Continuous rainbow contour pressure gradient map transitioning smoothly from high-pressure red at the leading stagnation point to low-pressure deep blue and cyan over the upper suction surface. "
            "Crisp vector-like streamline trajectories showing laminar boundary layer flow and downstream vortex shedding wake region. "
            "Clean dark slate-grey scientific background, professional technical legend color bar on the right side indicating velocity magnitude in meters per second (m/s), clean educational textbook illustration quality, zero gibberish symbols."
        )
    }
]


def assemble_engineering_3grid(image_paths: list[Path], title: str, subtitle: str, output_path: Path) -> Path:
    """Build a horizontal 3-panel showcase board for engineering benchmarks."""
    images = [Image.open(p).convert("RGB") for p in image_paths[:3]]
    panel_w, panel_h = 576, 1024
    resized = [img.resize((panel_w, panel_h), Image.Resampling.LANCZOS) for img in images]

    margin = 35
    gap = 25
    header_h = 150
    footer_h = 80

    canvas_w = margin * 2 + panel_w * 3 + gap * 2
    canvas_h = margin * 2 + header_h + panel_h + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (16, 18, 22))
    draw = ImageDraw.Draw(canvas)

    draw.text((margin + 10, margin + 20), title, fill=(245, 245, 248))
    draw.text((margin + 12, margin + 75), subtitle, fill=(160, 165, 175))

    for i, img in enumerate(resized):
        pos_x = margin + i * (panel_w + gap)
        pos_y = margin + header_h
        canvas.paste(img, (pos_x, pos_y))

    foot_y = canvas_h - margin - footer_h + 30
    draw.text((margin + 10, foot_y), "Local Drama Studio · Engineering & Scientific Accuracy Benchmark · Intel Arc A750", fill=(120, 125, 135))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=94, optimize=True)
    print(f"[Engineering] 3-Panel board saved: {output_path}")
    return output_path


def run_engineering_benchmark():
    print("=" * 75)
    print(" Engineering & Aerodynamics Benchmark: FLUX.3 Klein vs Z-Image Turbo")
    print(" Evaluating Mechanical Realism, Physical Smoke Flow, and Scientific Diagrams")
    print("=" * 75)

    for d in [RAW_DIR, CLEAN_DIR, BOARDS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    flux_outputs = []
    z_outputs = []

    for case in ENGINEERING_CASES:
        cid = case["id"]
        prompt = case["prompt"]
        seed = case["seed"]
        title = case["title"]
        print(f"\n>>> Running Scenario: {title} <<<")

        # 1. FLUX.3 Klein (Native, zero LoRA to evaluate raw mechanical prior)
        f_existing = list(RAW_DIR.glob(f"flux3_klein_{seed}_*.png"))
        if f_existing:
            f_raw = f_existing[0]
            print(f"  FLUX.3 already exists -> {f_raw.name}")
        else:
            print("  Generating: FLUX.3 Klein (16 steps, er_sde, CFG 1.0, Native Base)...")
            t0 = time.time()
            f_raw = run_generation(
                engine="flux3_klein",
                prompt=prompt,
                seed=seed,
                batch_count=1,
                output_dir=RAW_DIR,
                overrides={"steps": 16, "cfg": 1.0, "use_lora": False}
            )[0]
            print(f"  FLUX.3 done in {time.time() - t0:.2f}s -> {f_raw.name}")
        flux_outputs.append(f_raw)

        # 2. Z-Image Turbo (8 steps, euler, Native DiT)
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

        # Generate SBS comparison board
        sbs_path = BOARDS_DIR / f"{cid}_sbs_comparison.jpg"
        create_side_by_side_board(
            img_left_path=f_raw,
            title_left="FLUX.3 Klein (Native Base)",
            subtitle_left="16 Steps | er_sde | Zero LoRA Engineering",
            img_right_path=z_raw,
            title_right="Z-Image Turbo (Native DiT)",
            subtitle_right="8 Steps | euler | Zero LoRA Native",
            main_title=f"Engineering Comparison · {title}",
            output_path=sbs_path
        )

    # 3-Panel Showcases
    assemble_engineering_3grid(
        image_paths=flux_outputs,
        title="FLUX.3 Klein · Engineering & Physical Accuracy Showcase",
        subtitle="Automotive Product Photography, Wind Tunnel Smoke Flow, and Scientific CFD Visualization",
        output_path=BOARDS_DIR / "engineering_flux3_klein_3panel.jpg"
    )

    assemble_engineering_3grid(
        image_paths=z_outputs,
        title="Z-Image Turbo · Engineering & Physical Accuracy Showcase",
        subtitle="Automotive Product Photography, Wind Tunnel Smoke Flow, and Scientific CFD Visualization",
        output_path=BOARDS_DIR / "engineering_z_image_turbo_3panel.jpg"
    )

    print("\n[SUCCESS] Engineering & Aerodynamics Benchmark completed successfully!")


if __name__ == "__main__":
    run_engineering_benchmark()
