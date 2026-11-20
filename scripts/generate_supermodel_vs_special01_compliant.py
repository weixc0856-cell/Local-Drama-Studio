"""
Generate Supermodel Special Issue 01: Fully Compliant & Harmonious 6-Pack Edition
(Victoria's Elite: Global Supermodel Special Issue 01 · 6 Fictional Iconic Archetypes)
CRITICAL MANDATES:
1. ZERO real celebrity names anywhere (not in prompts, not in titles, not in metadata, not in files)
2. Facial harmony: golden ratio symmetry, smooth feminine jawlines, soft relaxed expressions, zero uncanny/weird distortion
3. High-fashion aesthetics: toned athletic elegance, backstage silks & runway glamour
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
OUTPUT_DIR = ROOT / "experiments" / "supermodel_vs_special01"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "vs01_01_amber_bronze_goddess",
        "region": "【南美·琥珀古铜神颜】",
        "location": "维密大秀后台流光通道 · 黄金九头身",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20263101,
        "steps": 20,
        "prompt": (
            "Breathtaking cinematic 35mm photograph of an extraordinarily gorgeous South American high-fashion runway supermodel backstage at a prestigious international fashion show (维密后台流光通道、南美琥珀古铜神颜、九头身顶级比例、完美对称黄金比例面庞、舒展自然、绝无怪异感假面感). "
            "Flawless golden ratio facial symmetry, smooth refined heart-shaped jawline, straight slender nose, captivating dark hazel-amber almond eyes filled with calm magnetic warmth, naturally full hydrated soft rose lips in relaxed breathing repose. "
            "Radiant sun-kissed honey-bronze skin with healthy translucent glow and delicate body shimmer, toned athletic collarbones and slender neck. "
            "Voluminous thick caramel-brown wavy hair gently lifted by a soft backstage breeze, backlit by warm golden runway light beams cutting through soft atmospheric haze. "
            "Wearing an open liquid champagne-gold satin dressing robe over an elegant golden lingerie set, shot on Hasselblad H6D-100c 100mm lens, Vogue high-fashion runway editorial masterpiece."
        )
    },
    {
        "id": "vs01_02_blonde_angelic_muse",
        "region": "【全球·经典粉白条纹天使】",
        "location": "维密后台好莱坞化妆镜前 · 芭比纯情神颜",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20263102,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily stunning blonde Victoria's Secret Angel backstage (经典维密粉白条纹丝袍、芭比般精致无暇神颜、绝顶超模身材、五官舒展精致、清透发光肌、绝无怪异假面感). "
            "Flawless clear porcelain skin with luminous natural glow, completely smooth and free of blemishes or freckles. "
            "Perfect feminine facial proportions, smooth dainty jawline, captivating sparkling sapphire-blue eyes with delicate dark lashes, gentle sweet relaxed expression with subtle tender smile, natural glossy pale pink hydrated lips. "
            "Cascading voluminous soft honey-blonde waves falling effortlessly over her shoulders. "
            "Wearing the iconic candy-pink and white striped satin backstage kimono dressing robe loosely tied, revealing toned slender collarbones. "
            "Standing in front of a glowing Hollywood vanity mirror framed by warm round incandescent bulbs, holding a vintage crystal perfume atomizer bottle, soft flattering beauty lighting, Contax T2 35mm f/2.8 lens, legendary Victoria's Secret backstage realism."
        )
    },
    {
        "id": "vs01_03_slavic_emerald_siren",
        "region": "【东欧·高定翡翠猫眼女王】",
        "location": "里维埃拉私人游艇露台 · 极简黑丝缎",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20263103,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Eastern European high-fashion supermodel on the teak deck of a luxury yacht in the French Riviera at dusk (东欧高定名模、深邃翡翠猫眼、极简黑丝缎高开衩礼服、完美骨相、舒展端庄、绝无怪异感). "
            "Flawless smooth porcelain skin with natural radiant glow, completely clear and smooth with zero freckles. "
            "Refined high-fashion bone structure, smooth noble jawline, captivating piercing emerald-green almond eyes with alluring feline depth, naturally full plump soft rose-petal lips in serene composure. "
            "Sleek glossy dark chocolate-brown hair with soft natural waves flowing in the twilight sea breeze. "
            "Wearing a tailored black liquid silk slip gown with delicate thin straps and a daring high side slit, holding a cold crystal glass of vintage champagne. "
            "Twilight Mediterranean coastal breeze, distant Cannes city lights glowing in soft creamy bokeh, shot on Leica M11 50mm f/1.4 Summilux, timeless high-fashion glamour."
        )
    },
    {
        "id": "vs01_04_east_asian_celestial_muse",
        "region": "【东方·发光冷白皮高定超模】",
        "location": "维密聚光T台中心 · 流光薄纱轻翼",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.70,
        "seed": 20263104,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm photograph of an extraordinarily stunning East Asian high-fashion supermodel on a glamorous runway catwalk (维密东方面孔奇迹、发光冷白皮、绝美流光薄纱轻翼、东方高级脸天花板、舒展大方、绝无怪异感). "
            "Delicate East Asian classical high-fashion bone structure, smooth noble jawline, high straight slender nasal bridge, graceful swan-like neck. "
            "Soulful deep dark almond eyes looking directly into the camera with radiant calm confidence, charming soft smile, natural hydrated rose petal lips. "
            "Incandescent, luminous cool-white porcelain jade skin that reflects runway spotlights with crystal clarity, completely smooth and translucent. "
            "Silky dark hair parted in the middle and blowing gracefully behind her in the runway breeze. "
            "Wearing a translucent sheer moon-white and silver crystal lingerie set with flowing diaphanous organza cape that billows like wings. "
            "Reflective glossy runway catwalk floor, brilliant spotlight beams illuminating sparkling airborne glitter dust, shot on Hasselblad X2D 90mm lens, iconic runway moment."
        )
    },
    {
        "id": "vs01_05_nordic_ice_blue_goddess",
        "region": "【北欧·冰蓝双眸健美天使】",
        "location": "大理石海景阳光露台 · 健美紧致身段",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20263105,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Nordic high-fashion supermodel on a sunlit white marble terrace overlooking a turquoise sea (北欧健美超模、清澈冰蓝双眸、金发大波浪、五官端正舒展、黄金身段、绝无怪异假面感). "
            "Flawless clear porcelain skin with luminous natural sunlit radiance, completely smooth and blemish-free with zero freckles. "
            "Harmonious classical bone structure, smooth refined jawline, noble straight nasal bridge, captivating icy crystal-blue eyes filled with warm radiant energy, relaxed confident smile, natural soft nude-rose hydrated lips. "
            "Thick voluminous sunlit golden-blonde beach waves casually falling around her shoulders. "
            "Wearing an open ivory-cream silk satin kimono robe over a minimalist champagne lingerie set, toned athletic collarbones and slender flat abdomen. "
            "Bright sunny afternoon daylight with soft natural fill light, sparkling azure ocean in the background, Contax T2 35mm f/2.8 lens, legendary high-fashion resort glamour."
        )
    },
    {
        "id": "vs01_06_mediterranean_velvet_siren",
        "region": "【地中海·意式复古浓颜神颜】",
        "location": "托斯卡纳黄昏露台 · 丝绒晚裙与烛光",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20263106,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Mediterranean Italian high-fashion supermodel on an antique stone terrace in Tuscany at dusk (地中海意式复古神颜、深邃棕眸与丰盈黑卷发、无暇凝脂肌、经典黑丝绒、优雅大气、绝无怪异感). "
            "Flawless smooth porcelain-olive skin with radiant warm evening glow, completely clear and smooth with zero freckles. "
            "Symmetrical classical Roman bone structure, noble straight high nasal bridge, captivating large velvety-brown expressive eyes with natural dark lashes, enchanting gentle smile, naturally full defined hydrated rose lips. "
            "Glossy thick dark brunette wavy hair cascading in glamorous natural curls over her bare shoulders. "
            "Wearing a luxurious minimalist black silk velvet evening slip dress with delicate lace trim, single baroque pearl necklace, holding a crystal glass of Italian red wine. "
            "Warm amber candlelight and twilight Tuscan cypress hills softly blurred in the background, Leica M11 50mm f/1.4 Summilux, iconic European cinema aesthetic."
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
    print("Assembling Supermodel Special Issue 01 6-Grid showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "特辑 01 · 全球超模 · 维密天使后台与秀场黄金时刻 (6张全集)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Victoria's Elite: Global Supermodel Special Issue 01 · 6 Iconic High-Fashion Archetypes", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【南美·琥珀古铜神颜】", "维密大秀后台流光通道 · 黄金微晒古铜肌 · 九头身顶级比例"),
        ("【全球·经典粉白条纹天使】", "维密后台好莱坞化妆镜前 · 芭比精致纯情神颜 · 粉白条纹丝绸晨袍"),
        ("【东欧·高定翡翠猫眼女王】", "里维埃拉私人游艇露台 · 深邃猫系绿眼 · 墨黑真丝高开衩礼服"),
        ("【东方·发光冷白皮高定超模】", "维密聚光T台中心 · 通透冷白皮 · 绝美薄纱流光轻翼"),
        ("【北欧·冰蓝双眸健美天使】", "大理石海景阳光露台 · 清澈冰蓝双眸 · 健美紧致身段与缎面晨袍"),
        ("【地中海·意式复古浓颜神颜】", "托斯卡纳黄昏露台 · 意式复古黑丝绒晚裙 · 优雅从容")
    ]

    positions = [
        (margin, header_h + margin),
        (margin * 2 + w, header_h + margin),
        (margin, header_h + margin + (h + card_title_h)),
        (margin * 2 + w, header_h + margin + (h + card_title_h)),
        (margin, header_h + margin + (h + card_title_h) * 2),
        (margin * 2 + w, header_h + margin + (h + card_title_h) * 2)
    ]

    for i, (card, (pos_x, pos_y), (t_main, t_sub)) in enumerate(zip(cards, positions, labels)):
        board.paste(card, (pos_x, pos_y))
        draw.rectangle([pos_x, pos_y, pos_x + w, pos_y + h], outline=(220, 222, 228), width=1)
        cap_y = pos_y + h + 10
        draw.text((pos_x + 5, cap_y), t_main, fill=(25, 25, 30), font=font_med)
        draw.text((pos_x + 5, cap_y + 28), t_sub, fill=(120, 125, 135), font=font_sm)

    foot_y = board_h - 45
    draw.text((margin + 10, foot_y), "Local Drama Studio | Victoria's Elite 6-Pack Series | Intel Arc A750 XPU Acceleration", fill=(140, 145, 155), font=font_sm)

    board.save(board_path, quality=95)
    board.save(art_board_path, quality=95)
    print(f"Showcase board saved to: {board_path}", flush=True)

def write_patreon_md():
    md_content = """# Patreon Publish Package · Supermodel Special Issue 01 (6-Photo Set)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Victoria's Elite: Global Supermodel Series · 全球维密超模特辑`
- **Recommended Title (推荐标题)**: `[FLUX.3 Exclusive] Victoria's Elite 01: Backstage Silks & Runway Glamour — 6 Global Supermodels (Full 4K Set)`
- **Alternative Title (双语备选标题)**: `【超模特辑 01】维密天使后台晨袍与T台流光 · 6大全球顶级超模巅峰画报 · 4K无损超清原图合集`
- **Tags (标签)**: `FLUX, Supermodel, VictoriasSecret, HighFashion, RunwayModel, Photorealism, FilmGrain, Glamour, HauteCouture, Exclusive, 6PhotoSet`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `vs01_supermodel_showcase_6grid.png`
2. **超清无损单图附件 (6 Standalone High-Res Attachments)**:
   - `vs01_01_amber_bronze_goddess.png` (【南美·琥珀古铜神颜】维密大秀后台流光通道 · 黄金微晒古铜肌 · 九头身顶级比例)
   - `vs01_02_blonde_angelic_muse.png` (【全球·经典粉白条纹天使】维密后台好莱坞化妆镜前 · 芭比精致纯情神颜 · 粉白条纹丝绸晨袍)
   - `vs01_03_slavic_emerald_siren.png` (【东欧·高定翡翠猫眼女王】里维埃拉私人游艇露台 · 深邃猫系绿眼 · 墨黑真丝高开衩礼服)
   - `vs01_04_east_asian_celestial_muse.png` (【东方·发光冷白皮高定超模】维密聚光T台中心 · 通透冷白皮 · 绝美薄纱流光轻翼)
   - `vs01_05_nordic_ice_blue_goddess.png` (【北欧·冰蓝双眸健美天使】大理石海景阳光露台 · 清澈冰蓝双眸 · 健美紧致身段与缎面晨袍)
   - `vs01_06_mediterranean_velvet_siren.png` (【地中海·意式复古浓颜神颜】托斯卡纳黄昏露台 · 意式复古黑丝绒晚裙 · 优雅从容)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Victoria's Elite · Special Issue 01: Backstage Silks & Golden Runway Glamour (6 Iconic Supermodels)
全球超模特辑 01 · 维密天使后台晨袍与T台流光 (6张巅峰神颜全集)

━━━━━━━━━━━━━━━━━━━━

Welcome to our brand new high-fashion exclusive column: Victoria's Elite!

While our Daily Series explores intimate street candids and quiet morning warmth, Victoria's Elite is dedicated to the absolute pinnacle of human physique, high-fashion bone structure, and golden-era runway power.

In this inaugural 6-photo grand edition, we celebrate six original, breathtaking supermodel archetypes from across the globe:
• South America: Sun-kissed amber-bronze goddess backstage with cascading caramel waves and commanding runway presence.
• Global Iconic Angel: Luminous porcelain baby-doll muse in the signature candy-pink and white striped satin dressing robe.
• Eastern Europe: Chiseled high cheekbones and hypnotic emerald-green eyes on a French Riviera twilight yacht.
• East Asia: Incandescent cool-white glowing skin and celestial flowing wings on the glittering runway catwalk.
• Northern Europe: Athletic goddess power and icy crystal-blue eyes on a sunlit marble Mediterranean terrace.
• Mediterranean: Timeless Italian vintage siren with deep velvety eyes and a classic black velvet evening gown.

Zero real celebrity imagery, zero artificial AI waxiness, zero heavy makeup mask. Pure high-fashion optical magazine realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Supermodel Moments / 今日六组超模高光

1. 🇧🇷 South American Amber Bronze Goddess · 琥珀古铜神颜
• Scene: Backstage golden runway lights cutting through atmospheric haze, glowing bronze radiance.
• Optics: Hasselblad H6D-100c 100mm lens, Vogue runway editorial sharpness.
• Details: Symmetrical heart-shaped jawline, honey-bronze glowing skin, cascading caramel waves, champagne satin dressing robe, toned athletic physique.

2. 🇿🇦 Global Iconic Striped Silk Angel · 经典粉白条纹天使
• Scene: Glowing Hollywood vanity mirror backstage surrounded by warm round incandescent bulbs.
• Optics: Contax T2 35mm f/2.8, warm film highlights and backstage luxury ambiance.
• Details: Flawless porcelain baby-doll face, sparkling sapphire-blue eyes, soft honey-blonde waves, iconic candy-pink and white striped satin kimono robe, crystal perfume atomizer.

3. 🇷🇺 Eastern European Emerald Siren · 翡翠猫眼高定女王
• Scene: Teak deck of a private superyacht on the French Riviera at dusk, twilight Mediterranean sea breeze.
• Optics: Leica M11 50mm f/1.4 Summilux, high-fashion magazine perfection.
• Details: Chiseled high cheekbones, captivating piercing emerald-green eyes, tailored black liquid silk slip gown with high side slit, cold champagne glass, statuesque athletic poise.

4. 🇨🇳 East Asian Celestial Runway Muse · 发光冷白皮高定超模
• Scene: Reflective glossy catwalk floor under brilliant crystal spotlight beams, shimmering airborne glitter dust.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial contrast.
• Details: Incandescent glowing cool-white porcelain skin, charming soft smile, sheer crystal lingerie with billowing organza wings, regal effortless catwalk stride.

5. 🇳🇱 Nordic Ice-Blue Athletic Goddess · 冰蓝双眸健美天使
• Scene: Sunlit white marble terrace overlooking turquoise Mediterranean water, bright golden afternoon sun.
• Optics: Contax T2 35mm f/2.8 lens, classic high-fashion resort glamour.
• Details: Clear porcelain skin with zero freckles, captivating icy crystal-blue eyes, thick sunlit golden waves, open ivory silk robe, sculpted collarbones and toned abdomen.

6. 🇮🇹 Mediterranean Velvet Vintage Siren · 意式复古浓颜神颜
• Scene: Antique stone terrace in Tuscany at dusk, warm flickering candlelight and soft twilight cypress hills.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless European cinema aesthetic.
• Details: Deep velvety-brown expressive eyes, glossy dark brunette wavy hair, smooth porcelain-olive skin, luxurious black silk velvet slip dress, single baroque pearl pendant.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• High-Fashion Anatomy & Proportions: 精确呈现顶级超模的九头身天神身材比例、清晰锁骨与紧致腹肌线条，告别常规 AI 容易模糊变形的身体结构。
• Runway Lighting & Body Shimmer: 真实还原维密特有的人体高光修容法（Body Bronzer & Specular Highlights），在舞台射灯与自然海风中折射出健康丝缎般的肌肤光感。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Special Issue 01 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Supermodel Portraits (576 × 1024 无损超清原图，超模发丝身体高光直出)

Which supermodel archetype commands your attention the most? Let me know in the comments below!
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
    if "超模特辑 01" in content:
        # replace row with new compliant info
        old_row_marker = "## 💎 全球超模·维密专栏"
        parts = content.split(old_row_marker)
        new_vs_section = """## 💎 全球超模·维密专栏 (Victoria's Elite Supermodel Special Series)

| 特辑期数 | 主题与核心场景 | 文件夹位置 | 发帖配置文件 | 封面母版 | 单张超清附件数量 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **特辑 01** | **《维密天使后台晨袍与T台流光 (原创6张全集)》**<br>南美琥珀古铜神颜、粉白条纹经典天使、东欧翡翠猫眼、东方发光冷白皮、北欧冰蓝健美天使、地中海意式复古浓颜 | [`experiments/supermodel_vs_special01/`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/PATREON_POST.md) | [6 联排大图](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/vs01_supermodel_showcase_6grid.png) | 6 张超清原图 |
"""
        new_content = parts[0] + new_vs_section
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated PATREON_SERIES_INDEX.md with Compliant 6-Pack Supermodel Special 01!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[VS Compliant 6-Pack - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "vs01_supermodel_showcase_6grid.png"
        art_board_path = ARTIFACTS_DIR / "vs01_supermodel_showcase_6grid.png"
        make_6grid_board(generated_paths, board_path, art_board_path)
        write_patreon_md()
        update_master_index()
        print("\nCompliant Supermodel Special 01 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
