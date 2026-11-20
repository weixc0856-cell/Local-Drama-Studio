#!/usr/bin/env python3
"""
scripts/rerun_douyin_master_suite.py
Complete Douyin Remaster Suite: 100% Native Z-Image Turbo 6B (Zero LoRA).
Generates 9 pristine vertical (9:16 / 768x1360) portraits across iconic global settings.
Assembles 3x3 9-Grid and 2x3 6-Grid showcase boards for Douyin / Xiaohongshu.
"""

import os
import sys
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.produce import produce_z_image_turbo

OUTPUT_ROOT = Path(os.environ.get("DRAMA_OUTPUT_ROOT", str(REPO_ROOT / "studio_data")))
DELIVER_DIR = OUTPUT_ROOT / "deliver" / "douyin_remaster_z_image"
DELIVER_DIR.mkdir(parents=True, exist_ok=True)

WINDIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
FONT_ZH_BOLD = str(WINDIR / "msyhbd.ttc")
FONT_ZH_REG = str(WINDIR / "msyh.ttc")

DOUYIN_SEQUENCE = [
    {
        "id": "01_shanghai_autumn_candid",
        "title": "01 · 中国上海 · 巨鹿路金秋漫步",
        "subtitle": "20岁文艺白月光 · 捧热咖啡侧身回眸",
        "seed": 20268101,
        "prompt": (
            "Cinematic candid 35mm street photograph of a serene 20-year-old Chinese woman walking down Shanghai Julu Road in late golden autumn. "
            "Master environmental walking framing: Walking along a sidewalk covered in golden plane tree leaves, turning her body gently back over her shoulder at a 35-degree angle. "
            "Holding a takeaway paper cup of warm latte naturally with both hands. "
            "Pristine East Asian bone structure, quiet soulful dark almond eyes with gentle warmth, naturally blooming rose lips in soft calm breathing repose, authentic translucent porcelain skin with realistic fine micro-pores and zero fake makeup. "
            "Silky dark raven hair drifting gently across her cheek in the breeze, wearing an oversized cream-beige soft cashmere knit sweater. "
            "Historic brick villa facades and warm golden autumn afternoon sunlight filtering through tree canopy with creamy optical bokeh, Leica M11 50mm f/1.4 Summilux lens, timeless Wong Kar-wai documentary realism."
        )
    },
    {
        "id": "02_beida_campus_muse",
        "title": "02 · 名校未名 · 象牙塔晨光校花",
        "subtitle": "20岁中文系学霸 · 抱书回眸纯天然神颜",
        "seed": 20268102,
        "prompt": (
            "Award-winning candid 35mm photograph of an extraordinarily gorgeous 20-year-old Chinese university literature student walking along a golden autumn campus avenue. "
            "Master environmental portrait composition: Walking along a brick-lined campus pathway under golden falling ginkgo leaves, turning back over her shoulder at a 35-degree three-quarter angle. "
            "Holding two thick hardcover textbooks against her chest with both arms in a natural student posture. "
            "Delicate symmetrical oval face, smooth brow, clear dark almond eyes filled with gentle intelligence, naturally plump rose lips slightly parted in soft calm breathing repose, realistic fine skin pores and natural collagen warmth, zero plastic doll look. "
            "Silky dark hair with soft wispy bangs dancing in gentle autumn breeze, wearing an oversized cream-white cable knit wool sweater and dark pleated skirt. "
            "Red brick collegiate buildings and glowing yellow ginkgo trees in soft morning sunlight, Leica M11 50mm Summilux lens, campus youth documentary masterpiece."
        )
    },
    {
        "id": "03_kamakura_sea_breeze",
        "title": "03 · 日本镰仓 · 青春海风电车道口",
        "subtitle": "20岁日系清爽初恋 · 帆布包回眸展颜甜笑",
        "seed": 20268103,
        "prompt": (
            "Authentic candid 35mm Japanese film photograph of an extraordinarily charming 20-year-old Japanese young beauty walking along the Pacific coastal road in Kamakura. "
            "Subject in relaxed mid-stride on the coastal sidewalk, holding a single canvas tote bag strap, turning back over her shoulder with an effortless candid sweet smile. "
            "Soft dainty jawline, crystal-clear dark doe eyes with sparkling catchlights, silky dark bob hair with wispy air bangs fluttering in ocean breeze. "
            "Wearing a clean white linen short-sleeved collared shirt and pleated navy skirt. "
            "Emerald-blue Pacific ocean waves crashing gently on the left, railway crossing barrier in distance, warm sparkling Pacific summer sunlight, authentic Fujifilm Pro 400H ocean palette, iconic Japanese youth cinema masterpiece."
        )
    },
    {
        "id": "04_tokyo_shibuya_rain",
        "title": "04 · 日本东京 · 涩谷雨夜透明伞",
        "subtitle": "霓虹倒影下的清透回眸 · 发丝与雨丝微动",
        "seed": 20268104,
        "prompt": (
            "Authentic candid 35mm street photograph of an extraordinarily adorable 20-year-old Japanese young beauty standing under a translucent clear umbrella on a rainy evening in Tokyo Shibuya. "
            "Looking softly into the camera with clear gentle catchlights in large dark eyes, relaxed lips in natural calm breathing repose, delicate Japanese bone structure, pristine fair skin glowing under neon street reflections. "
            "Single hand holding the clear umbrella handle, soft dark bob hair with wispy air bangs damp from mist, wearing a classic beige oversized trench coat over a high-neck dark sweater. "
            "Cool neon cyan and magenta city lights blending with warm street ramen lantern glow in deep wet asphalt reflections, rich film noir cinematic depth of field."
        )
    },
    {
        "id": "05_seoul_hanriver_bluehour",
        "title": "05 · 韩国首尔 · 汉江冷调蓝调黄昏",
        "subtitle": "21岁高智感御姐 · 极简大衣随性江风侧颜",
        "seed": 20268105,
        "prompt": (
            "Master candid 35mm fashion documentary photograph of a striking 21-year-old Korean woman standing by the Han River promenade in Seoul during twilight blue hour. "
            "Master three-quarter profile framing: Looking thoughtfully towards city bridge lights across the river, clean sculpted Korean jawline, cool clear eyes, natural hydrated soft lips in calm repose, authentic clean radiant skin texture. "
            "Dark long straight hair fluttering in river breeze, wearing a structured minimalist charcoal wool long trench coat with hands in pockets. "
            "Seoul skyline bridge lights glowing across mist over the river, cool blue hour atmospheric lighting, Contax T2 35mm prime lens cinema tone."
        )
    },
    {
        "id": "06_oxford_radcliffe_morning",
        "title": "06 · 英国牛津 · 古老图书馆石窗晨光",
        "subtitle": "20岁古典文学女神 · 靠窗捧书浅笑与羊绒",
        "seed": 20268106,
        "prompt": (
            "Breathtaking 35mm natural light photograph of a stunning 20-year-old British university student sitting on a deep stone arched window ledge inside Oxford Radcliffe Camera library. "
            "Leaning back gently against the medieval honey-colored stone wall, holding a vintage leather-bound poetry book resting lightly on her lap, gazing out the stone window with serene poetic warmth. "
            "High aristocratic English cheekbones, sparkling pale hazel-green eyes with morning sunlight catchlights, natural soft rose lips, dewy fair porcelain skin with fine natural pores and zero heavy makeup. "
            "Tousled dark honey-brown wavy hair loosely tied in a low chignon with loose tendrils framing her collarbones. "
            "Wearing an oversized heather-grey ribbed cashmere turtleneck sweater and charcoal pleated wool trousers. "
            "Shafts of golden morning sunlight cutting through dusty medieval leaded glass windows, Leica M11 50mm f/1.4 lens documentary realism."
        )
    },
    {
        "id": "07_paris_leftbank_cafe",
        "title": "07 · 法国巴黎 · 左岸圣日耳曼露天小馆",
        "subtitle": "法式慵懒少女 · 单手托腮与复古牛津衬衫",
        "seed": 20268107,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 21-year-old French woman sitting at an outdoor Parisian sidewalk bistro in Saint-Germain. "
            "Leaning sideways at a 45-degree angle against a small round green marble bistro table, chin resting casually on one palm, fingers softly curled. "
            "Captivating large sparkling grey-green doe eyes gazing with warm relaxed curiosity, a subtle tender blooming smile with relaxed lips, smooth blemish-free porcelain skin with authentic micro-pores. "
            "Tousled wavy honey-blonde hair catching warm afternoon rim light, wearing an unbuttoned vintage light-blue soft denim shirt with sleeves rolled to the elbows. "
            "Woven rattan green bistro chairs and historic Haussmannian stone facade in golden afternoon sunlight, Contax T2 35mm f/2.8 lens, legendary French cinema documentary."
        )
    },
    {
        "id": "08_sicily_velvet_siren",
        "title": "08 · 意式西西里 · 烛光黑丝绒名伶",
        "subtitle": "莫妮卡式复古神颜 · 烛光暗影与微卷发丝",
        "seed": 20268108,
        "prompt": (
            "Sensational candid 35mm editorial portrait of a stunning 22-year-old Mediterranean Italian beauty embodying the timeless sultry allure of Monica Bellucci. "
            "Deep sculpted Mediterranean bone structure, large soulful dark brown almond eyes, rich crimson lips in confident relaxed calm smile, warm golden-olive skin with natural fine pores. "
            "Rich voluminous dark chestnut curls framing her collarbones, wearing a black velvet robe over vintage corsetry. "
            "Gilded baroque mirror background with warm amber candlelight, timeless cinematic realism, Leica Noctilux 50mm f/0.95, Vogue Italia cover quality."
        )
    },
    {
        "id": "09_runway_celestial_angel",
        "title": "09 · 高定秀场 · 贝母流光晶石双翼",
        "subtitle": "何穗级发光冷白皮 · 东方丹凤眼神明白月光",
        "seed": 20268109,
        "prompt": (
            "Ethereal candid 35mm photograph of a breathtaking 22-year-old Chinese supermodel walking down a grand international haute couture gala catwalk. "
            "Luminous translucent milky-white skin glowing from within under runway spotlights, smooth elegant jawline, captivating elongated dark almond phoenix eyes, calm blooming regal smile with natural rosy lips. "
            "Silky obsidian black hair falling in cascading waves, wearing shimmering iridescent mother-of-pearl crystalline angel wings and a flowing silver-white silk chiffon gown. "
            "Backstage runway entrance with dramatic blue and silver haze, Kodak Portra 400 aesthetic, iconic Victoria's Secret haute couture."
        )
    }
]


def assemble_grid_board(image_paths: list[Path], titles: list[str], output_path: Path, rows: int = 3, cols: int = 3):
    """Build a professional showcase grid with borders and clean white banner headers."""
    images = [Image.open(p).convert("RGB") for p in image_paths]
    
    tile_w, tile_h = 600, 1060  # Aspect ratio 9:16
    pad = 16
    header_h = 140
    
    total_w = cols * tile_w + (cols + 1) * pad
    total_h = header_h + rows * tile_h + (rows + 1) * pad
    
    board = Image.new("RGB", (total_w, total_h), "#F8FAFC")
    draw = ImageDraw.Draw(board)
    
    # Header bar
    f_main = ImageFont.truetype(FONT_ZH_BOLD, 42)
    f_sub = ImageFont.truetype(FONT_ZH_REG, 22)
    f_badge = ImageFont.truetype(FONT_ZH_BOLD, 18)
    
    draw.rectangle([0, 0, total_w, 10], fill="#2563EB")
    draw.text((pad + 10, 30), "全球神颜特辑 · 纯原生 Z-Image Turbo 6B 裸跑高清九宫格", font=f_main, fill="#0F172A")
    draw.text((pad + 12, 85), "测试标准：100% 零 LoRA 裸跑直出 · 8步极速收敛 · 真实微血管毛孔 · 纯天然胶原蛋白微表情", font=f_sub, fill="#475569")
    
    # Place images
    for i, img in enumerate(images[:rows * cols]):
        r = i // cols
        c = i % cols
        x = pad + c * (tile_w + pad)
        y = header_h + pad + r * (tile_h + pad)
        
        resized = img.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        board.paste(resized, (x, y))
        
        # Border
        draw.rectangle([x, y, x + tile_w, y + tile_h], outline="#E2E8F0", width=2)
        
        # Label card at bottom of each tile
        label_h = 56
        draw.rectangle([x, y + tile_h - label_h, x + tile_w, y + tile_h], fill="#0F172ACC")
        if i < len(titles):
            draw.text((x + 16, y + tile_h - label_h + 16), titles[i], font=f_badge, fill="#F8FAFC")
            
    board.save(output_path, quality=95)
    print(f"[+] Saved grid board: {output_path}")


def main():
    print("=" * 70)
    print(" Complete Douyin Remaster Suite: 100% Z-Image Turbo 6B Native")
    print(f" Delivering to: {DELIVER_DIR}")
    print("=" * 70)

    generated_paths = []
    titles = []

    for idx, item in enumerate(DOUYIN_SEQUENCE, 1):
        task_id = item["id"]
        prompt = item["prompt"]
        seed = item["seed"]
        title = item["title"]
        titles.append(title)

        dest_file = DELIVER_DIR / f"{task_id}.png"
        print(f"\n[{idx}/9] Generating: {title} ...")

        t0 = time.time()
        # 9:16 vertical ratio (768 x 1360)
        img_path = produce_z_image_turbo(
            prompt=prompt,
            width=768,
            height=1360,
            seed=seed,
            prefix=f"douyin_zimage_{task_id}"
        )
        # Copy to deliver dir
        import shutil
        shutil.copy(img_path, dest_file)
        print(f"    Done in {time.time() - t0:.1f}s -> {dest_file.name}")
        generated_paths.append(dest_file)

    # Assemble 3x3 9-Grid Board
    grid_9_path = DELIVER_DIR / "douyin_muses_3x3_grid.png"
    print("\n[*] Assembling 3x3 9-Grid showcase board...")
    assemble_grid_board(generated_paths, titles, grid_9_path, rows=3, cols=3)

    # Assemble 2x3 6-Grid Board (First 6 images)
    grid_6_path = DELIVER_DIR / "douyin_muses_6grid.png"
    print("[*] Assembling 2x3 6-Grid showcase board...")
    assemble_grid_board(generated_paths[:6], titles[:6], grid_6_path, rows=2, cols=3)

    print("\n" + "=" * 70)
    print(" All 9 Douyin portraits & showcase boards generated successfully!")
    print(f" Output directory: {DELIVER_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
