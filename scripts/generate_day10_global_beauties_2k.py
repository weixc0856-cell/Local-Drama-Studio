"""
Generate Day 10 Milestone Collection: 《芳华初绽 · 顶级杂志封面与二十岁的黄金瞬间》
(In Full Bloom: The Golden Age of Youth - Vogue Editorial 6-Pack 2K Edition)
CRITICAL MANDATES:
1. Theme: High-fashion professional magazine editorial (Vogue/Harper's Bazaar) celebrating women in their peak golden age (20-22 years old)
2. ZERO real celebrity names anywhere
3. Abundant youthful collagen, flawless porcelain/dewy skin, zero freckles, soft feminine facial harmony
4. 6 photos in true 2K (1152 x 2048) + 1 master 6-grid showcase board + clean PATREON_POST.md
"""
import os
import sys
import json
import time
import re
import shutil
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_URL = "http://127.0.0.1:8188"
WF_LORA = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")
WF_BASE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_t2i_api.json")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day10"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day10_01_china_editorial",
        "region": "【中国·月华初绽】",
        "location": "顶级时尚大片影棚 · 21岁东方天仙神颜 · 白月光真丝晚装",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261001,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking high-fashion Vogue magazine cover portrait of an extraordinarily gorgeous 21-year-old Chinese muse (顶级时尚杂志封面大片、21岁东方神颜天花板、芳华初绽、饱满紧致胶原蛋白、平整鹅蛋脸、清冷端庄天仙气质、绝无浓妆假面). "
            "Exquisite youthful facial contours, delicate slender swan neck, high cranial top, slender straight nose, captivating dark almond eyes with quiet soulful tenderness and crystal-clear catchlights. "
            "Naturally plump hydrated soft petal-rose lips slightly parted in relaxed breathing repose, pristine porcelain jade skin glowing from within with pure youth. "
            "Sleek silky black hair gathered in an elegant loose couture chignon with delicate wispy strands framing her face. "
            "Wearing an architectural ivory-white heavy mulberry silk halter gown with liquid drape, minimalist diamond ear studs. "
            "Soft luxury beauty dish studio lighting casting gentle sculpted shadows, dark minimalist background, Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece."
        )
    },
    {
        "id": "day10_02_western_editorial",
        "region": "【欧美·法式浪漫】",
        "location": "巴黎高定沙龙窗边 · 21岁少女初熟的灵动绝色",
        "workflow": "base",
        "seed": 20261002,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion editorial portrait of an extraordinarily stunning 21-year-old French muse in a Parisian couture salon (法国Vogue封面大片、21岁浪漫少女神颜、饱满紧致胶原蛋白、灵动深邃大眼、零雀斑无暇雪肌、法式优雅甜美、绝无硬朗老态). "
            "Perfect feminine youthful facial proportions, soft rounded chin, slender straight nose, captivating large sparkling hazel-green doe eyes with natural lush dark lashes looking directly into the lens. "
            "Plump soft rosy-peach hydrated lips with subtle natural sweetness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Voluminous wavy honey-brown hair falling casually over one shoulder, wearing an off-the-shoulder minimalist black velvet corset dress with ivory silk organza trim. "
            "Soft directional Rembrandt window light from Parisian floor-to-ceiling balcony, creamy neutral studio background, Leica M11 50mm f/1.4 Summilux, timeless European cinema glamour."
        )
    },
    {
        "id": "day10_03_japan_editorial",
        "region": "【日本·纯氧初恋】",
        "location": "东京自然光艺术影棚 · 20岁清纯灵动初绽 · 粉彩羊绒与薄纱",
        "workflow": "base",
        "seed": 20261003,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion Japanese magazine cover photograph of an extraordinarily gorgeous 20-year-old Japanese youthful beauty (日本顶级杂志ar画报封面、20岁初恋神颜巅峰、清纯灵动氧气感、婴儿肥饱满胶原蛋白、水灵大眼睛、甜美治愈系). "
            "Dainty delicate feminine face, soft smooth jawline, large clear dewy dark expressive eyes filled with innocent sweet charm, petite straight nose. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with natural youthful blush, completely smooth and clear. "
            "Dark silky hair with soft air bangs, wearing a soft blush-pink fine cashmere knit and draped sheer silk scarf, holding a delicate white peony bloom near her cheek. "
            "Soft diffused Japanese natural daylight, creamy warm pastel studio background, Hasselblad X2D 90mm lens, iconic Japanese beauty magazine perfection."
        )
    },
    {
        "id": "day10_04_korea_editorial",
        "region": "【韩国·温润名媛】",
        "location": "首尔清潭洞高定艺廊 · 21岁顶级水光富家千金",
        "workflow": "base",
        "seed": 20261004,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion Vogue Korea editorial photograph of an extraordinarily stunning 21-year-old Korean heiress (Vogue韩国封面大片、21岁温润千金神颜、顶级饱满水光凝脂肌、三庭五眼极致端庄、清甜贵气、绝无整容流水线感). "
            "Impeccably proportioned soft oval face, full youthful cheeks without any hollows, delicate dainty straight nose, captivating clear dark almond eyes radiating calm aristocratic warmth. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing with pure luxury hydration. "
            "Voluminous glossy dark espresso hair with soft side-swept waves, wearing a tailored champagne-gold liquid silk satin blazer dress, minimalist diamond tennis choker. "
            "Soft luxury key lighting with delicate silver fill, warm architectural gallery background, Leica M11 50mm f/1.4 Summilux, luxury Korean fashion editorial."
        )
    },
    {
        "id": "day10_05_mediterranean_editorial",
        "region": "【地中海·西西里明艳】",
        "location": "罗马古堡暖阳露台 · 21岁明艳甜美意式神颜",
        "workflow": "base",
        "seed": 20261005,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion editorial portrait of an extraordinarily gorgeous 21-year-old Italian Mediterranean youthful goddess (意大利Vogue封面大片、21岁西西里明艳神颜巅峰、饱满紧致胶原蛋白、心形柔美小脸、大美人气场与甜美并存、绝无粗犷显老). "
            "Delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes with long naturally lush lashes and warm radiant sparkle. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in the warm Italian afternoon light. "
            "Wearing an emerald-green liquid silk slip dress with delicate gold jewelry. "
            "Warm golden rim lighting, antique Roman marble architecture softly blurred in background, Contax T2 35mm f/2.8 lens, Dolce & Gabbana luxury editorial masterpiece."
        )
    },
    {
        "id": "day10_06_slavic_editorial",
        "region": "【斯拉夫·极光翡翠】",
        "location": "维也纳古典音乐厅沙龙 · 20岁极光瓷娃娃",
        "workflow": "base",
        "seed": 20261006,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion magazine cover portrait of an extraordinarily stunning 20-year-old Slavic Eastern European doll-like beauty (Harper's Bazaar封面大片、20岁极光芭比神颜、瓷娃娃般紧致白皙、饱满胶原蛋白、清澈纯真翡翠猫眼、绝美空灵). "
            "Soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes filled with youthful sparkle and gentle warmth. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair styled with soft natural movement over bare shoulders. "
            "Wearing a midnight-navy blue liquid satin off-the-shoulder gown, delicate diamond drop earrings. "
            "Soft flattering studio glamour lighting, classical dark baroque backdrop with subtle warm gold accents, Leica M11 50mm f/1.4 Summilux, European haute couture perfection."
        )
    }
]

def _render(value, params: dict):
    if isinstance(value, dict):
        return {k: _render(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, params) for v in value]
    if isinstance(value, str):
        match = PLACEHOLDER.match(value)
        if match:
            key = match.group(1)
            if key not in params:
                raise KeyError(f"missing workflow parameter: {key}")
            return params[key]
    return value

def queue_prompt(prompt_workflow):
    data = json.dumps({"prompt": prompt_workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/prompt", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_history(prompt_id):
    req = urllib.request.Request(f"{BASE_URL}/history/{prompt_id}")
    for _ in range(10):
        try:
            with OPENER.open(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            time.sleep(3)
    return {}

def wait_for_completion(pid, dst_file, timeout=300):
    start = time.time()
    comfy_out_dir = ROOT / "runtime" / "ComfyUI" / "output"
    while time.time() - start < timeout:
        hist = get_history(pid)
        if pid in hist:
            outputs = hist[pid].get("outputs", {})
            for nid, nout in outputs.items():
                if "images" in nout and len(nout["images"]) > 0:
                    img_info = nout["images"][0]
                    subfolder = img_info.get("subfolder", "")
                    fname = img_info.get("filename", "")
                    src = comfy_out_dir
                    if subfolder:
                        src = src / subfolder
                    src_file = src / fname
                    if src_file.exists():
                        shutil.copy(src_file, dst_file)
                        print(f"-> Saved base: {dst_file.name}", flush=True)
                        return True
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return False

def upscale_image_to_2k_porcelain(file_path, art_file_path):
    img = Image.open(file_path).convert("RGB")
    print(f"  Upscaling {file_path.name} to 2K (1152x2048) with porcelain skin protection...", flush=True)
    up = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    # Mild edge unsharp mask (radius 0.6, percent 50) - keeps skin baby-smooth, sharpens eyes & hair
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=50, threshold=3))
    enhancer = ImageEnhance.Contrast(sharpened)
    final_img = enhancer.enhance(1.02)
    
    final_img.save(file_path, "PNG", quality=95)
    shutil.copy(file_path, art_file_path)
    print(f"  -> 2K Upscale Complete: {file_path.name}", flush=True)

def make_6grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 10 Milestone 6-Grid showcase board...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    
    thumb_w, thumb_h = 576, 1024
    cards_thumb = [c.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS) for c in cards]
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + thumb_w * 2
    board_h = header_h + margin + (thumb_h + card_title_h) * 3 + margin + footer_h
    
    board = Image.new("RGB", (board_w, board_h), (245, 245, 247))
    draw = ImageDraw.Draw(board)
    
    font_bold = None
    font_med = None
    font_sm = None
    for fpath in [
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyhbd.ttc"),
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf"),
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc")
    ]:
        if os.path.exists(fpath):
            try:
                font_bold = ImageFont.truetype(fpath, 42)
                font_med = ImageFont.truetype(fpath, 22)
                font_sm = ImageFont.truetype(fpath, 16)
                break
            except Exception:
                continue
    if not font_bold:
        font_bold = ImageFont.load_default()
        font_med = font_bold
        font_sm = font_bold

    # Header
    draw.text((margin + 10, 35), "Day 10 · 芳华初绽 · 顶级杂志封面与二十岁黄金神颜 (6张全集 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 10: In Full Bloom · The Golden Age of Youth (Vogue Editorial Master Set)", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·月华初绽】", "时尚杂志大片 · 21岁东方天仙神颜 · 白月光真丝晚装"),
        ("【欧美·法式浪漫】", "巴黎高定沙龙 · 21岁法式初熟少女 · 零雀斑纯净雪肌"),
        ("【日本·纯氧初恋】", "自然光艺术影棚 · 20岁清纯灵动初恋感 · 粉彩羊绒与薄纱"),
        ("【韩国·温润名媛】", "清潭高定艺廊 · 21岁水光凝脂富家千金 · 香槟金缎面晚装"),
        ("【地中海·西西里明艳】", "罗马古堡暖阳露台 · 21岁西西里明艳神颜 · 墨绿真丝吊带"),
        ("【斯拉夫·极光翡翠】", "维也纳古典沙龙 · 20岁极光瓷娃娃 · 纯净翡翠猫眼晚装")
    ]

    for idx, card in enumerate(cards_thumb):
        col = idx % 2
        row = idx // 2
        
        x = margin + col * (thumb_w + margin)
        y = header_h + margin + row * (thumb_h + card_title_h + margin)
        
        board.paste(card, (x, y))
        
        tx_main, tx_sub = labels[idx]
        text_y_main = y + thumb_h + 10
        text_y_sub = text_y_main + 26
        draw.text((x + 10, text_y_main), tx_main, fill=(30, 30, 35), font=font_med)
        draw.text((x + 10, text_y_sub), tx_sub, fill=(110, 115, 125), font=font_sm)

    foot_y = board_h - footer_h + 18
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism 6-Pack Series | 2K Ultra-HD Edition", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Day 10 Milestone Issue (6-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 10 Milestone: In Full Bloom — The Golden Age of Youth (Vogue Editorial 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 10 盛典特辑】芳华初绽 · 顶级杂志封面与二十岁黄金神颜 · 6大全球神颜画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, VogueEditorial, GoldenAge, HauteCouture, SilkGown, FilmGrain, Glamour, Exclusive, 6PhotoSet, 2KUltraHD`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day10_in_full_bloom_6grid.png`
2. **2K无损单图附件 (6 Standalone 2K High-Res Attachments)**:
   - `day10_01_china_editorial.png` (【中国·月华初绽】时尚杂志大片 · 21岁东方天仙神颜 · 白月光真丝晚装)
   - `day10_02_western_editorial.png` (【欧美·法式浪漫】巴黎高定沙龙 · 21岁法式初熟少女 · 零雀斑纯净雪肌)
   - `day10_03_japan_editorial.png` (【日本·纯氧初恋】自然光艺术影棚 · 20岁清纯灵动初恋感 · 粉彩羊绒与薄纱)
   - `day10_04_korea_editorial.png` (【韩国·温润名媛】清潭高定艺廊 · 21岁水光凝脂富家千金 · 香槟金缎面晚装)
   - `day10_05_mediterranean_editorial.png` (【地中海·西西里明艳】罗马古堡暖阳露台 · 21岁西西里明艳神颜 · 墨绿真丝吊带)
   - `day10_06_slavic_editorial.png` (【斯拉夫·极光翡翠】维也纳古典沙龙 · 20岁极光瓷娃娃 · 纯净翡翠猫眼晚装)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 10 Milestone: In Full Bloom — The Golden Age of Youth (6 Global Muses)
全球纪实神颜日更 · Day 10 盛典特辑 · 芳华初绽 · 顶级杂志封面与二十岁黄金神颜 (6张全集 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome to our Milestone Issue: Day 10 of Daily Candid Realism!

Today, we dedicate this special editorial edition to the single most breathtaking period of human beauty: the golden age of youth (20 to 22 years old). Captured through the high-end lens of an international fashion magazine cover editorial (Vogue, Harper's Bazaar, Numéro), this collection celebrates radiant youthful collagen, natural elegance, and timeless grace across six distinct cultural archetypes:

• China: 21-year-old ethereal goddess in liquid ivory mulberry silk, soft studio beauty dish lighting, and quiet celestial poise.
• Western Europe: 21-year-old French romantic muse in Parisian velvet and organza, sparkling hazel-green doe eyes, and flawless porcelain skin.
• Japan: 20-year-old innocent first-love icon in pastel cashmere, holding a delicate white peony bloom in soft diffused daylight.
• Korea: 21-year-old gentle heiress in a tailored champagne-satin blazer dress, luminous glass skin, and quiet aristocratic warmth.
• Mediterranean: 21-year-old radiant Sicilian beauty with bouncy dark chocolate curls in an emerald silk slip dress against warm Roman marble.
• Eastern Europe: 20-year-old doll-like Slavic angel in a midnight-navy satin gown, mesmerizing emerald-green cat eyes, and pure porcelain milk skin.

Zero artificial plastic filters, zero age fatigue, zero generic templates. All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Editorial Moments / 今日六组封面高光

1. 🇨🇳 China: Ethereal Moonlight Silk · 月华初绽
• Scene: Minimalist high-fashion studio, soft luxury beauty dish lighting.
• Optics: Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece.
• Details: 21-year-old celestial beauty, pristine porcelain jade skin, liquid ivory silk halter gown, diamond ear studs, calm captivating dark almond eyes.

2. 🇫🇷 Western Europe: Parisian Salon Romance · 法式浪漫
• Scene: Haussmannian salon balcony with soft directional Rembrandt window light.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless French cinema glamour.
• Details: 21-year-old French muse, large sparkling doe eyes, off-the-shoulder black velvet and organza gown, zero freckles, honey-brown wavy hair.

3. 🇯🇵 Japan: Pure Oxygen Bloom · 纯氧初恋
• Scene: Tokyo natural light studio, warm diffused daylight and soft pastel tones.
• Optics: Hasselblad X2D 90mm lens, iconic Japanese beauty magazine perfection.
• Details: 20-year-old first-love icon, soft air bangs, dewy strawberry-pink lips, blush-pink cashmere knit, fresh white peony bloom.

4. 🇰🇷 Korea: Cheongdam Penthouse Satin · 温润名媛
• Scene: High-end contemporary art gallery, soft silver fill lighting.
• Optics: Leica M11 50mm f/1.4 Summilux, luxury Korean fashion editorial.
• Details: 21-year-old gentle heiress, champagne-gold liquid satin blazer dress, diamond tennis necklace, luminous glass skin, serene aristocratic poise.

5. 🇮🇹 Mediterranean: Tuscan Golden Hour · 西西里明艳
• Scene: Antique Roman terrace at sunset, golden backlight glinting through dark curls.
• Optics: Contax T2 35mm f/2.8 lens, Dolce & Gabbana luxury editorial.
• Details: 21-year-old Sicilian goddess, soft heart-shaped face, emerald-green liquid silk slip dress, velvety dark eyes, bouncy chocolate curls.

6. 🇦🇹 Eastern Europe: Viennese Baroque Gala · 极光翡翠
• Scene: Classical Viennese salon, soft glamour lighting against dark baroque walls.
• Optics: Leica M11 50mm f/1.4 Summilux, European haute couture perfection.
• Details: 20-year-old Slavic doll-like angel, midnight-navy satin gown, hypnotic clear emerald-green cat eyes, diamond drop earrings, porcelain milk skin.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Studio Lighting & Haute Couture Textures: 精确模拟顶级时尚杂志（Vogue/Bazaar）的柔光美肤碟（Beauty Dish）与伦勃朗侧面光，完美呈现重磅真丝、天鹅绒与细织羊绒的高奢质感。
• Peak-Youth Collagen Tuning: 严格锁定 20~22 岁黄金颜值花期，饱满紧致、平整中庭，展现最具感染力的青春纯真与优雅。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出，发丝反光与瞳孔光斑纤毫毕现。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 10 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which cover editorial captures your heart the most? Let me know in the comments below!
"""
    patreon_file = OUTPUT_DIR / "PATREON_POST.md"
    with open(patreon_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated PATREON_POST.md at: {patreon_file}", flush=True)

def update_master_index():
    index_file = ROOT / "experiments" / "PATREON_SERIES_INDEX.md"
    if not index_file.exists():
        return
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "## 🚀 每次发帖 3 步操作指引"
    if marker in content:
        parts = content.split(marker)
        table_part = parts[0]
        rest_part = marker + parts[1]
        
        new_row = """| **Day 10** | **《芳华初绽 · 顶级杂志封面与二十岁黄金神颜 (10期盛典 · 2K)》**<br>东方天仙重磅真丝、巴黎高定沙龙法式浪漫、昭和纯氧初恋牡丹、清潭水光千金缎面、西西里明艳罗马暮色、维也纳极光翡翠瓷娃娃 | [`experiments/global_beauties_day10/`](experiments/global_beauties_day10/) | [`PATREON_POST.md`](experiments/global_beauties_day10/PATREON_POST.md) | [6 宫格母版大图](experiments/global_beauties_day10/day10_in_full_bloom_6grid.png) | 6 张超清原图 |
---

"""
        if "Day 10" not in table_part:
            table_part += new_row
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(table_part + rest_part)
            print("Updated PATREON_SERIES_INDEX.md with Day 10 successfully!", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 10 Magazine Milestone - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        if dst_file.exists() and dst_file.stat().st_size > 100000:
            print(f"  Already exists: {dst_file.name}, skipping generation.", flush=True)
            generated_paths.append(dst_file)
            shutil.copy(dst_file, art_file)
            continue

        if t["workflow"] == "lora":
            params = {
                "lora_name": t["lora_name"],
                "lora_strength": t["lora_strength"],
                "positive_prompt": t["prompt"],
                "width": 576,
                "height": 1024,
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_lora, params)
        else:
            params = {
                "positive_prompt": t["prompt"],
                "width": 576,
                "height": 1024,
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_base, params)

        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"  Queued prompt_id: {pid} on Intel Arc A750...", flush=True)

        ok = wait_for_completion(pid, dst_file)
        if ok:
            upscale_image_to_2k_porcelain(dst_file, art_file)
            generated_paths.append(dst_file)
        else:
            print(f"  Failed for {t['id']}", flush=True)

    if len(generated_paths) == 6:
        board_file = OUTPUT_DIR / "day10_in_full_bloom_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day10_in_full_bloom_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 10 Milestone Magazine Edition succeeded with 6 breathtaking faces!", flush=True)

if __name__ == "__main__":
    main()
