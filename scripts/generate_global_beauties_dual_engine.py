"""
scripts/generate_global_beauties_dual_engine.py
Day 04 Remaster: 《全球纪实人像 · 双引擎协同日更生成器》
(Daily Candid Realism · Dual Engine Architecture: FLUX.3 Klein & Z-Image Turbo)

Architecture & Hardware Rules (Arc A750 8GB + 64GB DDR5):
- Shanghai, Tokyo, Seoul -> Z-Image Turbo (Native 6B DiT + Qwen3-4B, Zero LoRA, 8 steps, euler/simple)
- Paris / Western Chic  -> FLUX.3 Klein (Distilled, Realism LoRA 0.35, 16 steps, er_sde/simple)
- Common Post-Process    -> Clean raw export + Social web 4-Grid showcase
"""

import os
import sys
import json
import time
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generator import run_generation
from scripts.postprocess import build_four_grid_board, export_clean_raw, export_social_web

OUTPUT_DIR = ROOT / "outputs" / "dual_engine_beauties"
RAW_DIR = OUTPUT_DIR / "raw"
CLEAN_DIR = OUTPUT_DIR / "clean_raw"
WEB_DIR = OUTPUT_DIR / "social_web"

TASKS = [
    {
        "id": "01_shanghai_autumn",
        "engine": "z_image_turbo",
        "city": "Shanghai",
        "title": "【中国·上海巨鹿路】文艺白月光捧咖啡漫步回眸",
        "prompt": (
            "Award-winning candid 35mm environmental street photograph of a serene 21-year-old Chinese woman walking down Shanghai Julu Road in late golden autumn. "
            "Master environmental walking framing: Walking along a sidewalk covered in golden plane tree leaves, turning her body gently back over her shoulder at a 35-degree angle. "
            "Holding a takeaway paper cup of warm latte naturally with both hands. "
            "Pristine East Asian bone structure, quiet soulful dark almond eyes with gentle warmth, naturally blooming rose lips in soft calm breathing repose, authentic translucent porcelain skin with realistic fine micro-pores and zero fake makeup. "
            "Silky dark raven hair drifting gently across her cheek in the breeze, wearing an oversized cream-beige soft cashmere knit sweater. "
            "Historic brick villa facades and warm golden autumn afternoon sunlight filtering through tree canopy with creamy bokeh, cinematic realism documentary."
        ),
        "seed": 20261101,
        "steps": 8,
        "cfg": 1.0,
    },
    {
        "id": "02_paris_leftbank",
        "engine": "flux3_klein",
        "city": "Paris",
        "title": "【欧美·巴黎左岸】法式初熟少女手托微腮闲适浅笑",
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 21-year-old French woman sitting at an outdoor Parisian sidewalk bistro in Saint-Germain. "
            "Master candid cafe framing: Leaning sideways at a 45-degree angle against a small round green marble bistro table, chin resting casually on one palm. "
            "Captivating grey-green doe eyes gazing with warm relaxed curiosity, subtle blooming smile with relaxed lips, smooth blemish-free porcelain skin with authentic micro-pores, tousled honey-blonde wavy hair catching warm rim light. "
            "Wearing an unbuttoned vintage light-blue soft denim shirt. "
            "Woven rattan green bistro chairs and historic Haussmannian stone facade in golden afternoon sunlight, Contax T2 35mm f/2.8 lens, legendary French cinema documentary."
        ),
        "seed": 20261102,
        "steps": 16,
        "cfg": 1.0,
        "lora_name": "flux_realism_xlabs.safetensors",
        "lora_strength": 0.35,
    },
    {
        "id": "03_tokyo_shibuya_rain",
        "engine": "z_image_turbo",
        "city": "Tokyo",
        "title": "【日本·东京雨夜】透明雨伞下的清透回眸",
        "prompt": (
            "Authentic candid 35mm street photograph of an extraordinarily adorable 20-year-old Japanese young beauty standing under a translucent clear umbrella on a rainy evening in Tokyo Shibuya. "
            "Master candid rain street framing: Looking softly into the camera with clear gentle catchlights in large dark eyes, relaxed lips in natural calm breathing repose, delicate Japanese bone structure, pristine fair skin glowing under neon street reflections. "
            "Single hand holding the clear umbrella handle, soft dark bob hair with wispy air bangs damp from the mist, wearing a classic beige oversized trench coat over a high-neck dark sweater. "
            "Cool neon cyan and magenta city lights blending with warm street ramen lantern glow in deep wet asphalt reflections, rich film noir cinematic depth of field."
        ),
        "seed": 20261103,
        "steps": 8,
        "cfg": 1.0,
    },
    {
        "id": "04_seoul_hanriver",
        "engine": "z_image_turbo",
        "city": "Seoul",
        "title": "【韩国·首尔汉江】冷调黄昏风衣随性侧颜",
        "prompt": (
            "Master candid 35mm fashion documentary photograph of a striking 22-year-old Korean woman standing by the Han River promenade in Seoul during twilight blue hour. "
            "Master three-quarter profile framing: Looking thoughtfully towards the city bridge lights across the river, clean sculpted Korean jawline, cool clear eyes, natural hydrated soft lips in calm repose, authentic clean radiant skin texture. "
            "Dark long straight hair fluttering in the river breeze, wearing a structured minimalist charcoal wool long trench coat with hands in pockets. "
            "Seoul skyline bridge lights glowing across the mist over the river, cool blue hour atmospheric lighting, 35mm prime lens cinema tone."
        ),
        "seed": 20261104,
        "steps": 8,
        "cfg": 1.0,
    }
]


def run_dual_engine_suite():
    print("=" * 70)
    print(" Local Drama Studio - Dual-Engine Daily Realism Production Suite")
    print(" Engines: Z-Image Turbo (East Asian) + FLUX.3 Klein (Western)")
    print("=" * 70)

    for d in [RAW_DIR, CLEAN_DIR, WEB_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    generated_raw = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n>>> Task [{idx}/4] {t['title']} | Target Engine: [{t['engine']}]")
        overrides = {
            "steps": t.get("steps"),
            "cfg": t.get("cfg"),
            "lora_name": t.get("lora_name", ""),
            "lora_strength": t.get("lora_strength", 0.0),
        }
        
        try:
            files = run_generation(
                engine=t["engine"],
                prompt=t["prompt"],
                seed=t["seed"],
                batch_count=1,
                output_dir=RAW_DIR,
                overrides=overrides
            )
            if files:
                generated_raw.extend(files)
        except Exception as e:
            print(f"    [Generation Skipped/Offline] {e}")

    # 公共后处理阶段
    if generated_raw:
        print("\n" + "=" * 70)
        print(" Running Unified Post-Processing & 4-Grid Showcase Generation")
        print("=" * 70)
        clean_paths = []
        web_paths = []
        for p in generated_raw:
            cp = export_clean_raw(p, CLEAN_DIR)
            wp = export_social_web(p, WEB_DIR)
            clean_paths.append(cp)
            web_paths.append(wp)

        if len(web_paths) >= 4:
            board_out = WEB_DIR / "daily_showcase_dual_engine_4grid.jpg"
            build_four_grid_board(
                web_paths[:4],
                title="GLOBAL CANDID REALISM · DUAL-ENGINE SUITE",
                subtitle="Z-Image Turbo (East Asian Candid) & FLUX.3 Klein (Western Chic) 35mm Remaster",
                output_path=board_out
            )
            print(f"\n[DONE] Final Showcase Board generated at: {board_out}")


if __name__ == "__main__":
    run_dual_engine_suite()
