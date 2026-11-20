#!/usr/bin/env python3
"""
scripts/remaster_daily_series_z_image.py
Universal Z-Image Turbo 6B Remaster Engine for Historical Daily Collections.
Eliminates all actress LoRA triggers and FLUX plastic artifacts.
Automatically generates dual-language showcase boards:
- [collection]_4grid_cn.png / [collection]_6grid_cn.png (Chinese)
- [collection]_4grid_en.png / [collection]_6grid_en.png (Pure English)
"""

import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.produce import produce_z_image_turbo

OUTPUT_ROOT = Path(os.environ.get("DRAMA_OUTPUT_ROOT", str(REPO_ROOT / "studio_data")))
WINDIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"

FONT_ZH_BOLD = str(WINDIR / "msyhbd.ttc")
FONT_ZH_REG = str(WINDIR / "msyh.ttc")
FONT_EN_BOLD = str(WINDIR / "arialbd.ttf")
FONT_EN_REG = str(WINDIR / "arial.ttf")

CLEAN_TRIGGERS = [
    r"girlslikeflux_[a-zA-Z0-9]+,\s*",
    r"flux_realism_[a-zA-Z0-9]+,\s*",
    r"flux_film_[a-zA-Z0-9]+,\s*",
    r"<lora:[^>]+>",
]

def sanitize_prompt(prompt: str) -> str:
    cleaned = prompt
    for pat in CLEAN_TRIGGERS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def build_bilingual_grid(
    image_paths: list[Path],
    titles_zh: list[str],
    titles_en: list[str],
    main_title_zh: str,
    sub_title_zh: str,
    main_title_en: str,
    sub_title_en: str,
    output_path_zh: Path,
    output_path_en: Path,
    cols: int = 2,
    rows: int = 2
):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    tile_w, tile_h = 600, 1060  # 9:16 vertical ratio
    pad = 16
    header_h = 135
    total_w = cols * tile_w + (cols + 1) * pad
    total_h = header_h + rows * tile_h + (rows + 1) * pad

    for lang, main_t, sub_t, titles, out_p, f_bold, f_reg, f_tile in [
        ("zh", main_title_zh, sub_title_zh, titles_zh, output_path_zh, FONT_ZH_BOLD, FONT_ZH_REG, FONT_ZH_BOLD),
        ("en", main_title_en, sub_title_en, titles_en, output_path_en, FONT_EN_BOLD, FONT_EN_REG, FONT_EN_BOLD)
    ]:
        board = Image.new("RGB", (total_w, total_h), "#F8FAFC")
        draw = ImageDraw.Draw(board)

        # Top Accent bar
        draw.rectangle([0, 0, total_w, 10], fill="#2563EB")

        f_head = ImageFont.truetype(f_bold, 40)
        f_sub = ImageFont.truetype(f_reg, 21)
        f_lbl = ImageFont.truetype(f_tile, 20)

        draw.text((pad + 12, 28), main_t, font=f_head, fill="#0F172A")
        draw.text((pad + 14, 82), sub_t, font=f_sub, fill="#475569")

        for i, img in enumerate(images[:rows * cols]):
            r = i // cols
            c = i % cols
            x = pad + c * (tile_w + pad)
            y = header_h + pad + r * (tile_h + pad)

            resized = img.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
            board.paste(resized, (x, y))
            draw.rectangle([x, y, x + tile_w, y + tile_h], outline="#E2E8F0", width=2)

            label_h = 52
            draw.rectangle([x, y + tile_h - label_h, x + tile_w, y + tile_h], fill="#0F172ACC")
            if i < len(titles):
                draw.text((x + 16, y + tile_h - label_h + 14), titles[i], font=f_lbl, fill="#F8FAFC")

        out_p.parent.mkdir(parents=True, exist_ok=True)
        board.save(out_p, quality=95)
        print(f"[+] Saved {lang.upper()} grid board: {out_p}")


DAY02_TASKS = [
    {
        "id": "day02_01_china_morning",
        "title_zh": "01 · 中国 · 晨曦微风与白瓷茶盏",
        "title_en": "01 · China · Morning Sunbeam & Ceramic Cup",
        "seed": 20268201,
        "prompt": (
            "Authentic candid 35mm film photograph of a beautiful young 20-year-old Chinese woman relaxing by a sunlit apartment window on a quiet golden morning. "
            "Delicate East Asian classical bone structure, smooth slender neck and natural jawline, soft morning bedhead dark hair with wispy flyaway strands illuminated by golden side sunlight. "
            "Pristine bare skin with natural micro-texture and soft warm morning glow, natural tender pink hydrated lips, calm affectionate dark almond eyes looking softly towards the camera. "
            "Wearing an oversized cozy ivory ribbed knit cotton sweater, sleeves slightly covering her palms as she holds a warm ceramic tea cup, steam gently rising. "
            "Sheer white linen curtains billowing gently in soft morning breeze, golden morning sunlight casting long warm shadows across wooden floor, Leica M11 50mm f/1.4 Summilux, Kodak Portra 400 warmth."
        )
    },
    {
        "id": "day02_02_western_loft",
        "title_zh": "02 · 欧美 · 纽约Loft慵懒窗台",
        "title_en": "02 · Western · NYC Industrial Loft Morning",
        "seed": 20268202,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 22-year-old Caucasian woman sitting cross-legged on a wide wooden window seat in a sun-drenched industrial loft. "
            "Sculpted European bone structure, high cheekbones, sparkling amber-hazel eyes with natural laugh crinkles, delicate light dusting of freckles, completely authentic skin pores and fine texture. "
            "Tousled sun-bleached golden-brown wavy hair falling effortlessly around her shoulders, rim-lit by bright morning sun. "
            "Wearing a slouchy heather-grey oversized cashmere cardigan over a white ribbed tank top, holding a steaming white ceramic mug in both hands. "
            "Exposed red brick wall and huge industrial grid windows in background, dust motes dancing in sunbeams, Contax T2 35mm f/2.8 lens, cinematic documentary realism."
        )
    },
    {
        "id": "day02_03_japan_tatami",
        "title_zh": "03 · 日本 · 京都町屋障子窗茶道",
        "title_en": "03 · Japan · Kyoto Machiya Shoji Morning Tea",
        "seed": 20268203,
        "prompt": (
            "Authentic candid Japanese film portrait of an exquisite 20-year-old Japanese woman kneeling gently beside an open sliding shoji screen overlooking a morning moss garden. "
            "Petite delicate Japanese features, soft oval face, airy wispy fringe gently grazing her eyebrows with loose strands dancing in morning garden breeze, clear dewy dark eyes reflecting bright morning sky. "
            "Translucent glowing porcelain skin with realistic natural texture, subtle rosy morning flush on cheeks, natural pale peach lips. "
            "Wearing a minimalist pure white cotton home blouse and soft linen trousers, delicate slender fingers resting lightly beside a traditional handcrafted ceramic green tea cup on tatami mat. "
            "Soft diffused natural daylight filtering through bamboo eaves, gentle green garden bokeh, Fujifilm Pro 400H emulation, peaceful quiet cinematic aesthetic."
        )
    },
    {
        "id": "day02_04_korea_penthouse",
        "title_zh": "04 · 韩国 · 首尔高空晨雾冰美式",
        "title_en": "04 · Korea · Seoul Skyline Penthouse Dawn",
        "seed": 20268204,
        "prompt": (
            "Candid editorial portrait of an extraordinarily elegant 21-year-old Korean woman standing by a floor-to-ceiling panoramic glass window in a high-rise Seoul penthouse at dawn. "
            "Refined clean Korean facial contours, smooth graceful jawline and slender neck, poised intellectual gaze looking out thoughtfully towards morning mist over Han River, natural MLBB soft rose hydrated lips. "
            "Immaculate cool porcelain glass skin with realistic micro-pores, zero heavy makeup, quiet effortless luxury. "
            "Sleek silky black-brown hair casually swept behind one ear, wearing luxurious minimalist ivory silk loungewear robe over a camisole. "
            "Modern minimalist marble side table with an iced Americano glass catching morning light, soft pale blue and silvery morning city glow, Hasselblad X2D 90mm lens, Vogue Korea morning editorial style."
        )
    }
]


DAY03_TASKS = [
    {
        "id": "day03_01_china_rain",
        "title_zh": "01 · 中国 · 江南烟雨油纸伞微步",
        "title_en": "01 · China · Misty Rain Alley & Oiled Paper Umbrella",
        "seed": 20268301,
        "prompt": (
            "Authentic cinematic 35mm film photograph of an extraordinarily beautiful 20-year-old Chinese woman walking through a misty rain-slicked ancient stone alley. "
            "Delicate East Asian classical bone structure, smooth slender neck and graceful profile, clear dark almond eyes looking back with quiet soulful warmth. "
            "Pristine porcelain skin with subtle dewiness, natural soft rose petal lips, fine damp dark hair strands gently clinging to her cheek in misty air. "
            "Holding a minimalist bamboo-framed oiled-paper umbrella with translucent raindrops rolling off edge, wearing an elegant beige double-breasted trench coat. "
            "Wet blue-grey flagstones reflecting soft amber lanterns from ancient wooden houses, Leica M11 50mm f/1.4 Summilux, cinematic Wong Kar-wai mood."
        )
    },
    {
        "id": "day03_02_western_rain",
        "title_zh": "02 · 英国 · 伦敦雨夜大伞与琥珀街灯",
        "title_en": "02 · UK · London Rain Night & Victorian Streetlights",
        "seed": 20268302,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 22-year-old British woman standing on a rain-slicked London street at twilight. "
            "Sculpted European bone structure, refined cheekbones, captivating hazel eyes glistening with reflected city lights, natural light freckles, authentic skin texture and micro-pores. "
            "Tousled damp wavy honey-brown hair framed under a classic large black umbrella, wearing a tailored classic camel wool trench coat with collar turned up. "
            "Glossy wet asphalt reflecting red bus taillights and warm amber Victorian street lamps in creamy optical bokeh, Contax T2 35mm f/2.8 lens, authentic documentary realism."
        )
    },
    {
        "id": "day03_03_japan_rain",
        "title_zh": "03 · 日本 · 东京微雨透明伞与霓虹",
        "title_en": "03 · Japan · Tokyo Drizzle & Vinyl Umbrella Reflections",
        "seed": 20268303,
        "prompt": (
            "Authentic candid Japanese film portrait of an exquisite 20-year-old Japanese young beauty holding a transparent vinyl umbrella on a rainy Tokyo street at dusk. "
            "Petite delicate Japanese features, smooth oval jawline, airy damp bangs lightly separated by raindrops, big clear dark eyes gazing with quiet warmth directly at camera, natural peach lips. "
            "Translucent glowing fair skin with soft natural cheek flush, fine water droplets beading on clear umbrella. "
            "Wearing an oversized navy knit cardigan over cream turtleneck, holding umbrella with both hands. "
            "Rain-blurred Tokyo storefront neon signs and traffic lights creating colorful bokeh circles, Fujifilm Superia 400 aesthetic, nostalgic cinema mood."
        )
    },
    {
        "id": "day03_04_korea_rain",
        "title_zh": "04 · 韩国 · 首尔都会冷调雨夜大女主",
        "title_en": "04 · Korea · Seoul Modern Wet Boulevard Night",
        "seed": 20268304,
        "prompt": (
            "Candid editorial portrait of an extraordinarily elegant 21-year-old Korean woman standing under a minimalist matte-black umbrella on a rain-drenched Seoul boulevard at night. "
            "Refined clean Korean bone structure, smooth noble jawline and slender neck, calm piercing intellectual gaze, cool porcelain glass skin with realistic micro-texture, natural soft berry MLBB lips. "
            "Sleek dark straight hair neatly tucked behind ears, water drops sliding down tailored charcoal-black wool coat with structured shoulders. "
            "Wet granite sidewalk and dark glass skyscrapers reflecting long vertical streaks of cool white headlights and cyan signage, Hasselblad X2D 90mm lens, Vogue Korea rainy night editorial style."
        )
    }
]


def remaster_day03():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day03"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 03: 《雨落都市 · 伞下回眸》 (City Rain & Reflections)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY03_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/4] Generating: {title_zh} ...")

        t0 = time.time()
        res_path = produce_z_image_turbo(
            prompt=prompt,
            width=768,
            height=1360,
            seed=seed,
            prefix=f"remaster_{task_id}"
        )
        import shutil
        shutil.copy(res_path, out_img)
        print(f"    Done in {time.time() - t0:.1f}s -> {out_img.name}")
        generated.append(out_img)

    grid_zh = day_dir / "day03_city_rain_4grid_cn.png"
    grid_en = day_dir / "day03_city_rain_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 03 《雨落都市 · 伞下回眸》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 真实雨丝湿发 · 纯天然毛孔 · 告别塑料假面",
        main_title_en="City Rain & Reflections · Day 03 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Authentic Rain Texture & Skin Pores · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 03 Remaster complete!")


def remaster_day02():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day02"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 02: 《晨光漫溢 · 窗边与咖啡》 (Morning Light & Window)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY02_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/4] Generating: {title_zh} ...")

        t0 = time.time()
        res_path = produce_z_image_turbo(
            prompt=prompt,
            width=768,
            height=1360,
            seed=seed,
            prefix=f"remaster_{task_id}"
        )
        import shutil
        shutil.copy(res_path, out_img)
        print(f"    Done in {time.time() - t0:.1f}s -> {out_img.name}")
        generated.append(out_img)

    # Build Bilingual 4-Grid Boards
    grid_zh = day_dir / "day02_morning_light_4grid_cn.png"
    grid_en = day_dir / "day02_morning_light_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 02 《晨光漫溢 · 窗边与咖啡》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 真实皮肤微血管毛孔 · 纯天然胶原蛋白 · 告别塑料假面",
        main_title_en="Morning Light & Window Breeze · Day 02 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Authentic Skin Micro-Pores · Zero Plastic Artificiality",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 02 Remaster complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="02", help="Day collection to remaster")
    args = parser.parse_args()

    if args.day == "02":
        remaster_day02()
    elif args.day == "03":
        remaster_day03()
    elif args.day == "all":
        remaster_day02()
        remaster_day03()
    else:
        print(f"Day {args.day} queue ready.")
