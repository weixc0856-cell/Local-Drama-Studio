"""
Generate Supermodel Special Issue 01: 6-Photo Grand Upgrade
(Victoria's Elite: Global Supermodel Special Issue 01 · 6 Legendary Archetypes)
1. South America (Brazil): Gisele Bündchen & Adriana Lima (黄金古铜肌、狼眸、九头身霸主)
2. South Africa: Candice Swanepoel (维密糖糖、黄金腰臀比、芭比脸与粉白条纹丝绸晨袍)
3. Eastern Europe (Slavic): Irina Shayk & Natalia Vodianova (锋利高颧骨、深邃猫系绿眸、黑丝缎高开衩)
4. East Asia: Sui He & Liu Wen (何穗发光冷白皮仙姑、流光双翼、东方高级脸大女主)
5. Northern Europe (Nordic): Doutzen Kroes & Elsa Hosk (金发刀马旦、通透冰蓝双眸、健美紧致身段)
6. Australia / Global: Miranda Kerr & Barbara Palvin (猫系甜心天使、标志性迷人酒窝与水蓝缎袍)
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
        "id": "vs01_01_brazil_gisele_lima",
        "region": "【南美·巴西天神】吉赛尔·邦辰与利马 (黄金古铜肌与九头身霸主)",
        "location": "维密大秀后台灯光通道 · 统治级气场",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20262101,
        "steps": 20,
        "prompt": (
            "Breathtaking cinematic 35mm photograph of an extraordinarily gorgeous Brazilian supermodel, capturing the legendary runway power of Gisele Bündchen and the fierce feline sensuality of Adriana Lima (维密巴西天神超模、吉赛尔邦辰台步气场、利马美洲豹般野性迷人、黄金微晒古铜肌、九头身顶级比例、绝无浓妆假面). "
            "Sculpted European-Latina bone structure, noble straight high nasal bridge, deep alluring dark hazel eyes with intense magnetic gaze, natural full hydrated lips. "
            "Glowing sun-kissed honey-bronze skin with natural micro-texture and subtle body shimmer, toned athletic abdomen and slender sculpted collarbones. "
            "Voluminous sun-bleached golden-brown beach waves violently whipped by runway wind machines with glowing backlit highlights. "
            "Wearing an unbuttoned champagne-gold liquid satin dressing robe over an exquisite golden crystal lingerie set, backstage golden runway light beams cutting through atmospheric haze, shot on Hasselblad H6D-100c 100mm lens, Vogue runway editorial masterpiece."
        )
    },
    {
        "id": "vs01_02_south_africa_candice",
        "region": "【南非·黄金腰臀天使】坎蒂丝·斯瓦内普尔 (维密糖糖与粉白条纹丝袍)",
        "location": "维密后台好莱坞化妆镜前 · 芭比神颜与香氛",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20262102,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily stunning South African Victoria's Secret Angel, embodying the iconic beauty of Candice Swanepoel (维密经典糖糖天使、黄金腰臀比、芭比般精致无暇神颜、绝顶超模身材、绝非浓妆). "
            "Flawless clear porcelain skin with luminous natural glow, completely blemish-free and zero freckles. "
            "Baby-doll supermodel facial proportions, high refined cheekbones, captivating sparkling sapphire-blue eyes with natural long dark lashes, enchanting sweet playful smile, natural glossy soft pink lips. "
            "Cascading voluminous honey-blonde beach waves falling effortlessly over her shoulders. "
            "Wearing the iconic Victoria's Secret candy-pink and white striped satin backstage kimono robe loosely tied, revealing toned collarbones. "
            "Standing before a glowing backstage Hollywood vanity mirror surrounded by warm round light bulbs, holding a vintage crystal perfume atomizer bottle, soft warm backstage atmosphere, Contax T2 35mm f/2.8 lens, legendary Victoria's Secret Fashion Show realism."
        )
    },
    {
        "id": "vs01_03_slavic_irina_shayk",
        "region": "【东欧·冷艳高定女王】伊莉娜·莎伊克与水果娜 (锋利高颧骨与猫系绿眸)",
        "location": "法国里维埃拉私人游艇露台 · 黑丝缎高开衩",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20262103,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Eastern European supermodel, capturing the razor-sharp high-fashion glamour of Irina Shayk and the aristocratic beauty of Natalia Vodianova (东欧斯拉夫顶级超模、伊莉娜莎伊克冷艳锋利骨相、深邃猫系绿眼、维密高定大片、绝无假面感). "
            "Flawless smooth porcelain skin with natural radiant glow, completely clear and smooth with zero freckles. "
            "High chiseled cheekbones, sharp elegant jawline, captivating piercing emerald-green eyes with intense feline magnetism, naturally full plump nude-rose hydrated lips. "
            "Sleek glossy dark chocolate-brown hair with soft wind-blown waves. "
            "Wearing a tailored black liquid silk slip gown with thin straps and a daring high side slit, standing on the teak deck of a luxury yacht in the French Riviera at dusk. "
            "Twilight Mediterranean sea breeze, distant Cannes city lights glowing in soft creamy bokeh, cold glass of vintage champagne, shot on Leica M11 50mm f/1.4 Summilux, high-fashion editorial perfection."
        )
    },
    {
        "id": "vs01_04_east_asia_he_sui",
        "region": "【东方·发光冷白皮仙姑】何穗与刘雯 (流光白翼与高级脸大女人气场)",
        "location": "维密聚光灯T台中心 · 镜面镜光与白羽流光",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.70,
        "seed": 20262104,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm photograph of an extraordinarily stunning East Asian supermodel on the Victoria's Secret runway, capturing the iconic incandescent glowing cool-white skin and ethereal elegance of Sui He and the high-fashion charisma of Liu Wen (维密东方面孔奇迹、何穗发光冷白皮仙姑、刘雯高级大女人气场、清冷骨相与流光双翼、绝无假面浓妆). "
            "Delicate East Asian classical high-fashion bone structure, smooth noble jawline and slender swan-like neck, soulful deep dark almond eyes looking directly into the camera with radiant confidence, dimpled charming smile, natural hydrated rose petal lips. "
            "Luminous, almost glowing cool-white porcelain jade skin that reflects runway spotlights, completely smooth and translucent. "
            "Silky dark hair parted in the middle and blowing gracefully behind her in the runway breeze. "
            "Wearing a translucent sheer moon-white and silver crystal lingerie set with flowing diaphanous organza cape that billows like wings. "
            "Reflective glossy runway catwalk floor, brilliant spotlight beams illuminating sparkling airborne glitter dust, shot on Hasselblad X2D 90mm lens, legendary Victoria's Secret runway moment."
        )
    },
    {
        "id": "vs01_05_nordic_doutzen_elsa",
        "region": "【北欧·金发刀马旦天使】杜晨·科洛斯与艾尔莎·霍斯卡 (通透冰蓝双眸与健美体态)",
        "location": "大理石海景阳光露台 · 维密健美力量感",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20262105,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Nordic Victoria's Secret Angel, embodying the athletic goddess power of Doutzen Kroes and the high-fashion beauty of Elsa Hosk (北欧荷兰维密天使、杜晨科洛斯金发刀马旦、艾尔莎霍斯卡、通透冰蓝双眸、健美紧致身段、绝非浓妆假面). "
            "Flawless clear porcelain skin with luminous natural sunlit glow, completely blemish-free and zero freckles. "
            "Strong refined Nordic bone structure, noble high straight nasal bridge, captivating icy crystal-blue eyes with intense radiance, warm confident smile, natural soft nude-rose hydrated lips. "
            "Voluminous thick sunlit golden-blonde beach waves casually falling over her shoulders. "
            "Wearing an open ivory-cream silk satin kimono robe over a minimalist champagne lingerie set, toned athletic abs and sculpted collarbones. "
            "Standing on a sunlit marble terrace overlooking sparkling turquoise ocean water in the bright afternoon sun, Contax T2 35mm f/2.8 lens, legendary Victoria's Secret Summer Glamour realism."
        )
    },
    {
        "id": "vs01_06_aus_miranda_barbara",
        "region": "【澳洲·猫系甜心天使】米兰达·可儿与芭芭拉·帕尔文 (标志性迷人酒窝与水蓝缎袍)",
        "location": "维密后台花絮抓拍 · 甜美酒窝神颜与水晶晨袍",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20262106,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily stunning Victoria's Secret Angel, capturing the signature doll-like dimpled charm of Miranda Kerr and the seductive feline innocence of Barbara Palvin (澳洲维密天使、米兰达可儿甜美酒窝神颜、芭芭拉帕尔文猫系无辜灵动、璀璨水晶流光、绝无假面浓妆). "
            "Flawless smooth porcelain skin with natural peach flush on cheeks, zero blemish and zero freckles. "
            "Round delicate baby-doll facial structure with enchanting deep dimples on both cheeks, captivating bright azure-blue cat-like almond eyes, sweet radiant smile, naturally full glossy pink lips. "
            "Glossy dark caramel-brown wavy hair gently lifted by the runway wind machine. "
            "Wearing an exquisite pastel baby-blue silk satin dressing robe loosely tied, adorned with delicate crystal embroidery along the lapels, backstage Hollywood vanity lights softly blurred in the background, shot on Leica M11 50mm f/1.4 Summilux, iconic Victoria's Secret backstage perfection."
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
    
    # 2 columns x 3 rows
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
    draw.text((margin + 12, 92), "Victoria's Elite: Global Supermodel Special Issue 01 · 6 Legendary Goddess Archetypes", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【南美·巴西天神】吉赛尔·邦辰与利马", "维密后台灯光通道 · 黄金古铜肌 · 九头身台步气场"),
        ("【南非·黄金腰臀天使】坎蒂丝·斯瓦内普尔", "维密后台梳妆镜前 · 糖糖天使神颜 · 粉白条纹丝绸晨袍"),
        ("【东欧·冷艳高定女王】伊莉娜·莎伊克与水果娜", "里维埃拉私人游艇 · 锋利高颧骨 · 墨黑真丝高开衩礼服"),
        ("【东方·发光冷白皮仙姑】何穗与刘雯", "维密聚光T台中心 · 何仙姑流光冷白皮 · 绝美薄纱轻翼"),
        ("【北欧·金发刀马旦天使】杜晨·科洛斯与艾尔莎", "大理石海景阳光露台 · 冰蓝双眸 · 健美紧致身段与缎面晨袍"),
        ("【澳洲·猫系甜心天使】米兰达·可儿与芭芭拉", "维密后台花絮抓拍 · 甜美酒窝神颜 · 水晶水蓝丝绸晨袍")
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
   - `vs01_01_brazil_gisele_lima.png` (【南美·巴西天神】吉赛尔·邦辰与利马 · 黄金古铜肌 · 九头身台步气场)
   - `vs01_02_south_africa_candice.png` (【南非·黄金腰臀天使】坎蒂丝·斯瓦内普尔 · 糖糖天使神颜 · 粉白条纹丝绸晨袍)
   - `vs01_03_slavic_irina_shayk.png` (【东欧·冷艳高定女王】伊莉娜·莎伊克与水果娜 · 锋利高颧骨 · 墨黑真丝高开衩礼服)
   - `vs01_04_east_asia_he_sui.png` (【东方·发光冷白皮仙姑】何穗与刘雯 · 维密聚光T台中心 · 何仙姑流光冷白皮 · 绝美薄纱轻翼)
   - `vs01_05_nordic_doutzen_elsa.png` (【北欧·金发刀马旦天使】杜晨·科洛斯与艾尔莎·霍斯卡 · 冰蓝双眸 · 健美紧致身段)
   - `vs01_06_aus_miranda_barbara.png` (【澳洲·猫系甜心天使】米兰达·可儿与芭芭拉·帕尔文 · 甜美酒窝神颜 · 水晶水蓝丝绸晨袍)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Victoria's Elite · Special Issue 01: Backstage Silks & Golden Runway Glamour (6 Iconic Supermodels)
全球超模特辑 01 · 维密天使后台晨袍与T台流光 (6张巅峰神颜全集)

━━━━━━━━━━━━━━━━━━━━

Welcome to our brand new high-fashion exclusive column: Victoria's Elite!

While our Daily Series explores intimate street candids and quiet morning warmth, Victoria's Elite is dedicated to the absolute pinnacle of human physique, high-fashion bone structure, and golden-era runway power.

In this upgraded 6-photo grand edition, we celebrate six legendary supermodel archetypes from across the globe:
• South America (Brazil): The fierce feline dominance of Gisele Bündchen & Adriana Lima with glowing sun-kissed bronze skin.
• South Africa: The golden waist-to-hip ratio and porcelain doll beauty of Candice Swanepoel in the iconic backstage striped silk robe.
• Eastern Europe (Slavic): The chiseled high cheekbones and hypnotic cat-green eyes of Irina Shayk on a Riviera twilight yacht.
• East Asia: The incandescent cool-white glowing skin and celestial wings of Sui He on the glittering Victoria's Secret catwalk.
• Northern Europe (Nordic): The athletic goddess power and icy crystal-blue eyes of Doutzen Kroes & Elsa Hosk in sunlit silk.
• Australia / Global: The signature doll-like dimples and seductive innocence of Miranda Kerr & Barbara Palvin in baby-blue satin.

Zero artificial AI waxiness, zero heavy makeup mask. Pure high-fashion optical magazine realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Supermodel Moments / 今日六组超模高光

1. 🇧🇷 Brazilian Runway Goddess · 黄金古铜肌与九头身霸主
• Scene: Backstage golden runway lights cutting through atmospheric haze, glowing bronze radiance.
• Optics: Hasselblad H6D-100c 100mm lens, Vogue runway editorial sharpness.
• Details: Gisele Bündchen dominant catwalk presence and Adriana Lima feline gaze, golden honey-bronze skin with subtle body shimmer, champagne-gold liquid satin robe, toned athletic physique.

2. 🇿🇦 South African Angel & Iconic Striped Silk · 维密糖糖与后台好莱坞镜
• Scene: Glowing Hollywood vanity mirror backstage surrounded by warm round light bulbs.
• Optics: Contax T2 35mm f/2.8, warm film highlights and backstage luxury ambiance.
• Details: Candice Swanepoel golden ratio silhouette, flawless porcelain baby-doll face, sparkling sapphire-blue eyes, iconic candy-pink and white striped satin backstage kimono robe, crystal perfume atomizer.

3. 🇷🇺 Slavic High-Fashion Royalty · 锋利高颧骨与猫系绿眸
• Scene: Teak deck of a private superyacht on the French Riviera at dusk, twilight Mediterranean breeze.
• Optics: Leica M11 50mm f/1.4 Summilux, high-fashion magazine perfection.
• Details: Irina Shayk razor-sharp bone structure and piercing emerald-green eyes, tailored black liquid silk slip gown with high side slit, cold champagne glass, statuesque athletic poise.

4. 🇨🇳 Celestial East Asian Glow · 何仙姑流光冷白皮与薄纱轻翼
• Scene: Reflective glossy catwalk floor under brilliant crystal spotlight beams, shimmering airborne glitter dust.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial contrast.
• Details: Sui He legendary incandescent glowing cool-white porcelain skin, charming dimpled smile, sheer crystal lingerie with billowing organza wings, regal effortless catwalk stride.

5. 🇳🇱 Nordic Sunlit Athletic Power · 冰蓝双眸与金发刀马旦
• Scene: Sunlit white marble terrace overlooking turquoise Mediterranean water, bright golden afternoon sun.
• Optics: Contax T2 35mm f/2.8 lens, classic Victoria's Secret Summer Glamour realism.
• Details: Doutzen Kroes athletic goddess power and Elsa Hosk icy blue eyes, flawless clear skin, voluminous sunlit golden waves, open ivory silk robe, sculpted collarbones and toned abs.

6. 🇦🇺 Australian Dimpled Angel · 米兰达酒窝与水晶水蓝丝袍
• Scene: Backstage Hollywood vanity mirror lights softly blurred in warm glowing circles.
• Optics: Leica M11 50mm f/1.4 Summilux, delicate skin tones and fine fabric textures.
• Details: Miranda Kerr deep enchanting dimples and Barbara Palvin cat-like blue eyes, soft glossy pink lips, pastel baby-blue silk satin robe adorned with delicate crystal embroidery.

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
        # replace row with 6-photo info
        old_row = "| **特辑 01** | **《维密天使后台晨袍与T台流光》**<br>巴西天神(吉娘娘+利马)、维密糖糖(粉白条纹丝袍)、东欧冷艳(伊莉娜黑丝缎)、东方仙姑(何穗冷白皮流光双翼) | [`experiments/supermodel_vs_special01/`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/PATREON_POST.md) | [4 联排大图](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/vs01_supermodel_showcase_4grid.png) | 4 张超清原图 |"
        new_row = "| **特辑 01** | **《维密天使后台晨袍与T台流光 (6张全集)》**<br>巴西天神(吉娘娘+利马)、维密糖糖(粉白条纹丝袍)、东欧冷艳(伊莉娜黑丝缎)、东方仙姑(何穗流光冷白皮)、北欧刀马旦(杜晨+艾尔莎)、猫系甜心(米兰达酒窝+芭芭拉) | [`experiments/supermodel_vs_special01/`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/PATREON_POST.md) | [6 联排大图](file:///d:/Local-Drama-Studio/experiments/supermodel_vs_special01/vs01_supermodel_showcase_6grid.png) | 6 张超清原图 |"
        content = content.replace(old_row, new_row)
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with 6-photo info!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[VS Special 01 (6-Pack) - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
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
        print("\nSupermodel Special 01 (6-Pack) completed successfully!", flush=True)

if __name__ == "__main__":
    main()
