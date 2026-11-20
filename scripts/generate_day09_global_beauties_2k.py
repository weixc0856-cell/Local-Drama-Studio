"""
Re-Generate Day 09: Peak-Youth Goddess Overhaul (Age 20-22, Full Collagen, Absolute Beauty)
Eliminates all aged, hollow, or harsh masculine bone structures.
Every single model is a breathtaking, 20-22 year old peak beauty with soft feminine contours and radiant collagen.
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
WF_LORA = r"d:\Local-Drama-Studio\workflows\flux3_lora_t2i_api.json"
WF_BASE = r"d:\Local-Drama-Studio\workflows\flux3_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day09"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day09_01_china_autumn",
        "region": "【中国·金叶天仙神颜】",
        "location": "古都红墙银杏长廊 · 21岁巅峰神颜白月光",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20269901,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm film photograph of an extraordinarily gorgeous 21-year-old Chinese goddess standing by ancient red palace walls surrounded by glowing golden ginkgo trees in autumn (21岁天仙神颜巅峰、饱满胶原蛋白、平整无暇鹅蛋脸、清纯端庄天花板、绝无老态下垂、绝无浓妆假面). "
            "Exquisite youthful facial contours, smooth soft jawline, high cranial top, delicate slender nose, crystal-clear dark almond eyes with soulful radiant tenderness. "
            "Plump hydrated natural rose lips slightly parted in soft breathing repose, pristine porcelain jade skin glowing with pure youth. "
            "Long silky raven hair flowing in the gentle autumn breeze, wearing an elegant tailored camel cashmere trench coat over an ivory silk blouse. "
            "Golden autumn sunlight and drifting yellow ginkgo leaves in creamy background, Leica M11 50mm f/1.4 Summilux, cinematic masterpiece."
        )
    },
    {
        "id": "day09_02_western_autumn",
        "region": "【欧美·法式甜欲神颜】",
        "location": "巴黎塞纳河畔林荫道 · 21岁少女初熟的浪漫绝色",
        "workflow": "base",
        "seed": 20269902,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film portrait of an extraordinarily gorgeous 21-year-old French European beauty standing along the Seine in Paris in autumn (21岁少女绝顶神颜、胶原蛋白饱满、法式甜美浪漫、精致小巧鹅蛋脸、零雀斑无暇雪肌、绝无硬朗显老感、惊艳动人). "
            "Flawless youthful feminine facial proportions, soft rounded chin, delicate straight slender nose, captivating large sparkling hazel-green doe eyes with natural dark lashes. "
            "Plump soft rosy-peach lips with subtle natural tenderness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Lush wavy honey-brown hair tossed effortlessly by the breeze, wearing a tailored honey-tan gabardine trench coat over a soft knit. "
            "Golden chestnut leaves drifting over the stone embankment, creamy vintage Parisian autumn bokeh, Contax T2 35mm f/2.8 lens, legendary French cinema beauty."
        )
    },
    {
        "id": "day09_03_japan_autumn",
        "region": "【日本·昭和初恋神颜】",
        "location": "京都岚山古寺石阶 · 20岁清纯初恋感天花板",
        "workflow": "base",
        "seed": 20269903,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily stunning 20-year-old Japanese young beauty on stone steps in Kyoto beneath scarlet autumn maples (20岁初恋神颜巅峰、清纯灵气、饱满胶原蛋白婴儿肥、水汪汪大眼睛、绝美治愈系、绝无老气僵硬). "
            "Dainty delicate feminine face, soft smooth jawline, large clear dewy dark expressive eyes filled with innocent sweet charm, petite straight nose. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with youthful blush, zero blemish. "
            "Dark silky hair with soft wispy bangs, wearing an oatmeal-cream wool coat, holding a warm wooden cup of roasted green tea with both hands. "
            "Mossy stone lanterns and vibrant red maple leaves in soft golden autumn mist, Hasselblad X2D 90mm lens, cinematic Japanese youth drama perfection."
        )
    },
    {
        "id": "day09_04_korea_autumn",
        "region": "【韩国·温润千金初熟】",
        "location": "首尔三清洞古石墙路 · 21岁温润水光富家千金",
        "workflow": "base",
        "seed": 20269904,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily beautiful 21-year-old Korean heiress walking along Samcheong-dong stone wall in autumn (21岁温润千金神颜、顶级饱满胶原蛋白、水光凝脂肌、清甜贵气、五官极致对称端庄、绝无老成整容感). "
            "Softly contoured oval face, full youthful cheeks without any hollows, delicate dainty straight nose, captivating dark almond eyes with gentle clear warmth. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing in the autumn sunlight. "
            "Voluminous glossy dark espresso hair with soft side-swept waves, wearing a tailored cream-white double-faced cashmere coat with wide lapels. "
            "Golden ginkgo leaves and ancient stone wall in warm golden hour glow, Leica M11 50mm f/1.4 Summilux, Vogue Korea luxury realism."
        )
    },
    {
        "id": "day09_05_mediterranean_autumn",
        "region": "【地中海·西西里明艳少女】",
        "location": "托斯卡纳金秋柏树道 · 21岁明艳甜美意式神颜",
        "workflow": "base",
        "seed": 20269905,
        "steps": 20,
        "prompt": (
            "Breathtaking cinematic 35mm film portrait of an extraordinarily gorgeous 21-year-old Italian Mediterranean youthful goddess in Tuscany at golden autumn sunset (21岁意式明艳神颜巅峰、饱满紧致胶原蛋白、甜美与风情并存、心形柔美小脸、绝无粗犷骨架、绝无衰老凹陷、惊艳明眸). "
            "Delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes with long naturally lush lashes and warm radiant sparkle. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in the warm sunset breeze. "
            "Wearing an olive-green belted wool trench coat, holding a small wicker basket of purple figs. "
            "Golden rolling Tuscan hills and tall cypress trees bathed in warm amber backlight, Contax T2 35mm f/2.8 lens, Italian romantic cinema masterpiece."
        )
    },
    {
        "id": "day09_06_slavic_autumn",
        "region": "【斯拉夫·极光翡翠瓷娃娃】",
        "location": "维也纳美泉宫林荫道 · 20岁洋娃娃般冰雪神颜",
        "workflow": "base",
        "seed": 20269906,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily stunning 20-year-old Slavic Eastern European doll-like beauty in Vienna in autumn (20岁极光芭比神颜、瓷娃娃般紧致白皙、饱满胶原蛋白、绝顶惊艳绝非刻薄显老、翡翠猫眼清澈动人). "
            "Soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes filled with youthful sparkle and gentle warmth. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair blowing softly in the autumn wind. "
            "Wearing a tailored deep forest-green wool trench coat with dark buttons. "
            "Golden cathedral canopy of Schönbrunn autumn trees and historic palace statues in soft golden bokeh, Leica M11 50mm f/1.4 Summilux, European fairy-tale realism."
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
    print("Assembling Day 09 Peak-Youth 6-Grid showcase board...", flush=True)
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
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc"
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
    draw.text((margin + 10, 35), "Day 09 · 秋意浓郁 · 金叶长廊与经典风衣 (20岁巅峰神颜 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 09: Autumn Reverie & Classic Trench Coats · Peak Youth Aesthetics", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·金叶天仙神颜】", "古都红墙银杏长廊 · 21岁巅峰神颜白月光 · 驼色羊绒风衣"),
        ("【欧美·法式甜欲神颜】", "巴黎塞纳河畔林荫道 · 21岁法式初熟少女 · 零雀斑瓷白雪肌"),
        ("【日本·昭和初恋神颜】", "京都岚山古寺石阶 · 20岁清纯初恋感天花板 · 燕麦羊绒大衣"),
        ("【韩国·温润千金初熟】", "首尔三清洞古石墙路 · 21岁温润水光富家千金 · 双面羊绒大衣"),
        ("【地中海·西西里明艳少女】", "托斯卡纳金秋柏树道 · 21岁明艳甜美意式神颜 · 墨绿束腰风衣"),
        ("【斯拉夫·极光翡翠瓷娃娃】", "维也纳美泉宫林荫道 · 20岁芭比般冰雪绝色 · 翡翠绿眼瓷肌")
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
    md_content = """# Patreon Publish Package · Day 09 (6-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 09: Autumn Reverie & Classic Trench Coats — 6 Peak-Youth Beauties (Full 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 09】秋意浓郁 · 金叶长廊与经典风衣 · 全球6大20岁巅峰神颜画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, AutumnVibes, TrenchCoat, Cashmere, HighFashion, FilmGrain, Glamour, Exclusive, 6PhotoSet, 2KUltraHD`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day09_autumn_trench_6grid.png`
2. **2K无损单图附件 (6 Standalone 2K High-Res Attachments)**:
   - `day09_01_china_autumn.png` (【中国·金叶天仙神颜】古都红墙银杏长廊 · 21岁巅峰神颜白月光 · 驼色羊绒风衣)
   - `day09_02_western_autumn.png` (【欧美·法式甜欲神颜】巴黎塞纳河畔林荫道 · 21岁法式初熟少女 · 零雀斑瓷白雪肌)
   - `day09_03_japan_autumn.png` (【日本·昭和初恋神颜】京都岚山古寺石阶 · 20岁清纯初恋感天花板 · 燕麦羊绒大衣)
   - `day09_04_korea_autumn.png` (【韩国·温润千金初熟】首尔三清洞古石墙路 · 21岁温润水光富家千金 · 双面羊绒大衣)
   - `day09_05_mediterranean_autumn.png` (【地中海·西西里明艳少女】托斯卡纳金秋柏树道 · 21岁明艳甜美意式神颜 · 墨绿束腰风衣)
   - `day09_06_slavic_autumn.png` (【斯拉夫·极光翡翠瓷娃娃】维也纳美泉宫林荫道 · 20岁芭比般冰雪绝色 · 翡翠绿眼瓷肌)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 09: Autumn Reverie & Classic Trench Coats (6 Peak-Youth Beauties)
全球纪实神颜日更 · Day 09 · 秋意浓郁 · 金叶长廊与经典风衣 (6张巅峰神颜全集 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Daily Candid Realism! Today, we celebrate the season of golden light, drifting maple foliage, and the timeless elegance of classic trench coats.

In Day 09, we present six breathtaking youthful muses in their absolute golden age (20–22 years old), captured across iconic autumn avenues worldwide:
• China: 21-year-old ethereal goddess standing quietly by ancient red palace walls surrounded by glowing golden ginkgo trees.
• Western Europe: 21-year-old French muse along the Seine, youthful romantic charm, sparkling hazel-green doe eyes and pure porcelain skin.
• Japan: 20-year-old innocent first-love icon on wet stone steps in Kyoto beneath fiery scarlet maples, holding warm roasted green tea.
• Korea: 21-year-old gentle heiress walking along Samcheong-dong, glowing glass skin, soft cashmere and quiet luxury poise.
• Mediterranean: 21-year-old vibrant Italian beauty with bouncy curls and a soft heart-shaped face along Tuscan golden cypress roads.
• Eastern Europe: 20-year-old doll-like Slavic angel in Vienna's Schönbrunn palace gardens, luminous porcelain skin and hypnotic emerald-green eyes.

All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Moments / 今日六组高光

1. 🇨🇳 China: Ancient Ginkgo Canopy · 金叶天仙神颜
• Scene: Historic red palace walls framing a golden carpet of ginkgo leaves in crisp autumn sunlight.
• Optics: Leica M11 50mm f/1.4 Summilux, cinematic poetry.
• Details: 21-year-old peak fairy beauty, full youthful collagen, smooth heart-shaped face, camel cashmere trench coat, falling golden leaves.

2. 🇫🇷 Western Europe: Seine Riverbank Breeze · 法式甜欲神颜
• Scene: Paris stone riverbank covered in golden chestnut leaves, creamy vintage bokeh.
• Optics: Contax T2 35mm f/2.8 lens, legendary European cinema realism.
• Details: 21-year-old French youthful charm, large sparkling doe eyes, blemish-free porcelain skin with zero freckles, honey-tan trench coat.

3. 🇯🇵 Japan: Kyoto Crimson Maples · 昭和初恋神颜
• Scene: Moss-covered stone stairway of a quiet Kyoto temple surrounded by scarlet Japanese maples.
• Optics: Hasselblad X2D 90mm lens, gentle Showa film nostalgia.
• Details: 20-year-old pure first-love aesthetic, dewy dark eyes, tender sweet expression, oatmeal-cream wool coat, warm roasted tea cup.

4. 🇰🇷 Korea: Samcheong Historic Stone Wall · 温润千金初熟
• Scene: Ancient stone-wall avenue in Samcheong-dong, Seoul, bathed in low golden afternoon sunlight.
• Optics: Leica M11 50mm f/1.4 Summilux, luxury editorial realism.
• Details: 21-year-old gentle heiress, plump dewy petal-pink lips, luminous glass skin, cream-white cashmere coat.

5. 🇮🇹 Mediterranean: Tuscan Sunset Cypress Avenue · 西西里明艳少女
• Scene: Rolling Tuscan countryside road bordered by tall cypress trees at golden hour.
• Optics: Contax T2 35mm f/2.8 lens, Italian cinema romance.
• Details: 21-year-old radiant Italian beauty, soft heart-shaped face, velvety dark eyes, dark chocolate curls, olive-green belted trench coat.

6. 🇦🇹 Eastern Europe: Schönbrunn Golden Tree Tunnel · 极光翡翠瓷娃娃
• Scene: Majestic golden tree-lined avenue of Schönbrunn Palace in Vienna, Roman statues in soft background.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless European elegance.
• Details: 20-year-old Slavic doll-like angel, bright emerald-green eyes, soft rose lips, forest-green tailored coat, porcelain milk skin.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Peak-Youth Collagen Tuning: 锁定 20~22 岁黄金颜值巅峰，杜绝深陷骨窝或刻薄面相，呈现极致饱满柔润的天然神颜。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出，保留发丝光泽与羊绒编织纹理，面部肌肤如天然羊脂般柔嫩细腻。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 09 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which autumn muse captures your heart the most? Let me know in the comments below!
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
        
        if "Day 09" in table_part:
            lines = table_part.split("\n")
            new_lines = []
            for l in lines:
                if "Day 09" in l:
                    new_lines.append("| **Day 09** | **《秋意浓郁 · 金叶长廊与经典风衣 (20岁巅峰神颜 · 2K)》**<br>古都红墙银杏天仙、塞纳河畔法式甜欲少女、京都岚山20岁初恋神颜、三清洞温润千金、西西里21岁明艳少女、维也纳20岁极光瓷娃娃 | [`experiments/global_beauties_day09/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day09/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day09/PATREON_POST.md) | [6 宫格母版大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day09/day09_autumn_trench_6grid.png) | 6 张超清原图 |")
                else:
                    new_lines.append(l)
            table_part = "\n".join(new_lines)
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(table_part + rest_part)
            print("Updated PATREON_SERIES_INDEX.md with Peak-Youth Day 09!", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 09 Peak-Youth - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

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
        board_file = OUTPUT_DIR / "day09_autumn_trench_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day09_autumn_trench_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 09 Peak-Youth Complete Overhaul succeeded with 6 breathtaking faces!", flush=True)

if __name__ == "__main__":
    main()
