"""
Generate Day 08 Collection: 《暮色微醺 · 城市天际线与露台酒廊》 (Twilight Skyline & Rooftop Cocktails - 6-Pack Edition)
Global Candid Realism · 全球纪实神颜日更 (每期6张标准全集)
CRITICAL MANDATES:
1. ZERO real celebrity names anywhere (not in prompts, not in titles, not in metadata, not in files)
2. Golden ratio facial symmetry, smooth feminine jawlines, soft relaxed expressions, zero uncanny/weird distortion
3. Flawless clear porcelain skin, zero freckles on Western/European beauties
4. 6 photos + 1 master 6-grid showcase board (2 columns x 3 rows) + clean PATREON_POST.md
"""
import os
import sys
import json
import time
import re
import shutil
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://127.0.0.1:8188"
WF_LORA = r"d:\Local-Drama-Studio\workflows\flux3_lora_t2i_api.json"
WF_BASE = r"d:\Local-Drama-Studio\workflows\flux3_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day08"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day08_01_china_skyline",
        "region": "【中国·外滩暮色】",
        "location": "外滩高空露天吧 · 江景流光与香槟微风",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.70,
        "seed": 20261801,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm film photograph of an extraordinarily stunning young Chinese woman at an open-air rooftop lounge overlooking the Shanghai Bund skyline at twilight (外滩高空夜景、天际线流光、东方古典仙姿神颜、黄金比例端庄面容、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender swan neck and graceful collarbone, soulful clear dark almond eyes looking back with quiet breathtaking depth and gentle warmth, naturally full hydrated soft rose lips in relaxed breathing repose. "
            "Pristine translucent porcelain jade skin illuminated by warm flickering candle glow and cool city bokeh. "
            "Long silky raven hair blown gracefully by the high-altitude river breeze with loose strands dancing in the air. "
            "Wearing an elegant modern pearl-white silk halterneck slip dress, holding a slender crystal flute of champagne with gentle bubbles. "
            "Glistening Huangpu River reflections and glowing historic colonial architecture in creamy out-of-focus background, Leica M11 50mm f/1.4 Summilux, cinematic poetry, timeless elegance."
        )
    },
    {
        "id": "day08_02_western_rooftop",
        "region": "【欧美·巴黎晚风】",
        "location": "蒙马特高地露台吧 · 塞纳河暮色与法式优雅",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261802,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous European woman seated at an intimate Parisian rooftop terrace bar at dusk (巴黎天台暮色、法式浪漫神颜、古典高贵骨相、无暇瓷白肌、绝无雀斑、绝非浓妆假面、五官舒展精致). "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, luminous soft candlelight illumination. "
            "Exquisite classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel-brown eyes with long natural dark lashes, gentle enchanting smile, natural soft rose lips. "
            "Chestnut brown wavy hair casually swept into a loose French chignon with delicate wispy bangs, a few loose curls framing her neck. "
            "Wearing an off-the-shoulder minimalist black silk top with delicate spaghetti straps, delicate gold pendant, holding a chilled French 75 cocktail glass. "
            "Warm amber candle on the small bistro table, purple-navy twilight Paris skyline and distant glowing Eiffel Tower lights softly blurred in creamy bokeh, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day08_03_japan_roppongi",
        "region": "【日本·港区微醺】",
        "location": "东京六本木高空露台 · 昭和电影感与城市夜色",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261803,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily beautiful young Japanese woman leaning gently against the glass balcony of a high-rise Tokyo rooftop lounge (东京六本木天台微醺、清冷温润昭和画报神韵、易碎感与贵气并存、五官精致舒展、绝无浓妆假面). "
            "Petite delicate Japanese facial contours, soft oval jawline, slightly dewy expressive dark eyes looking thoughtfully at the viewer with profound tender emotion, natural fresh nude-peach lip gloss. "
            "Translucent glowing fair porcelain skin softly reflecting warm ambient fairy lights, zero blemish, natural clear complexion. "
            "Dark silky shoulder-length hair gently swept by the Tokyo night breeze, wearing an elegant midnight-blue silk camisole and a draped fine cream cashmere cardigan off one shoulder. "
            "Holding a highball glass with an oversized clear ice sphere, glowing Tokyo Tower warm orange silhouette bokeh in the twilight distance, Hasselblad X2D 90mm lens, cinematic Japanese drama atmosphere."
        )
    },
    {
        "id": "day08_04_korea_gangnam",
        "region": "【韩国·江南清潭】",
        "location": "清潭洞顶层露天艺廊 · 汉江暮色与财阀千金",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261804,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm photograph of an extraordinarily stunning Korean heiress on a high-end rooftop gallery terrace in Cheongdam-dong overlooking the sunset over the Han River (首尔江南顶层露台、财阀千金松弛感、顶级水光凝脂肌、高颅顶天鹅颈、温润高贵神颜、绝无塑料充气感). "
            "Flawless luminous glass skin with exquisite natural dewy hydration, perfectly symmetrical refined feminine jawline, captivating clear dark almond eyes reflecting the warm golden sunset, naturally plush hydrated petal-rose lips. "
            "Voluminous glossy dark espresso hair with soft side-swept waves framing her high cheekbones. "
            "Wearing an impeccably tailored ivory-cream fine cashmere blazer draped over an oyster-silk slip camisole, single minimalist diamond choker necklace. "
            "Holding a chilled bellini cocktail with a thin peach slice, warm golden hour sun dipping below the Seoul skyline with glittering river reflections, Leica M11 50mm f/1.4 Summilux, Vogue Korea luxury editorial realism."
        )
    },
    {
        "id": "day08_05_mediterranean_amalfi",
        "region": "【地中海·阿马尔菲暮霞】",
        "location": "阿马尔菲悬崖海景露台 · 柠檬树与晚霞微风",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261805,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Mediterranean woman on a cliffside terrace in Amalfi at golden sunset (阿马尔菲悬崖海景露台、地中海意式神颜、深邃棕眸与丰盈黑卷发、无暇暖光凝脂肌、自然松弛、绝无假面怪异感). "
            "Flawless smooth porcelain-olive skin glowing in the warm golden hour sunset light, completely clear of blemishes or freckles. "
            "Sculpted symmetrical classical bone structure, noble straight nasal bridge, captivating large velvety-brown expressive eyes with natural dark lashes, gentle enchanting smile, naturally full defined hydrated rose lips. "
            "Glossy thick dark brunette wavy hair cascading naturally over her bare shoulders in the sea breeze. "
            "Wearing a terracotta-orange pure linen slip dress with delicate straps, holding a chilled Aperol spritz in a large crystal goblet with an orange slice. "
            "Rustic stone balustrade, potted lemon trees, and the shimmering Tyrrhenian Sea reflecting golden pink sunset clouds below, Contax T2 35mm f/2.8 lens, Italian holiday cinema masterpiece."
        )
    },
    {
        "id": "day08_06_slavic_prague",
        "region": "【斯拉夫·布拉格金顶】",
        "location": "伏尔塔瓦河畔露台 · 查理大桥金色暮光与哥特尖顶",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261806,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily beautiful Eastern European woman at an elevated terrace overlooking Prague at golden twilight (布拉格天台暮色、东欧斯拉夫翡翠猫眼神颜、高颅顶精致小脸、清透发光瓷肌、高贵清冷从容、绝无怪异感). "
            "Flawless golden ratio facial symmetry, razor-sharp delicate jawline, noble straight nose, captivating piercing emerald-green almond eyes reflecting golden sunlight, soft hydrated nude-rose lips with calm gentle smile. "
            "Glossy ash-brown wavy hair gently lifted by the evening breeze, falling elegantly over a high-neck emerald-green liquid silk blouse. "
            "Holding a slender crystal flute of sparkling white wine, leaning gracefully against an antique wrought-iron terrace railing. "
            "Historic red rooftops, Charles Bridge, and glowing spires of Prague bathed in molten golden sunset light in the creamy background bokeh, Leica M11 50mm f/1.4 Summilux, timeless European editorial realism."
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

def wait_for_completion(pid, dst_file, art_file, timeout=300):
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
                        shutil.copy(src_file, art_file)
                        print(f"-> Saved: {dst_file.name}", flush=True)
                        return True
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return False

def make_6grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 08 6-Grid showcase board...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    w, h = cards[0].size  # 576, 1024
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + w * 2
    board_h = header_h + margin + (h + card_title_h) * 3 + margin + footer_h
    
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
    draw.text((margin + 10, 35), "Day 08 · 暮色微醺 · 城市天际线与露台酒廊 (6张全集)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 08: Twilight Skyline & Rooftop Cocktails · 6 Global Archetypes", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·外滩暮色】", "外滩高空露天吧 · 江景流光与香槟微风 · 古典仙姿"),
        ("【欧美·巴黎晚风】", "蒙马特高地露台吧 · 塞纳河暮色与法式优雅 · 零雀斑瓷白肌"),
        ("【日本·港区微醺】", "东京六本木高空露台 · 昭和电影感与城市夜色 · 温润清冷"),
        ("【韩国·江南清潭】", "清潭洞顶层露天艺廊 · 汉江暮色与财阀千金 · 顶级水光肌"),
        ("【地中海·阿马尔菲暮霞】", "悬崖海景露台 · 柠檬树与晚霞微风 · 意式复古浓颜"),
        ("【斯拉夫·布拉格金顶】", "伏尔塔瓦河畔露台 · 查理大桥金色暮光与哥特尖顶 · 翡翠猫眼")
    ]

    for idx, card in enumerate(cards):
        col = idx % 2
        row = idx // 2
        
        x = margin + col * (w + margin)
        y = header_h + margin + row * (h + card_title_h + margin)
        
        board.paste(card, (x, y))
        
        tx_main, tx_sub = labels[idx]
        text_y_main = y + h + 10
        text_y_sub = text_y_main + 26
        draw.text((x + 10, text_y_main), tx_main, fill=(30, 30, 35), font=font_med)
        draw.text((x + 10, text_y_sub), tx_sub, fill=(110, 115, 125), font=font_sm)

    foot_y = board_h - footer_h + 18
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism 6-Pack Series | Intel Arc A750 XPU Acceleration", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Day 08 (6-Photo Set)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 08: Twilight Skyline & Rooftop Cocktails — 6 Global Beauties (Full 4K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 08】暮色微醺 · 城市天际线与露台酒廊 · 全球6大神颜大片 · 4K超清原图`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, GoldenHour, RooftopLounge, HighFashion, FilmGrain, Glamour, Exclusive, 6PhotoSet`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day08_twilight_cocktails_6grid.png`
2. **超清无损单图附件 (6 Standalone High-Res Attachments)**:
   - `day08_01_china_skyline.png` (【中国·外滩暮色】外滩高空露天吧 · 江景流光与香槟微风 · 古典仙姿)
   - `day08_02_western_rooftop.png` (【欧美·巴黎晚风】蒙马特高地露台吧 · 塞纳河暮色与法式优雅 · 零雀斑瓷白肌)
   - `day08_03_japan_roppongi.png` (【日本·港区微醺】东京六本木高空露台 · 昭和电影感与城市夜色 · 温润清冷)
   - `day08_04_korea_gangnam.png` (【韩国·江南清潭】清潭洞顶层露天艺廊 · 汉江暮色与财阀千金 · 顶级水光肌)
   - `day08_05_mediterranean_amalfi.png` (【地中海·阿马尔菲暮霞】悬崖海景露台 · 柠檬树与晚霞微风 · 意式复古浓颜)
   - `day08_06_slavic_prague.png` (【斯拉夫·布拉格金顶】伏尔塔瓦河畔露台 · 查理大桥金色暮光与哥特尖顶 · 翡翠猫眼)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 08: Twilight Skyline & Rooftop Cocktails (6 Global Beauties)
全球纪实神颜日更 · Day 08 · 暮色微醺 · 城市天际线与露台酒廊 (6张全集)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Daily Candid Realism! Today, we expand our daily series to a brand new 6-photo grand edition.

As golden hour fades into deep violet dusk, high-altitude city breezes sweep across open rooftop lounges around the world. In Day 08, we capture six breathtaking, original cultural beauties holding chilled cocktails against iconic twilight skylines:
• China: High above the Shanghai Bund, river reflections and historic colonial architecture bathed in champagne bubbles.
• Western Europe: Montmartre rooftop terrace in Paris, delicate black silk camisole and distant glowing Eiffel Tower lights.
• Japan: Roppongi skyline lounge in Tokyo, midnight-blue silk, soft cashmere and nostalgic Showa cinema depth.
• Korea: Cheongdam-dong penthouse gallery terrace, luminous glass skin glowing in the golden sunset over the Han River.
• Mediterranean: Amalfi cliffside lemon terrace overlooking the pink Tyrrhenian Sea, terracotta linen and chilled spritz.
• Eastern Europe: Vltava river terrace in Prague, molten golden light reflecting off Gothic spires and emerald-green cat eyes.

Zero real celebrity names, zero artificial waxiness, zero heavy makeup mask. Pure high-definition optical film realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Moments / 今日六组高光

1. 🇨🇳 China: Bund Twilight & Champagne · 外滩暮色
• Scene: Open-air rooftop lounge high above the Bund, river breeze dancing through silk.
• Optics: Leica M11 50mm f/1.4 Summilux, cinematic poetry.
• Details: Classical swan neck, jade-translucent porcelain skin, ivory silk halterneck slip dress, chilled champagne flute, golden river reflections.

2. 🇫🇷 Western Europe: Parisian Twilight Terrace · 巴黎晚风
• Scene: Intimate Parisian bistro balcony in Montmartre overlooking twilight rooftops.
• Optics: Contax T2 35mm f/2.8 lens, legendary European cinema realism.
• Details: Flawless porcelain skin with zero freckles, wide hazel-brown eyes, loose French chignon, off-the-shoulder black silk top, French 75 cocktail.

3. 🇯🇵 Japan: Roppongi High-Rise Breeze · 港区微醺
• Scene: Tokyo rooftop lounge balcony, glowing Tokyo Tower bokeh in the twilight distance.
• Optics: Hasselblad X2D 90mm lens, gentle Showa film nostalgia.
• Details: Petite oval jawline, tender expressive eyes, glowing fair complexion, midnight-blue silk camisole with cream cashmere cardigan, highball glass with crystal clear sphere ice.

4. 🇰🇷 Korea: Cheongdam Penthouse Sunset · 江南清潭
• Scene: Elevated gallery terrace in Cheongdam-dong overlooking the golden Han River sunset.
• Optics: Leica M11 50mm f/1.4 Summilux, luxury editorial realism.
• Details: Luminous glass skin, calm aristocratic gaze, soft rose lips, cream cashmere blazer over champagne satin slip dress, chilled bellini with peach slice.

5. 🇮🇹 Mediterranean: Amalfi Cliffside Spritz · 阿马尔菲暮霞
• Scene: Rustic stone cliff terrace in Amalfi surrounded by lemon trees at golden hour.
• Optics: Contax T2 35mm f/2.8 lens, Italian holiday cinema romance.
• Details: Smooth porcelain-olive skin, deep velvety dark eyes, dark chocolate wavy hair, terracotta linen dress, chilled Aperol spritz in crystal goblet.

6. 🇨🇿 Eastern Europe: Prague Golden Spire Dusk · 布拉格金顶
• Scene: Historic terrace overlooking the Charles Bridge and Vltava River at twilight.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless European elegance.
• Details: Golden ratio facial symmetry, captivating emerald-green eyes, high-neck emerald silk blouse, sparkling white wine flute, molten golden horizon.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Twilight Lighting & Atmospheric Bokeh: 精确模拟黄昏日落向深蓝暮色过渡时刻（Blue Hour & Golden Hour）的自然光比，融合烛光暖光与城市霓虹散景。
• Pristine Skin Textures: 严格调优面部微积分提示词，杜绝任何生硬扭曲或不自然的怪异感，展现自然通透、零瑕疵、零雀斑的顶级骨相质感。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 08 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (576 × 1024 无损超清原图)

Which twilight moment resonates with your aesthetic the most? Let me know in the comments below!
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
        
        new_row = """| **Day 08** | **《暮色微醺 · 城市天际线与露台酒廊 (6张全集)》**<br>外滩高空江景、巴黎蒙马特暮色、六本木天台微醺、清潭洞汉江晚霞、阿马尔菲悬崖海景、布拉格查理大桥金顶 | [`experiments/global_beauties_day08/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/PATREON_POST.md) | [6 宫格母版大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/day08_twilight_cocktails_6grid.png) | 6 张超清原图 |
---

"""
        if "Day 08" not in table_part:
            table_part += new_row
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(table_part + rest_part)
            print("Updated PATREON_SERIES_INDEX.md with Day 08 6-pack successfully!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 08 6-Pack - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        if dst_file.exists() and dst_file.stat().st_size > 50000:
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

        ok = wait_for_completion(pid, dst_file, art_file)
        if ok:
            generated_paths.append(dst_file)
        else:
            print(f"  Failed for {t['id']}", flush=True)

    if len(generated_paths) == 6:
        board_file = OUTPUT_DIR / "day08_twilight_cocktails_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day08_twilight_cocktails_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 08 6-Pack generation, 6-grid board, PATREON_POST.md, and master index updated successfully!", flush=True)

if __name__ == "__main__":
    main()
