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


DAY04_TASKS = [
    {
        "id": "day04_01_china_coastal",
        "title_zh": "01 · 中国 · 海南环岛公路海风白衬衫",
        "title_en": "01 · China · Coastal Highway & White Linen Shirt",
        "seed": 20268401,
        "prompt": (
            "Authentic candid 35mm film photograph of an extraordinarily beautiful 20-year-old Chinese woman standing beside a sun-drenched coastal highway in tropical Hainan. "
            "Delicate East Asian classical bone structure, smooth slender neck and graceful jawline, radiant genuine smile with bright joyful almond eyes looking towards camera. "
            "Sun-kissed glowing skin with natural micro-texture and fine pores, natural dewy peach lips. "
            "Long silky dark hair blown by warm ocean breeze with strands dancing across her laughing face. "
            "Wearing a crisp oversized white linen button-down shirt fluttering in wind over simple cotton tank, sleeves loosely rolled. "
            "Turquoise ocean waves crashing against coastal rocks and tropical palm tree shadows in bright sunny background, Leica M11 50mm f/1.4 Summilux, vibrant natural daylight, Kodak Portra 400 warmth."
        )
    },
    {
        "id": "day04_02_western_highway",
        "title_zh": "02 · 欧美 · 加州一号公路复古敞篷",
        "title_en": "02 · Western · Pacific Coast Highway Convertible",
        "seed": 20268402,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 22-year-old Caucasian woman seated in a vintage convertible on Pacific Coast Highway in California at golden hour. "
            "Sculpted European bone structure, high refined cheekbones, sparkling warm hazel eyes with natural laugh lines, delicate dusting of natural freckles, authentic skin texture with visible micro-pores. "
            "Voluminous wavy golden-blonde hair violently whipped by coastal wind with radiant golden backlit rim light, vintage tortoiseshell sunglasses pushed into hair. "
            "Wearing a casual slouchy off-white knitted tank top, dainty layered gold chains. "
            "Steep coastal cliffs, winding asphalt highway, and endless sparkling Pacific Ocean glowing in molten orange sunset light, Contax T2 35mm f/2.8 lens, cinematic documentary realism."
        )
    },
    {
        "id": "day04_03_japan_okinawa",
        "title_zh": "03 · 日本 · 冲绳堤坝草帽与纯白棉裙",
        "title_en": "03 · Japan · Okinawa Seawall Straw Hat & White Sundress",
        "seed": 20268403,
        "prompt": (
            "Authentic candid Japanese film portrait of an exquisite 20-year-old Japanese young beauty standing on a concrete seawall overlooking crystal-clear turquoise sea in Okinawa. "
            "Petite delicate Japanese features, soft youthful oval face, airy wispy fringe blown sideways by ocean breeze, big expressive dark eyes filled with summer clarity, natural fresh peach lip gloss. "
            "Translucent fair porcelain skin with natural soft flush on sun-warmed cheeks, holding down a wide-brimmed woven straw hat with one slender hand against sea wind. "
            "Wearing a breezy pure white cotton sleeveless sundress fluttering in wind, simple canvas shoulder tote. "
            "Pristine bright emerald-blue ocean water sparkling in afternoon sun with white sea foam, Fujifilm Pro 400H emulation, nostalgic Japanese summer cinema aesthetic."
        )
    },
    {
        "id": "day04_04_korea_jeju",
        "title_zh": "04 · 韩国 · 济州岛玄武岩露台度假千金",
        "title_en": "04 · Korea · Jeju Basalt Ocean Terrace Resort Chic",
        "seed": 20268404,
        "prompt": (
            "Candid editorial portrait of an extraordinarily elegant 21-year-old Korean woman standing by glass railing on oceanfront terrace of a minimalist modern cafe in Jeju Island. "
            "Refined clean Korean facial contours, smooth elegant jawline, calm intellectual dark eyes with direct poised gaze, natural soft rose MLBB hydrated lips. "
            "Flawless cool-tone porcelain glass skin with realistic micro-texture, zero heavy makeup, quiet understated luxury. "
            "Sleek dark straight hair blowing gracefully in ocean wind, wearing an oversized flowing champagne silk resort shirt over white crop top and wide-leg linen trousers. "
            "Dramatic black volcanic basalt rocks meeting deep sapphire ocean waves, modern architectural concrete lines, Hasselblad X2D 90mm lens, Vogue Korea resort editorial style."
        )
    }
]


def remaster_day04():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day04"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 04: 《海风微凉 · 沿海公路与白衬衫》 (Coastal Breeze & Highway)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY04_TASKS, 1):
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

    grid_zh = day_dir / "day04_coastal_breeze_4grid_cn.png"
    grid_en = day_dir / "day04_coastal_breeze_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 04 《海风微凉 · 沿海公路与白衬衫》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 阳光海风发丝 · 纯天然微孔光泽 · 告别塑料假面",
        main_title_en="Coastal Breeze & Ocean Highway · Day 04 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Sunlit Coastal Hair & Skin Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 04 Remaster complete!")


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


DAY05_TASKS = [
    {
        "id": "day05_01_china_bookstore",
        "title_zh": "01 · 中国 · 旧时光书店捧读侧颜",
        "title_en": "01 · China · Vintage Bookstore Sunset Reading",
        "seed": 20268501,
        "prompt": (
            "Authentic candid 35mm film photograph of an extraordinarily beautiful young Chinese woman standing in a quiet vintage bookstore at golden hour. "
            "Delicate East Asian classical bone structure, smooth slender neck and natural jawline, peaceful focused gaze reading an open hardcover book with quiet warmth and soulful intelligence. "
            "Pristine translucent porcelain skin, natural soft peach hydrated lips, flyaway dark hair strands illuminated by low-angle golden sunset light pouring through tall wooden windows. "
            "Wearing an oversized warm cream-beige knit sweater over a vintage white collared shirt. "
            "Surrounded by towering warm dark mahogany bookshelves filled with antique books, dust motes dancing in warm sunbeams, Leica M11 50mm f/1.4 Summilux, Kodak Gold 200 nostalgic warmth."
        )
    },
    {
        "id": "day05_02_western_vinyl",
        "title_zh": "02 · 英国 · 诺丁山黑胶店复古银耳麦",
        "title_en": "02 · UK · Notting Hill Vintage Vinyl & Headphones",
        "seed": 20268502,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 22-year-old British woman browsing vintage vinyl records in a cozy retro record store in London. "
            "Sculpted European bone structure, high refined cheekbones, sparkling amber-hazel eyes with a playful gentle smile, delicate dusting of light freckles across her nose and cheeks, authentic skin texture with visible micro-pores. "
            "Voluminous wavy golden-brown hair spilling naturally over classic vintage silver over-ear headphones, backlit by warm golden sunset light streaming through the storefront glass. "
            "Wearing a slouchy distressed brown leather bomber jacket over a striped cotton tee, fingers casually flipping through a wooden crate of vinyl records. "
            "Colorful vinyl record album covers and retro music posters softly blurred in the background, Contax T2 35mm f/2.8 lens, authentic documentary warmth."
        )
    },
    {
        "id": "day05_03_japan_jimbocho",
        "title_zh": "03 · 日本 · 神保町古书架间澈然回眸",
        "title_en": "03 · Japan · Jimbocho Antique Stacks & Dewy Gaze",
        "seed": 20268503,
        "prompt": (
            "Authentic candid Japanese film portrait of an exquisite 20-year-old Japanese young beauty peeking from between two wooden bookshelves in a narrow vintage bookstore in Jimbocho, Tokyo. "
            "Petite delicate Japanese features, soft oval face, airy wispy bangs gently framing her forehead, dark hair loosely gathered in a casual low bun with loose tendrils, big dewy expressive dark eyes looking directly into the camera with tender warmth, natural fresh nude-peach lip gloss. "
            "Translucent fair porcelain skin, holding an old Japanese poetry book close to her chest. "
            "Wearing a cozy oversized navy knit cardigan over a soft linen blouse. "
            "Floor-to-ceiling wooden shelves stacked with weathered vintage paperbacks, warm incandescent tungsten light bulbs glowing gently overhead, Fujifilm Pro 400H emulation, nostalgic Japanese cinema mood."
        )
    },
    {
        "id": "day05_04_korea_samcheong",
        "title_zh": "04 · 韩国 · 三清洞黑胶艺廊冷白知性",
        "title_en": "04 · Korea · Samcheong Vinyl Lounge Minimalist Chic",
        "seed": 20268504,
        "prompt": (
            "Candid editorial portrait of an extraordinarily elegant modern Korean woman seated at a minimalist natural oak table in a sunlit art bookstore and vinyl listening lounge in Samcheong-dong, Seoul. "
            "Refined clean Korean facial contours, smooth elegant jawline and slender swan-like neck, calm intellectual dark eyes with direct poised gaze, natural soft rose MLBB hydrated lips. "
            "Flawless cool-tone porcelain glass skin with realistic micro-pores, zero heavy makeup, quiet understated luxury. "
            "Sleek silky dark hair parted in the middle, wearing a tailored minimalist dark charcoal double-breasted coat over a cream silk knit top. "
            "A vintage minimalist turntable spinning a vinyl record on the wooden table beside her, warm sunset rays cutting across the concrete wall in the background, Hasselblad X2D 90mm lens, Vogue Korea editorial style."
        )
    }
]


DAY06_TASKS = [
    {
        "id": "day06_01_china_snow",
        "title_zh": "01 · 中国 · 故宫角楼红墙白雪回眸",
        "title_en": "01 · China · Forbidden City Red Wall Winter Snow",
        "seed": 20268601,
        "prompt": (
            "Authentic cinematic 35mm film photograph of an extraordinarily beautiful young Chinese woman in a gentle winter snowfall beside an ancient red palace wall. "
            "Delicate East Asian classical bone structure, smooth slender neck and graceful jawline, soulful intelligent dark almond eyes with soft snowflakes caught on her eyelashes. "
            "Pristine translucent porcelain jade skin with subtle cold-air rosy flush on cheeks, natural pale rose hydrated lips. "
            "Wearing an elegant long ivory-white double-faced cashmere coat and a thick cream wool scarf tucked around her neck, dark hair dusted with fine snowflakes. "
            "Ancient vermilion palace wall and snow-dusted corner tower in soft out-of-focus background, gentle winter snowflakes drifting in the air, Leica M11 50mm f/1.4 Summilux, cinematic poetry."
        )
    },
    {
        "id": "day06_02_western_audrey_snow",
        "title_zh": "02 · 瑞士 · 阿尔卑斯雪山木屋古典名媛",
        "title_en": "02 · Swiss · Alpine Chalet Balcony Classic Grace",
        "seed": 20268602,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily beautiful young European woman in a snowy alpine setting with the timeless aristocratic elegance of Audrey Hepburn and romantic French allure. "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, radiant natural winter glow. "
            "Aristocratic classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel-brown eyes framed by long dark eyelashes, subtle natural laugh lines with an enchanting graceful smile, natural soft pink hydrated lips. "
            "Silky chestnut brown hair loosely styled with gentle French fringe bangs, delicate crystalline snowflakes melting in her hair. "
            "Wearing an oversized cozy cream-white chunky cable-knit mohair sweater, hands holding a warm steaming white mug. "
            "Rustic wooden alpine chalet balcony and snow-capped pine mountains softly blurred in the bright winter sunlight, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day06_03_japan_otaru_snow",
        "title_zh": "03 · 日本 · 小樽初雪白毛耳罩与纯情",
        "title_en": "03 · Japan · Otaru First Snow & White Earmuffs",
        "seed": 20268603,
        "prompt": (
            "Authentic candid Japanese film portrait of an exquisite young Japanese woman standing in a heavy quiet snowfall in Otaru, Hokkaido. "
            "Petite delicate Japanese features, soft youthful oval face, airy wispy fringe dusted with powdery white snowflakes, big dewy expressive dark eyes looking straight into the lens with tender warmth, natural rosy peach winter lip gloss. "
            "Translucent glowing fair skin with natural chilly winter pink flush on cheeks and nose tip. "
            "Wearing fluffy plush white earmuffs, an oversized classic navy blue wool duffle coat with wooden toggle buttons, and a voluminous cream knitted scarf. "
            "Soft snowy street lamps and falling snow creating gentle white bokeh circles, Fujifilm Pro 400H emulation, nostalgic Japanese winter cinema aesthetic."
        )
    },
    {
        "id": "day06_04_korea_namsan_snow",
        "title_zh": "04 · 韩国 · 首尔南山雪景极简冷白千金",
        "title_en": "04 · Korea · Seoul Namsan Snow & White Cashmere",
        "seed": 20268604,
        "prompt": (
            "Candid editorial portrait of an extraordinarily elegant modern Korean woman standing on a snow-covered pavilion terrace overlooking winter Seoul. "
            "Refined clean Korean facial contours, smooth noble jawline and slender neck, calm poised intellectual dark eyes, immaculate cool-tone porcelain glass skin, natural soft berry-tinted MLBB hydrated lips. "
            "Sleek silky dark hair parted neatly, fine crystalline snow particles resting on her shoulders. "
            "Wearing a tailored minimalist off-white double-breasted wool-cashmere trench coat belted at the waist, quiet luxury styling. "
            "Snow-laden branches and modern Seoul city skyline softly visible through winter mist, shot on Hasselblad X2D 90mm lens, Vogue Korea winter editorial style."
        )
    }
]


def remaster_day05():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day05"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 05: 《文艺黄昏 · 黑胶唱片与复古书店》 (Golden Hour Nostalgia)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY05_TASKS, 1):
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

    grid_zh = day_dir / "day05_vinyl_books_4grid_cn.png"
    grid_en = day_dir / "day05_vinyl_books_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 05 《文艺黄昏 · 黑胶唱片与复古书店》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 暖金夕阳发丝 · 纯天然微孔光泽 · 告别塑料假面",
        main_title_en="Golden Hour Nostalgia · Day 05 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Warm Sunset Glow & Authentic Skin Micro-Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 05 Remaster complete!")


def remaster_day06():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day06"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 06: 《冬日微雪 · 纯白毛领与红墙》 (Winter Snow & Pure White)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY06_TASKS, 1):
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

    grid_zh = day_dir / "day06_winter_snow_4grid_cn.png"
    grid_en = day_dir / "day06_winter_snow_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 06 《冬日微雪 · 纯白毛领与红墙》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 晶莹初雪融发 · 冷感通透玉肌 · 告别塑料假面",
        main_title_en="Winter Snow & Pure Cashmere · Day 06 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Winter Snowfall & Radiant Porcelain Skin · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 06 Remaster complete!")


DAY07_TASKS = [
    {
        "id": "day07_01_china_silk",
        "title_zh": "01 · 中国 · 水榭暮色新中式真丝白月光",
        "title_en": "01 · China · Twilight Lotus Pavilion White Silk",
        "seed": 20268701,
        "prompt": (
            "Authentic candid 35mm film photograph of an extraordinarily stunning young Chinese woman standing by a tranquil lotus pond pavilion at twilight. "
            "Delicate East Asian classical bone structure, smooth slender swan neck and graceful jawline, soulful clear dark almond eyes looking back with quiet breathtaking depth and gentle warmth. "
            "Pristine translucent porcelain jade skin glowing softly in evening dusk, natural soft peach hydrated lips. "
            "Long silky raven hair partially pinned in an elegant loose updo with delicate loose strands dancing in evening lake breeze. "
            "Wearing an exquisite minimalist ivory-white mulberry silk modern qipao dress with subtle water-ripple sheen, flowing gracefully. "
            "Reflective dark water, ancient carved stone balustrade, and soft warm lantern glow in background, Leica M11 50mm f/1.4 Summilux, cinematic poetry."
        )
    },
    {
        "id": "day07_02_western_audrey_sophie",
        "title_zh": "02 · 法国 · 巴黎露台黑丝绒经典神颜",
        "title_en": "02 · France · Parisian Terrace Black Velvet Elegance",
        "seed": 20268702,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Caucasian woman standing on an ornate Parisian mansion stone balcony at dusk, combining the timeless aristocratic elegance of Audrey Hepburn and romantic French allure. "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, luminous natural evening glow. "
            "Exquisite classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel eyes with long natural dark lashes, gentle enigmatic smile with natural rosy lips. "
            "Chestnut brown hair styled in an elegant loose French chignon with soft wispy fringe bangs grazing her brow. "
            "Wearing a timeless minimalist black silk velvet evening dress with delicate thin straps, accentuating her slender collarbone and swan-like neck, single natural baroque pearl pendant. "
            "Parisian skyline, Eiffel Tower silhouette, and soft purple-gold twilight sky blurred in creamy bokeh, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day07_03_japan_akina_ryoko",
        "title_zh": "03 · 日本 · 京都幽竹石灯昭和和风",
        "title_en": "03 · Japan · Kyoto Twilight Bamboo & Indigo Silk",
        "seed": 20268703,
        "prompt": (
            "Authentic candid 35mm Japanese film photograph of an extraordinarily beautiful young Japanese woman capturing nostalgic Showa-era film warmth. "
            "Petite delicate Japanese facial contours, soft oval jawline, slightly tearful dewy expressive dark eyes looking directly into camera with profound tender emotion, natural fresh nude-peach lips. "
            "Translucent glowing fair porcelain skin with subtle evening chill flush on cheeks, zero blemish, natural clear complexion. "
            "Dark silky hair styled in soft vintage wavy layers with airy wispy bangs gently lifted by mountain breeze. "
            "Wearing a refined minimalist indigo-navy silk modern kimono-inspired wrap dress, tied loosely with silk ribbon. "
            "Twilight bamboo grove with soft warm stone lantern glow in background, subtle film grain, Fujifilm Pro 400H aesthetic, iconic Japanese cinema masterpiece."
        )
    },
    {
        "id": "day07_04_korea_song_hye_kyo",
        "title_zh": "04 · 韩国 · 首尔江南露台香槟缎面名媛",
        "title_en": "04 · Korea · Gangnam Skyline Champagne Silk Slip",
        "seed": 20268704,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Korean woman embodying timeless natural beauty. "
            "Refined Korean facial contours, smooth elegant jawline, perfectly proportioned straight high nasal bridge, deep calm intellectual almond eyes filled with captivating charisma, naturally full hydrated soft rose MLBB lips. "
            "Immaculate cool-tone porcelain glass skin, radiant and clear with realistic micro-texture, zero heavy makeup, quiet effortless luxury. "
            "Sleek silky black hair swept smoothly over one shoulder, wearing a tailored minimalist champagne-gold bias-cut liquid silk slip dress that drapes effortlessly. "
            "Modern architectural glass lines, warm interior amber glow, and city night lights sparkling in creamy background bokeh, shot on Hasselblad X2D 90mm lens, Vogue Korea high-fashion editorial style."
        )
    }
]


DAY08_TASKS = [
    {
        "id": "day08_01_china_skyline",
        "title_zh": "01 · 中国 · 外滩天际线露台真丝长裙",
        "title_en": "01 · China · Shanghai Bund Skyline Pearl Silk",
        "seed": 20268801,
        "prompt": (
            "Breathtaking cinematic 35mm film photograph of an extraordinarily stunning young Chinese woman at an open-air rooftop lounge overlooking the Shanghai Bund skyline at twilight. "
            "Delicate East Asian classical bone structure, smooth slender swan neck and graceful collarbone, soulful clear dark almond eyes looking back with quiet breathtaking depth and gentle warmth. "
            "Pristine translucent porcelain jade skin illuminated by warm flickering candle glow and cool city bokeh. "
            "Long silky raven hair blown gracefully by high-altitude river breeze with loose strands dancing in air. "
            "Wearing an elegant modern pearl-white silk halterneck slip dress, holding a slender crystal flute of champagne with gentle bubbles. "
            "Glistening Huangpu River reflections and glowing historic colonial architecture in creamy out-of-focus background, Leica M11 50mm f/1.4 Summilux, cinematic poetry."
        )
    },
    {
        "id": "day08_02_western_rooftop",
        "title_zh": "02 · 法国 · 蒙马特露台塞纳河暮色鸡尾酒",
        "title_en": "02 · France · Montmartre Rooftop Twilight French 75",
        "seed": 20268802,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous European woman seated at an intimate Parisian rooftop terrace bar at dusk. "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, luminous soft candlelight illumination. "
            "Exquisite classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel-brown eyes with long natural dark lashes, gentle enchanting smile. "
            "Chestnut brown wavy hair casually swept into loose French chignon with delicate wispy bangs. "
            "Wearing an off-the-shoulder minimalist black silk top with delicate spaghetti straps, delicate gold pendant, holding a chilled French 75 cocktail glass. "
            "Warm amber candle on small bistro table, purple-navy twilight Paris skyline and distant glowing Eiffel Tower lights softly blurred, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day08_03_japan_roppongi",
        "title_zh": "03 · 日本 · 六本木高空露台东京塔微醺",
        "title_en": "03 · Japan · Roppongi Rooftop Tokyo Tower Highball",
        "seed": 20268803,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily beautiful young Japanese woman leaning gently against the glass balcony of a high-rise Tokyo rooftop lounge. "
            "Petite delicate Japanese facial contours, soft oval jawline, slightly dewy expressive dark eyes looking thoughtfully at viewer with profound tender emotion, natural fresh nude-peach lip gloss. "
            "Translucent glowing fair porcelain skin softly reflecting warm ambient fairy lights, zero blemish, natural clear complexion. "
            "Dark silky shoulder-length hair gently swept by Tokyo night breeze, wearing an elegant midnight-blue silk camisole and draped fine cream cashmere cardigan. "
            "Holding a highball glass with an oversized clear ice sphere, glowing Tokyo Tower warm orange silhouette bokeh in twilight distance, Hasselblad X2D 90mm lens, cinematic Japanese drama atmosphere."
        )
    },
    {
        "id": "day08_04_korea_gangnam",
        "title_zh": "04 · 韩国 · 清潭洞顶层露天汉江晚霞千金",
        "title_en": "04 · Korea · Cheongdam Rooftop Han River Sunset Bellini",
        "seed": 20268804,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily stunning Korean heiress on a high-end rooftop gallery terrace in Cheongdam-dong overlooking sunset over Han River. "
            "Flawless luminous glass skin with exquisite natural dewy hydration, perfectly symmetrical refined feminine jawline, captivating clear dark almond eyes reflecting warm golden sunset, naturally plush hydrated petal-rose lips. "
            "Voluminous glossy dark espresso hair with soft side-swept waves framing high cheekbones. "
            "Wearing an impeccably tailored ivory-cream fine cashmere blazer draped over oyster-silk slip camisole. "
            "Holding a chilled bellini cocktail with a thin peach slice, warm golden hour sun dipping below Seoul skyline, Leica M11 50mm f/1.4 Summilux, Vogue Korea luxury editorial realism."
        )
    },
    {
        "id": "day08_05_mediterranean_amalfi",
        "title_zh": "05 · 意大利 · 阿马尔菲悬崖海景Aperol微风",
        "title_en": "05 · Italy · Amalfi Cliffside Sunset Aperol Spritz",
        "seed": 20268805,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Mediterranean woman on a cliffside terrace in Amalfi at golden sunset. "
            "Flawless smooth porcelain-olive skin glowing in warm golden hour sunset light, completely clear of blemishes or freckles. "
            "Sculpted symmetrical classical bone structure, noble straight nasal bridge, captivating large velvety-brown expressive eyes with natural dark lashes, gentle enchanting smile. "
            "Glossy thick dark brunette wavy hair cascading naturally over bare shoulders in sea breeze. "
            "Wearing a terracotta-orange pure linen slip dress with delicate straps, holding a chilled Aperol spritz in a large crystal goblet with an orange slice. "
            "Rustic stone balustrade, potted lemon trees, and shimmering Tyrrhenian Sea reflecting golden pink sunset clouds, Contax T2 35mm f/2.8 lens, Italian holiday cinema masterpiece."
        )
    },
    {
        "id": "day08_06_slavic_prague",
        "title_zh": "06 · 捷克 · 布拉格金色哥特尖顶香槟暮光",
        "title_en": "06 · Czech · Prague Rooftop Golden Spire Champagne",
        "seed": 20268806,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily beautiful Eastern European woman at an elevated terrace overlooking Prague at golden twilight. "
            "Flawless golden ratio facial symmetry, razor-sharp delicate jawline, noble straight nose, captivating piercing emerald-green almond eyes reflecting golden sunlight, soft hydrated nude-rose lips. "
            "Glossy ash-brown wavy hair gently lifted by evening breeze, falling elegantly over high-neck emerald-green liquid silk blouse. "
            "Holding a slender crystal flute of sparkling white wine, leaning gracefully against antique wrought-iron terrace railing. "
            "Historic red rooftops, Charles Bridge, and glowing spires of Prague bathed in molten golden sunset light, Leica M11 50mm f/1.4 Summilux, timeless European editorial realism."
        )
    }
]


def remaster_day07():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day07"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 07: 《流光真丝 · 月下水榭与法式黑裙》 (Silk Elegance)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY07_TASKS, 1):
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

    grid_zh = day_dir / "day07_silk_elegance_4grid_cn.png"
    grid_en = day_dir / "day07_silk_elegance_4grid_en.png"
    print("\n[*] Assembling Bilingual 4-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 07 《流光真丝 · 月下水榭与法式黑裙》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 缎面流光微澜 · 纯天然凝脂皮相 · 告别塑料假面",
        main_title_en="Silk Elegance & Velvet Twilight · Day 07 Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Liquid Silk Sheen & Natural Skin Micro-Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=2
    )
    print("\n[+] Day 07 Remaster complete!")


def remaster_day08():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day08"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 08: 《暮色微醺 · 天台夜景与鸡尾酒》 (Twilight Cocktails 6-Pack)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY08_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/6] Generating: {title_zh} ...")

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

    grid_zh = day_dir / "day08_twilight_cocktails_6grid_cn.png"
    grid_en = day_dir / "day08_twilight_cocktails_6grid_en.png"
    print("\n[*] Assembling Bilingual 6-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 08 《暮色微醺 · 天台夜景与鸡尾酒》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 城市流光斑斓 · 纯天然毛孔与呼吸感 · 告别塑料假面",
        main_title_en="Twilight Cocktails & Skyline · Day 08 6-Pack Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · City Skyline Bokeh & Real Skin Radiance · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=3
    )
    print("\n[+] Day 08 Remaster complete!")


DAY09_TASKS = [
    {
        "id": "day09_01_china_autumn",
        "title_zh": "01 · 中国 · 古都红墙银杏长廊风衣回眸",
        "title_en": "01 · China · Golden Ginkgo Alley & Camel Trench",
        "seed": 20268901,
        "prompt": (
            "Authentic candid 35mm film photograph of an extraordinarily gorgeous 21-year-old Chinese muse standing by ancient red palace walls surrounded by glowing golden ginkgo trees in autumn. "
            "Exquisite youthful facial contours, smooth soft jawline, high cranial top, delicate slender nose, crystal-clear dark almond eyes with soulful radiant tenderness. "
            "Plump hydrated natural rose lips slightly parted in soft breathing repose, pristine porcelain jade skin glowing with pure youth. "
            "Long silky raven hair flowing in gentle autumn breeze, wearing an elegant tailored camel cashmere trench coat over an ivory silk blouse. "
            "Golden autumn sunlight and drifting yellow ginkgo leaves in creamy background, Leica M11 50mm f/1.4 Summilux, cinematic masterpiece."
        )
    },
    {
        "id": "day09_02_western_autumn",
        "title_zh": "02 · 法国 · 巴黎塞纳河畔林荫风衣绝色",
        "title_en": "02 · France · Seine River Embankment Trench Allure",
        "seed": 20268902,
        "prompt": (
            "Breathtaking candid 35mm film portrait of an extraordinarily gorgeous 21-year-old French European beauty standing along the Seine in Paris in autumn. "
            "Flawless youthful feminine facial proportions, soft rounded chin, delicate straight slender nose, captivating large sparkling hazel-green doe eyes with natural dark lashes. "
            "Plump soft rosy-peach lips with subtle natural tenderness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Lush wavy honey-brown hair tossed effortlessly by breeze, wearing a tailored honey-tan gabardine trench coat over a soft knit. "
            "Golden chestnut leaves drifting over stone embankment, creamy vintage Parisian autumn bokeh, Contax T2 35mm f/2.8 lens, legendary French cinema beauty."
        )
    },
    {
        "id": "day09_03_japan_autumn",
        "title_zh": "03 · 日本 · 京都岚山古寺红枫石阶初恋",
        "title_en": "03 · Japan · Kyoto Arashiyama Scarlet Maples & Wool Coat",
        "seed": 20268903,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily stunning 20-year-old Japanese young beauty on stone steps in Kyoto beneath scarlet autumn maples. "
            "Dainty delicate feminine face, soft smooth jawline, large clear dewy dark expressive eyes filled with innocent sweet charm, petite straight nose. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with youthful blush, zero blemish. "
            "Dark silky hair with soft wispy bangs, wearing an oatmeal-cream wool coat, holding a warm wooden cup of roasted green tea with both hands. "
            "Mossy stone lanterns and vibrant red maple leaves in soft golden autumn mist, Hasselblad X2D 90mm lens, cinematic Japanese youth drama perfection."
        )
    },
    {
        "id": "day09_04_korea_autumn",
        "title_zh": "04 · 韩国 · 首尔三清洞古石墙路水光千金",
        "title_en": "04 · Korea · Samcheong Stone Wall Cream Cashmere",
        "seed": 20268904,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily beautiful 21-year-old Korean heiress walking along Samcheong-dong stone wall in autumn. "
            "Softly contoured oval face, full youthful cheeks without any hollows, delicate dainty straight nose, captivating dark almond eyes with gentle clear warmth. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing in autumn sunlight. "
            "Voluminous glossy dark espresso hair with soft side-swept waves, wearing a tailored cream-white double-faced cashmere coat with wide lapels. "
            "Golden ginkgo leaves and ancient stone wall in warm golden hour glow, Leica M11 50mm f/1.4 Summilux, Vogue Korea luxury realism."
        )
    },
    {
        "id": "day09_05_mediterranean_autumn",
        "title_zh": "05 · 意大利 · 托斯卡纳金秋柏树道明艳少女",
        "title_en": "05 · Italy · Tuscany Cypress Sunset Olive Trench",
        "seed": 20268905,
        "prompt": (
            "Breathtaking cinematic 35mm film portrait of an extraordinarily gorgeous 21-year-old Italian Mediterranean youthful goddess in Tuscany at golden autumn sunset. "
            "Delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes with long naturally lush lashes and warm radiant sparkle. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in warm sunset breeze. "
            "Wearing an olive-green belted wool trench coat, holding a small wicker basket of purple figs. "
            "Golden rolling Tuscan hills and tall cypress trees bathed in warm amber backlight, Contax T2 35mm f/2.8 lens, Italian romantic cinema masterpiece."
        )
    },
    {
        "id": "day09_06_slavic_autumn",
        "title_zh": "06 · 奥地利 · 维也纳美泉宫深林风衣芭比",
        "title_en": "06 · Austria · Vienna Schönbrunn Forest Green Trench",
        "seed": 20268906,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily stunning 20-year-old Slavic Eastern European doll-like beauty in Vienna in autumn. "
            "Soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes filled with youthful sparkle and gentle warmth. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair blowing softly in autumn wind. "
            "Wearing a tailored deep forest-green wool trench coat with dark buttons. "
            "Golden cathedral canopy of Schönbrunn autumn trees and historic palace statues in soft golden bokeh, Leica M11 50mm f/1.4 Summilux, European fairy-tale realism."
        )
    }
]


def remaster_day09():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day09"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 09: 《秋风微凉 · 经典风衣与金秋落叶》 (Autumn Trench 6-Pack)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY09_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/6] Generating: {title_zh} ...")

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

    grid_zh = day_dir / "day09_autumn_trench_6grid_cn.png"
    grid_en = day_dir / "day09_autumn_trench_6grid_en.png"
    print("\n[*] Assembling Bilingual 6-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 09 《秋风微凉 · 经典风衣与金秋落叶》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 经典风衣面料质感 · 纯天然微孔光泽 · 告别塑料假面",
        main_title_en="Autumn Trench & Golden Foliage · Day 09 6-Pack Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Classic Wool Trench & Authentic Skin Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=3
    )
    print("\n[+] Day 09 Remaster complete!")


DAY10_TASKS = [
    {
        "id": "day10_01_china_editorial",
        "title_zh": "01 · 中国 · 时尚大片影棚重磅真丝晚装",
        "title_en": "01 · China · Studio Couture Mulberry Silk Halter Gown",
        "seed": 20261001,
        "prompt": (
            "Authentic high-fashion Vogue magazine cover portrait of an extraordinarily gorgeous 21-year-old Chinese muse. "
            "Exquisite youthful facial contours, delicate slender swan neck, high cranial top, slender straight nose, captivating dark almond eyes with quiet soulful tenderness and crystal-clear catchlights. "
            "Naturally plump hydrated soft petal-rose lips slightly parted in relaxed breathing repose, pristine porcelain jade skin glowing from within with pure youth. "
            "Sleek silky black hair gathered in an elegant loose couture chignon with delicate wispy strands framing her face. "
            "Wearing an architectural ivory-white heavy mulberry silk halter gown with liquid drape, minimalist diamond ear studs. "
            "Soft luxury beauty dish studio lighting casting gentle sculpted shadows, dark minimalist background, Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece."
        )
    },
    {
        "id": "day10_02_western_editorial",
        "title_zh": "02 · 法国 · 巴黎高定沙龙黑丝绒抹胸裙",
        "title_en": "02 · France · Parisian Couture Salon Black Velvet Corset",
        "seed": 20261002,
        "prompt": (
            "Breathtaking high-fashion editorial portrait of an extraordinarily stunning 21-year-old French muse in a Parisian couture salon. "
            "Perfect feminine youthful facial proportions, soft rounded chin, slender straight nose, captivating large sparkling hazel-green doe eyes with natural lush dark lashes looking directly into the lens. "
            "Plump soft rosy-peach hydrated lips with subtle natural sweetness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Voluminous wavy honey-brown hair falling casually over one shoulder, wearing an off-the-shoulder minimalist black velvet corset dress with ivory silk organza trim. "
            "Soft directional Rembrandt window light from Parisian floor-to-ceiling balcony, creamy neutral studio background, Leica M11 50mm f/1.4 Summilux, timeless European cinema glamour."
        )
    },
    {
        "id": "day10_03_japan_editorial",
        "title_zh": "03 · 日本 · 自然光艺术影棚粉彩羊绒与白牡丹",
        "title_en": "03 · Japan · Tokyo Daylight Studio Blush Cashmere & Peony",
        "seed": 20261003,
        "prompt": (
            "Breathtaking high-fashion Japanese magazine cover photograph of an extraordinarily gorgeous 20-year-old Japanese youthful beauty. "
            "Dainty delicate feminine face, soft smooth jawline, large clear dewy dark expressive eyes filled with innocent sweet charm, petite straight nose. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with natural youthful blush, completely smooth and clear. "
            "Dark silky hair with soft air bangs, wearing a soft blush-pink fine cashmere knit and draped sheer silk scarf, holding a delicate white peony bloom near her cheek. "
            "Soft diffused Japanese natural daylight, creamy warm pastel studio background, Hasselblad X2D 90mm lens, iconic Japanese beauty magazine perfection."
        )
    },
    {
        "id": "day10_04_korea_editorial",
        "title_zh": "04 · 韩国 · 清潭洞高定艺廊香槟液体真丝",
        "title_en": "04 · Korea · Cheongdam Gallery Champagne Liquid Silk Blazer",
        "seed": 20261004,
        "prompt": (
            "Breathtaking high-fashion Vogue Korea editorial photograph of an extraordinarily stunning 21-year-old Korean heiress. "
            "Impeccably proportioned soft oval face, full youthful cheeks without any hollows, delicate dainty straight nose, captivating clear dark almond eyes radiating calm aristocratic warmth. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing with pure luxury hydration. "
            "Voluminous glossy dark espresso hair with soft side-swept waves, wearing a tailored champagne-gold liquid silk satin blazer dress, minimalist diamond tennis choker. "
            "Soft luxury key lighting with delicate silver fill, warm architectural gallery background, Leica M11 50mm f/1.4 Summilux, luxury Korean fashion editorial."
        )
    },
    {
        "id": "day10_05_mediterranean_editorial",
        "title_zh": "05 · 意大利 · 罗马古堡暖阳露台祖母绿真丝",
        "title_en": "05 · Italy · Roman Villa Terrace Emerald Green Silk",
        "seed": 20261005,
        "prompt": (
            "Breathtaking high-fashion editorial portrait of an extraordinarily gorgeous 21-year-old Italian Mediterranean youthful goddess. "
            "Delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes with long naturally lush lashes and warm radiant sparkle. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in warm Italian afternoon light. "
            "Wearing an emerald-green liquid silk slip dress with delicate gold jewelry. "
            "Warm golden rim lighting, antique Roman marble architecture softly blurred in background, Contax T2 35mm f/2.8 lens, Dolce & Gabbana luxury editorial masterpiece."
        )
    },
    {
        "id": "day10_06_slavic_editorial",
        "title_zh": "06 · 奥地利 · 维也纳古典沙龙午夜蓝缎面抹胸",
        "title_en": "06 · Austria · Vienna Classical Salon Midnight Navy Satin",
        "seed": 20261006,
        "prompt": (
            "Breathtaking high-fashion magazine cover portrait of an extraordinarily stunning 20-year-old Slavic Eastern European doll-like beauty. "
            "Soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes filled with youthful sparkle and gentle warmth. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair styled with soft natural movement over bare shoulders. "
            "Wearing a midnight-navy blue liquid satin off-the-shoulder gown, delicate diamond drop earrings. "
            "Soft flattering studio glamour lighting, classical dark baroque backdrop with subtle warm gold accents, Leica M11 50mm f/1.4 Summilux, European haute couture perfection."
        )
    }
]


DAY11_TASKS = [
    {
        "id": "day11_01_china_campus",
        "title_zh": "01 · 中国 · 百年图书馆红木窗边清冷校花",
        "title_en": "01 · China · Historic Library Mahogany Window Collegiate Muse",
        "seed": 91820101,
        "prompt": (
            "Authentic Vogue magazine cover bust portrait of an extraordinarily gorgeous 20-year-old Chinese university student. "
            "Large detailed facial framing, perfect golden ratio facial symmetry, delicate slender swan neck, high cranial top, slender straight nose bridge. "
            "Soulful clear dark almond eyes looking directly into the camera with crystal-clear catchlights and quiet intelligent tenderness. "
            "Naturally plump hydrated soft petal-rose lips slightly parted in relaxed breathing repose, pristine porcelain jade skin glowing from within with pure youth. "
            "Silky dark raven hair falling over her shoulders, wearing a crisp white collared cotton shirt under a classic navy-blue fine wool collegiate vest with neat collar. "
            "Warm golden afternoon sunlight streaming from tall library windows, soft blurred mahogany bookshelves in warm cinematic bokeh, Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece."
        )
    },
    {
        "id": "day11_02_western_campus",
        "title_zh": "02 · 英国 · 剑桥古老石柱回廊英伦羊绒",
        "title_en": "02 · UK · Cambridge Gothic Cloister Cream Cashmere Knit",
        "seed": 82739202,
        "prompt": (
            "Breathtaking high-fashion magazine cover portrait of an extraordinarily stunning 20-year-old European university student in an Oxford or Cambridge cloister. "
            "Large detailed bust portrait framing, perfect feminine youthful facial proportions, soft rounded chin, slender straight nose, captivating large sparkling hazel-green doe eyes looking straight into the lens with natural dark lashes and brilliant catchlights. "
            "Plump soft rosy-peach hydrated lips with natural sweetness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Lush wavy honey-brown hair framing her graceful face in cool English breeze. "
            "Wearing an oversized chunky-knit cream cashmere sweater with soft ribbed crewneck over a crisp collared shirt. "
            "Gothic stone archway softly blurred in creamy golden hour background, Leica M11 50mm f/1.4 Summilux, legendary European academic beauty."
        )
    },
    {
        "id": "day11_03_japan_campus",
        "title_zh": "03 · 日本 · 早稻田红砖拱门纯氧文学少女",
        "title_en": "03 · Japan · Waseda Red Brick Archway Oatmeal Knit Cardigan",
        "seed": 73628303,
        "prompt": (
            "Breathtaking Japanese beauty magazine cover portrait of an extraordinarily gorgeous 19-year-old Japanese university student. "
            "Detailed close-up bust portrait framing, dainty delicate feminine facial structure, perfectly symmetrical smooth jawline, large clear dewy dark expressive eyes gazing directly at viewer with bright clear catchlights and innocent sweet charm. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with natural youthful pink blush, completely smooth and clear. "
            "Dark silky hair with soft air bangs, wearing a soft pale oatmeal-cream knit cardigan with a neat round collar. "
            "Warm morning natural daylight, soft red-brick university archway and golden ginkgo foliage in creamy bokeh, Hasselblad X2D 90mm lens, iconic Japanese campus youth aesthetic."
        )
    },
    {
        "id": "day11_04_korea_campus",
        "title_zh": "04 · 韩国 · 延世常春藤古建筑西装名媛",
        "title_en": "04 · Korea · Yonsei Ivy Hall Preppy Wool Blazer",
        "seed": 64519404,
        "prompt": (
            "Breathtaking Vogue Korea magazine cover bust portrait of an extraordinarily beautiful 20-year-old Korean top-university heiress. "
            "Prominent detailed facial framing, impeccably proportioned soft oval face, full youthful cheeks without any hollows, delicate straight dainty nose, captivating clear dark almond eyes looking straight at camera with calm aristocratic intelligence. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing with pure luxury hydration. "
            "Voluminous glossy dark espresso hair styled in elegant soft waves, wearing a tailored charcoal-grey wool preppy blazer with neat lapels over an ivory silk mock-neck top. "
            "Historic ivy-covered stone collegiate building and warm autumn sunlight, Leica M11 50mm f/1.4 Summilux, luxury Korean collegiate realism."
        )
    },
    {
        "id": "day11_05_mediterranean_campus",
        "title_zh": "05 · 意大利 · 博洛尼亚古拱廊橄榄绿知性校花",
        "title_en": "05 · Italy · Bologna Ancient Portico Olive Wool Blazer",
        "seed": 55428505,
        "prompt": (
            "Breathtaking Italian Vogue magazine cover portrait of an extraordinarily gorgeous 20-year-old Italian university student in Bologna. "
            "Prominent bust portrait framing, delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes looking directly into camera with long naturally lush lashes and warm radiant catchlights. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in warm Italian afternoon sun. "
            "Wearing a tailored olive-green wool blazer over an ivory silk top with clean neckline. "
            "Ancient arched stone porticoes and sunlit cobblestone courtyard in creamy background, Contax T2 35mm f/2.8 lens, Italian academic cinema masterwork."
        )
    },
    {
        "id": "day11_06_ivy_campus",
        "title_zh": "06 · 美国 · 耶鲁哥特式回廊深蓝常春藤学霸",
        "title_en": "06 · USA · Yale Gothic Cloister Navy Ivy League Crewneck",
        "seed": 46317606,
        "prompt": (
            "Breathtaking Harper's Bazaar cover portrait of an extraordinarily stunning 20-year-old Ivy League student at Yale University. "
            "Detailed close-up bust portrait framing, soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes looking directly into the lens with youthful sparkle and intellectual brilliance. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair styled naturally over her shoulders, wearing a classic deep navy-blue collegiate crewneck sweater with neat white collared shirt underneath. "
            "Majestic Gothic stone arches of Yale University and warm autumn sunlight in soft creamy bokeh, Leica M11 50mm f/1.4 Summilux, Ivy League collegiate perfection."
        )
    }
]


DAY12_TASKS = [
    {
        "id": "day12_01_china_cinema",
        "title_zh": "01 · 中国 · 王家卫式雨夜弄堂拱门回眸",
        "title_en": "01 · China · Wong Kar-wai Rainy Alley Emerald Silk Qipao",
        "seed": 20261221,
        "prompt": (
            "Award-winning cinematic 35mm film still of an extraordinarily gorgeous 21-year-old Chinese leading actress walking in a 1960s vintage Shanghai alleyway. "
            "Dynamic over-the-shoulder three-quarter angle, walking under an ancient brick archway creating natural architectural sub-framing. "
            "Delicately holding a dark oiled bamboo umbrella in one slender hand, showing slender waist and graceful posture. "
            "Sparkling dark almond eyes filled with warm lively intelligence, sweet captivating gentle smile with upturned lip corners, relaxed open brow. "
            "Wearing a tailored high-neck emerald-green liquid silk jacquard qipao. "
            "Rain-slicked cobblestone street, soft amber streetlamp backlighting casting a golden rim on her hair, wet asphalt reflections, 50mm anamorphic lens, breathtaking cinematic depth."
        )
    },
    {
        "id": "day12_02_western_cinema",
        "title_zh": "02 · 摩纳哥 · 蒙特卡洛赌场香槟吧台法式邦女郎",
        "title_en": "02 · Monaco · Monte Carlo Casino Lounge Black Velvet Gown",
        "seed": 20261222,
        "prompt": (
            "Breathtaking 35mm Panavision anamorphic film still of a stunning 21-year-old European Bond Girl in a luxurious Monte Carlo casino lounge. "
            "Casually leaning at a 45-degree angle against a polished marble bar counter, rule of thirds composition with negative space. "
            "Slender fingers elegantly holding the stem of a crystal champagne flute, body turned sideways showing sculpted waist and bare back silhouette. "
            "Large sparkling hazel doe eyes looking with playful alluring confidence, radiant blooming smile full of warmth and effortless charisma. "
            "Voluminous wavy honey-brown hair spilling luxuriously over one bare shoulder. "
            "Wearing a backless midnight-black silk velvet cocktail gown. "
            "Foreground soft crystal glass bokeh, warm golden chandeliers and opulent casino salon blurred in creamy background, 55mm lens, blockbuster cinema masterpiece."
        )
    },
    {
        "id": "day12_03_japan_cinema",
        "title_zh": "03 · 日本 · 岩井俊二沿海列车木窗托腮看海",
        "title_en": "03 · Japan · Shunji Iwai Seaside Train Wooden Window Candid",
        "seed": 20261223,
        "prompt": (
            "Award-winning 35mm Japanese cinematic film still of an adorable 20-year-old Japanese leading actress inside a vintage wooden seaside train carriage. "
            "Framed naturally inside open wooden train window, seated sideways at a three-quarter angle. "
            "One elbow resting casually on wooden windowsill, chin resting gently on palm in a natural candid gesture, looking joyfully toward ocean breeze. "
            "Large sparkling dark doe eyes shining with youthful happiness, sweet blooming smile with cute dimples, glowing porcelain skin with soft petal blush. "
            "Silky dark bob with soft bangs dancing in coastal breeze. "
            "Wearing an oversized crisp white linen button-down shirt loosely tucked into high-waist vintage blue jeans. "
            "Sunlit turquoise Pacific Ocean waves and coastal greenery sparkling through window in warm afternoon light, 50mm f/1.4 lens, iconic Japanese cinema poetry."
        )
    },
    {
        "id": "day12_04_korea_cinema",
        "title_zh": "04 · 韩国 · 现代豪宅露台凭栏看夜景水光千金",
        "title_en": "04 · Korea · Penthouse Terrace Champagne Silk Satin Gown",
        "seed": 20261224,
        "prompt": (
            "Cinematic 35mm film still of a gorgeous 21-year-old Korean cinema actress in a high-end luxury mystery drama. "
            "Leaning lightly against glass and steel balustrade of a penthouse terrace overlooking city nightscape, rule of thirds diagonal pose. "
            "Holding a minimalist ceramic warm coffee cup with both hands on railing, body turned sideways at 35 degrees, showing slender hourglass waist. "
            "Clear sparkling dark almond eyes looking calmly into glittering night sky with intelligent poise, subtle elegant smile, luminous glass skin glowing under terrace ambient lights. "
            "Glossy espresso hair flowing down over one shoulder, wearing a bespoke champagne-ivory silk satin wrap gown with a cinched belt. "
            "Panoramic city lights shimmering in cool cyan and warm amber bokeh behind glass, Leica M11 50mm Summilux lens, prestige cinema realism."
        )
    },
    {
        "id": "day12_05_mediterranean_cinema",
        "title_zh": "05 · 意大利 · 西西里托斯卡纳石阶回廊提果篮",
        "title_en": "05 · Italy · Sicilian Stone Staircase Terracotta Linen Sundress",
        "seed": 20261225,
        "prompt": (
            "Award-winning 35mm cinematic film still of a stunning 21-year-old Italian leading actress in a Mediterranean romantic masterpiece. "
            "Descending an ancient sun-drenched limestone staircase framed by arched Roman pillars, turning back gracefully toward warm golden sunlight with dynamic body curvature. "
            "One hand carrying a rustic woven wicker basket of fresh purple figs, other hand lightly touching terracotta linen dress, slender waist and sunkissed collarbones. "
            "Large velvety-dark hazel eyes sparkling with vibrant zest, wide radiant joyful smile full of lively Mediterranean warmth. "
            "Bouncy dark chocolate curls dancing in sea wind, wearing a fitted terracotta-red fine linen sundress with a sweetheart neckline. "
            "Ancient stone architecture, shimmering turquoise Mediterranean Sea and olive groves in golden hour glow, Contax 50mm f/1.4 lens, Italian auteur cinema romance."
        )
    },
    {
        "id": "day12_06_scifi_cinema",
        "title_zh": "06 · 欧美 · 银翼沙石赛博天台翡翠猫眼女英雄",
        "title_en": "06 · Sci-Fi · Cyber Sky-Terrace Black Leather Jacket & Emerald Eyes",
        "seed": 20261226,
        "prompt": (
            "Breathtaking 65mm IMAX cinematic film still of a striking 20-year-old sci-fi epic heroine on an aerial skyscraper terrace in a futuristic city. "
            "Leaning casually back against a luminous metallic sky-terrace barrier, dynamic diagonal silhouette, rule of thirds placement. "
            "One hand resting casually in pocket of tailored cropped black leather jacket, other hand resting on railing, revealing toned slender waist. "
            "Hypnotic clear bright emerald-green almond eyes looking with keen vibrant intellect, subtle confident playful smirk, flawless porcelain milk skin glistening with atmospheric rain mist. "
            "Silky ash-blonde hair with wispy strands framing her cheekbones. "
            "Futuristic neon skyscrapers, airborne vehicle light trails, and misty holographic cyan and amber anamorphic bokeh in vast background, ARRI Alexa 65 50mm lens, IMAX sci-fi blockbuster masterwork."
        )
    }
]


def remaster_day10():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day10"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 10: 《芳华初绽 · 高定时尚杂志大片》 (In Full Bloom 6-Pack)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY10_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/6] Generating: {title_zh} ...")

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

    grid_zh = day_dir / "day10_in_full_bloom_6grid_cn.png"
    grid_en = day_dir / "day10_in_full_bloom_6grid_en.png"
    print("\n[*] Assembling Bilingual 6-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 10 《芳华初绽 · 高定时尚杂志大片》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 高定面料剪裁 · 纯天然毛孔透气感 · 告别塑料假面",
        main_title_en="In Full Bloom Editorial · Day 10 6-Pack Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · High-Fashion Textures & Natural Skin Radiance · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=3
    )
    print("\n[+] Day 10 Remaster complete!")


def remaster_day11():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day11"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 11: 《象牙塔晨光 · 名校校花特写神颜》 (Campus Reverie Muses 6-Pack)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY11_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/6] Generating: {title_zh} ...")

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

    grid_zh = day_dir / "day11_campus_muses_6grid_cn.png"
    grid_en = day_dir / "day11_campus_muses_6grid_en.png"
    print("\n[*] Assembling Bilingual 6-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 11 《象牙塔晨光 · 名校校花特写神颜》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 学院知性风骨 · 纯天然微孔光泽 · 告别塑料假面",
        main_title_en="Campus Reverie Muses · Day 11 6-Pack Showcase (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Collegiate Intellectual Elegance & Real Skin Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=3
    )
    print("\n[+] Day 11 Remaster complete!")


def remaster_day12():
    day_dir = OUTPUT_ROOT / "experiments" / "global_beauties_day12"
    remaster_dir = day_dir / "remaster_z_image"
    remaster_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" Remastering Day 12: 《光影造梦 · 殿堂级电影神颜大片》 (Cinema Muses 6-Pack)")
    print(" Engine: Z-Image Turbo 6B (Native Zero-LoRA) | Dual-Language Boards")
    print(f" Output: {remaster_dir}")
    print("=" * 70)

    generated = []
    titles_zh = []
    titles_en = []

    for idx, item in enumerate(DAY12_TASKS, 1):
        task_id = item["id"]
        title_zh = item["title_zh"]
        title_en = item["title_en"]
        prompt = sanitize_prompt(item["prompt"])
        seed = item["seed"]

        titles_zh.append(title_zh)
        titles_en.append(title_en)

        out_img = remaster_dir / f"{task_id}.png"
        print(f"\n[{idx}/6] Generating: {title_zh} ...")

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

    grid_zh = day_dir / "day12_cinema_muses_6grid_cn.png"
    grid_en = day_dir / "day12_cinema_muses_6grid_en.png"
    print("\n[*] Assembling Bilingual 6-Grid boards...")
    build_bilingual_grid(
        image_paths=generated,
        titles_zh=titles_zh,
        titles_en=titles_en,
        main_title_zh="象牙塔晨光 · Day 12 《光影造梦 · 殿堂级电影神颜大片》 (全新Z-Image 6B重制版)",
        sub_title_zh="标准：100% 零 LoRA 裸跑直出 · 殿堂级电影摄影构图与光影 · 告别塑料假面",
        main_title_en="Cinema Muses Showcase · Day 12 6-Pack (Z-Image Turbo 6B Remaster)",
        sub_title_en="Standard: 100% Native Zero-LoRA · Master Cinematic Lighting & Pure Skin Texture · Zero Plastic",
        output_path_zh=grid_zh,
        output_path_en=grid_en,
        cols=2,
        rows=3
    )
    print("\n[+] Day 12 Remaster complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="02", help="Day collection to remaster")
    args = parser.parse_args()

    if args.day == "02":
        remaster_day02()
    elif args.day == "03":
        remaster_day03()
    elif args.day == "04":
        remaster_day04()
    elif args.day == "05":
        remaster_day05()
    elif args.day == "06":
        remaster_day06()
    elif args.day == "07":
        remaster_day07()
    elif args.day == "08":
        remaster_day08()
    elif args.day == "09":
        remaster_day09()
    elif args.day == "10":
        remaster_day10()
    elif args.day == "11":
        remaster_day11()
    elif args.day == "12":
        remaster_day12()
    elif args.day == "all":
        remaster_day02()
        remaster_day03()
        remaster_day04()
        remaster_day05()
        remaster_day06()
        remaster_day07()
        remaster_day08()
        remaster_day09()
        remaster_day10()
        remaster_day11()
        remaster_day12()
    else:
        print(f"Day {args.day} queue ready.")
