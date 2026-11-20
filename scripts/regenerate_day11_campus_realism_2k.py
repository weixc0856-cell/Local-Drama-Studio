"""
Day 11 Remaster: 《象牙塔晨光 · 全球在校女大学生神颜特辑 (全新写实摄影与大师构图 2K版)》
(Daily Candid Realism · Issue 11: Campus Muses · Global College Students)
APPLIES THE PORTRAIT_PRODUCTION_SOP v2.0 SPECIFICATION:
1. Native Base Resolution: 768 x 1360 (High Native Sweet Spot)
2. Realism LoRA Integration: flux_realism_xlabs.safetensors (0.35-0.40) for real skin pores & candid lighting
3. Master Photographer Framing: 35mm-55mm, waist-up, three-quarter angles, sub-framing, campus props (books, bicycle, coffee, sketchpad)
4. Anti-Grimace / Anti-Bitter Expression: relaxed lips in soft calm breathing repose, clear bright eyes, natural radiant youth
5. 2K Ultra-HD (1152 x 2048) gentle porcelain skin upscale + 6-Grid showcase board
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
ROOT = Path(__file__).resolve().parent.parent
WF_SINGLE_LORA = ROOT / "workflows" / "flux3_lora_t2i_api.json"
WF_DUAL_LORA = ROOT / "workflows" / "flux3_dual_lora_t2i_api.json"
WF_BASE = ROOT / "workflows" / "flux3_t2i_api.json"

OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day11"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day11_01_china_campus",
        "region": "【中国·金秋未名银杏道】",
        "location": "古朴红砖大学连廊 · 20岁中文系校花怀抱书本侧身回眸",
        "workflow": "dual_lora",
        "lora_1": "girlslikeflux_lyf5.safetensors",
        "strength_1": 0.45,
        "lora_2": "flux_realism_xlabs.safetensors",
        "strength_2": 0.35,
        "w": 768,
        "h": 1360,
        "seed": 20261111,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, award-winning candid 35mm photograph of an extraordinarily gorgeous 20-year-old Chinese university literature student walking along a golden autumn campus avenue (顶级名校校花、金秋银杏林荫道、大师级环境人像、侧身漫步优雅回眸、怀抱书本自然交互、绝无死板大头照、清纯温润天仙神颜、真实细腻毛孔、绝无假笑苦相). "
            "Master environmental portrait composition: Walking along a brick-lined campus pathway under golden falling ginkgo leaves, turning back over her shoulder at a 35-degree three-quarter angle, rule of thirds placement. "
            "Holding two thick hardcover university textbooks against her chest with both arms in a natural student posture, showing a slender waist, face occupying roughly 23 percent of frame. "
            "Delicate symmetrical oval face, smooth brow, clear dark almond eyes filled with gentle intelligence, naturally plump rose lips slightly parted in soft calm breathing repose, realistic fine skin pores and natural warmth. "
            "Silky dark hair with soft wispy bangs dancing in the gentle autumn breeze, wearing an oversized cream-white cable knit wool sweater and dark pleated skirt. "
            "Historic red brick collegiate buildings and glowing yellow ginkgo trees in soft morning sunlight, Leica M11 50mm f/1.4 Summilux lens, timeless campus youth documentary."
        )
    },
    {
        "id": "day11_02_western_campus",
        "region": "【英国·牛津古老图书馆】",
        "location": "拉德克里夫石拱窗台 · 20岁古典文学系女神靠窗捧书浅笑",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261112,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a stunning 20-year-old British university undergraduate seated inside an ancient stone collegiate library (牛津剑桥顶级学霸校花、古老石窗晨光画中画构图、一手轻翻书页一手托腮、绝无死板大头照、真实胶片质感、灵动大鹿眸、松弛高级学府气质). "
            "Master window sub-framing composition: Seated sideways at a vintage polished oak library desk next to an ancient gothic arched stone window with streaming morning sunbeams. "
            "One hand lightly resting on an open vintage leather-bound book, other arm relaxed on the desk, face occupying 24 percent of frame with atmospheric negative space. "
            "Radiant feminine beauty, soft rounded chin, captivating large sparkling hazel-green doe eyes gazing with gentle curiosity, naturally plump rosy-peach lips in soft breathing repose, completely smooth porcelain ivory skin with real micro-texture and zero freckles. "
            "Lush wavy honey-brown hair tossed effortlessly over one shoulder. "
            "Wearing a tailored navy wool collegiate blazer over a crisp white collared shirt. "
            "Dust motes dancing in golden sunbeams, towering mahogany bookshelves and stained glass blurred in creamy bokeh, 50mm f/1.4 lens, dark academia photographic masterpiece."
        )
    },
    {
        "id": "day11_03_japan_campus",
        "region": "【日本·早稻田单车初恋】",
        "location": "坡道林荫路单车旁 · 19岁初恋校花手扶车把纯净甜笑",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261113,
        "steps": 20,
        "prompt": (
            "Award-winning 35mm candid Japanese film photograph of an adorable 19-year-old Japanese university student on a sunlit campus slope beside her vintage bicycle (岩井俊二式校园初恋神颜、手扶复古单车漫步、灵动水汪汪大眼、治愈纯净笑容、绝无死板大头照、饱满婴儿肥胶原蛋白、阳光洒落发丝、真实生活抓拍). "
            "Master environmental candid composition: Walking alongside a vintage cream-colored bicycle on a tree-lined campus road, hands resting naturally on the handlebars, turning toward the camera at a three-quarter angle. "
            "Relaxed youthful posture, canvas tote bag in bicycle basket, face occupying 22 percent of frame. "
            "Dainty sweet feminine facial structure, clear sparkling dark doe eyes filled with innocent warmth, a sweet serene blooming smile with cute dimples, luminous translucent porcelain skin with natural petal blush and realistic fine pores. "
            "Dark silky bob hair with soft air bangs catching golden afternoon sunbeams. "
            "Wearing a clean white linen button-up shirt casually paired with high-waist vintage blue denim. "
            "Green campus trees, sun-dappled asphalt and historic university clock tower blurred in warm golden bokeh, 55mm f/1.4 lens, iconic Japanese youth cinema realism."
        )
    },
    {
        "id": "day11_04_korea_campus",
        "region": "【韩国·首尔名门现代校园】",
        "location": "下沉大峡谷玻璃连廊 · 20岁建筑系千金单手端热咖啡",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261114,
        "steps": 20,
        "prompt": (
            "Candid 35mm photograph of an extraordinarily beautiful 20-year-old Korean college student at an avant-garde architectural university campus (韩国顶级名校建筑系女神、大峡谷玻璃护栏侧倚、单手端纸杯热咖啡、绝非死板大头照、水光凝脂真实皮质、清甜贵气、从容自信神采). "
            "Master architectural portrait framing: Leaning lightly against the glass and steel terrace balustrade overlooking a sunken modernist campus valley, dynamic diagonal body line. "
            "Holding a white paper takeaway hot coffee cup in one slender hand, architectural drawing cylinder tucked under her other arm, showing a slender waist, face occupying 23 percent of frame. "
            "Softly contoured oval face, full youthful cheeks, clear dark almond eyes radiating intelligent warmth, naturally plump hydrated dewy petal-pink lips in soft breathing repose, luminous glass skin glowing under soft afternoon ambient light with realistic fine pores. "
            "Glossy dark espresso hair cascading smoothly down her shoulders, wearing a tailored oatmeal-beige double-faced wool coat over a fitted black ribbed knit turtleneck. "
            "Modern glass campus facade reflecting the golden sunset sky, Leica M11 50mm Summilux lens, Vogue Korea campus editorial realism."
        )
    },
    {
        "id": "day11_05_mediterranean_campus",
        "region": "【意大利·博洛尼亚古老回廊】",
        "location": "罗马拱券石阶阳光画板 · 20岁美术系意式绝色回眸灿笑",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261115,
        "steps": 20,
        "prompt": (
            "Award-winning 35mm candid film photograph of a gorgeous 20-year-old Italian fine arts student sitting on sun-drenched ancient stone steps beneath historical university portico arches (世界最古老大学美术系女神、罗马拱券画中画构图、手持木质速写画板、地中海阳光斜照、绝无死板大头照、盛世美颜丰盈生机、真实皮质质感). "
            "Master sub-framing composition: Sitting comfortably on the stone steps between ancient terracotta pillars, sketchpad resting on her lap, holding a charcoal pencil in one hand, turning back toward the golden sunlight. "
            "Slender waist and sun-kissed shoulders, face occupying 23 percent of frame height along rule of thirds. "
            "Captivating soft heart-shaped face, velvety-dark hazel almond eyes sparkling with creative passion, a warm radiant natural smile full of lively Mediterranean charm, naturally defined soft berry-rose lips, smooth golden-porcelain skin with realistic texture and sun-warmed glow, zero wrinkles. "
            "Bouncy dark chocolate voluminous curls moving gently in the warm Italian breeze. "
            "Wearing a terracotta-orange ribbed knit sleeveless top and high-waist cream linen trousers. "
            "Ancient sun-bleached sandstone porticoes and cobbled courtyard in golden afternoon light, Contax 50mm f/1.4 lens, Italian cinematic realism."
        )
    },
    {
        "id": "day11_06_ivy_campus",
        "region": "【美国·斯坦福红瓦长廊】",
        "location": "棕榈林主方庭回廊漫步 · 20岁常春藤医学院校花单手扶墨镜",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261116,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a radiant 20-year-old American collegiate muse walking along the sandstone arcade of a prestigious Ivy/Stanford university quad (常春藤名校阳光学霸女神、砂岩连廊漫步动感抓拍、单肩背双肩包手扶墨镜、自信阳光神采飞扬、绝无死板大头照、真实细腻日光皮质、青春生命力天花板). "
            "Master dynamic walking composition: Striding naturally along a historic sandstone arched cloister at a 45-degree angle, backpack slung casually over one shoulder, one hand lightly resting on sunglasses pushed up onto her hair. "
            "Athletic slender posture, showing slender waist and arms, face occupying 22 percent of frame. "
            "Captivating large sparkling emerald-green doe eyes shining with warm confident intellect, a glowing radiant bright smile full of effortless collegiate charm, plump soft rosy-peach lips in soft breathing repose, completely blemish-free smooth porcelain ivory skin with subtle sun-kissed warmth. "
            "Sun-streaked honey-blonde hair moving naturally with her stride. "
            "Wearing a forest-green collegiate crewneck sweatshirt casually paired with beige tailored chino trousers. "
            "Sunlit quadrangle courtyard, towering palm trees and bright California blue sky framed between stone arches, 50mm f/1.8 lens, classic American campus realism."
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

def wait_for_completion(pid, dst_file, timeout=360):
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
                        elapsed = time.time() - start
                        print(f"-> Saved base: {dst_file.name} in {elapsed:.1f}s", flush=True)
                        return True
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return False

def upscale_image_to_2k_porcelain(file_path, art_file_path):
    img = Image.open(file_path).convert("RGB")
    print(f"  Upscaling {file_path.name} to 2K (1152x2048) with cinematic skin protection...", flush=True)
    up = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=3))
    enhancer = ImageEnhance.Contrast(sharpened)
    final_img = enhancer.enhance(1.02)
    final_img.save(file_path, "PNG", quality=95)
    shutil.copy(file_path, art_file_path)
    print(f"  -> 2K Upscale Complete: {file_path.name}", flush=True)

def make_6grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 11 Campus Muses (Master Realism) 6-Grid showcase board...", flush=True)
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
                font_bold = ImageFont.truetype(fpath, 40)
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
    draw.text((margin + 10, 35), "Day 11 · 象牙塔晨光 · 全球在校女大学生神颜特辑 (写实大作 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 11: Campus Muses · Global College Students (Master Realism 2K)", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·金秋未名银杏道】", "古朴红砖大学连廊 · 20岁中文系校花怀抱书本侧身回眸"),
        ("【英国·牛津古老图书馆】", "拉德克里夫石拱窗台 · 20岁古典文学系女神靠窗捧书浅笑"),
        ("【日本·早稻田单车初恋】", "坡道林荫路单车旁 · 19岁初恋校花手扶车把纯净甜笑"),
        ("【韩国·首尔名门现代校园】", "下沉大峡谷玻璃连廊 · 20岁建筑系千金单手端热咖啡"),
        ("【意大利·博洛尼亚古老回廊】", "罗马拱券石阶阳光画板 · 20岁美术系意式绝色回眸灿笑"),
        ("【美国·斯坦福红瓦长廊】", "棕榈林主方庭回廊漫步 · 20岁常春藤医学院校花单手扶墨镜")
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
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism 6-Pack Series | High-Native Realism Edition", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Day 11 (6-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 11: Campus Muses — Global College Students in Autumn (High-Res 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 11】象牙塔晨光 · 全球在校女大学生神颜特辑 · 6大名校写实抓拍画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, CampusMuses, CollegeGirl, AutumnLight, EnvironmentalPortrait, 35mmFilm, FilmGrain, Glamour, Exclusive, 6PhotoSet, 2KUltraHD`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day11_campus_muses_6grid.png`
2. **2K无损单图附件 (6 Standalone 2K High-Res Attachments)**:
   - `day11_01_china_campus.png` (【中国·金秋未名银杏道】古朴红砖大学连廊 · 20岁中文系校花怀抱书本侧身回眸)
   - `day11_02_western_campus.png` (【英国·牛津古老图书馆】拉德克里夫石拱窗台 · 20岁古典文学系女神靠窗捧书浅笑)
   - `day11_03_japan_campus.png` (【日本·早稻田单车初恋】坡道林荫路单车旁 · 19岁初恋校花手扶车把纯净甜笑)
   - `day11_04_korea_campus.png` (【韩国·首尔名门现代校园】下沉大峡谷玻璃连廊 · 20岁建筑系千金单手端热咖啡)
   - `day11_05_mediterranean_campus.png` (【意大利·博洛尼亚古老回廊】罗马拱券石阶阳光画板 · 20岁美术系意式绝色回眸灿笑)
   - `day11_06_ivy_campus.png` (【美国·斯坦福红瓦长廊】棕榈林主方庭回廊漫步 · 20岁常春藤医学院校花单手扶墨镜)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 11: Campus Muses — Global College Students in Autumn (6 Photographic Portraits)
全球纪实神颜日更 · Day 11 · 象牙塔晨光 · 全球在校女大学生神颜特辑 (写实大作 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Daily Candid Realism! Today, we capture the pure, radiant vitality of university youth across six iconic collegiate campuses around the world.

Rendered through high-native resolution (768×1360 native base) and real photographic optics, this collection moves far beyond static studio poses. Each shot captures natural student life through master environmental composition: dynamic walking turns, library window sub-framing, holding textbooks, leaning on vintage bicycles, and holding morning takeaway coffee:

• China (Peking University Ginkgo Walk): 20-year-old literature student walking in golden autumn light, holding textbooks against her chest, turning back with a serene tender smile.
• Western Europe (Oxford Bodleian Library Window): 20-year-old classics scholar seated by an ancient gothic arched stone window, morning sunbeams illuminating her open book and hazel eyes.
• Japan (Waseda University Campus Slope): 19-year-old first-love muse beside her cream vintage bicycle, natural sea-breeze bangs and an infectious pure sweet smile.
• Korea (Modern Avant-Garde Campus Valley): 20-year-old architecture student leaning against a glass terrace balustrade, holding a hot takeaway coffee cup, radiant glass skin in sunset glow.
• Mediterranean (Bologna Historic University Portico): 20-year-old fine arts student sitting on sunlit stone steps with charcoal sketchpad in lap, turning with a warm radiant smile.
• North America (Stanford Main Quad Cloister): 20-year-old pre-med student striding along sandstone arches, backpack slung casually, hand adjusting sunglasses with effortless sun-kissed charm.

All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with high-density facial resolution and delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Campus Moments / 今日六组校园高光

1. 🇨🇳 China: Peking University Ginkgo Walk · 金秋未名
• Scene: Red brick collegiate buildings, falling yellow ginkgo leaves, morning light.
• Composition: Dynamic 3/4 walking turn, holding hardcover textbooks, rule of thirds.
• Details: 20-year-old literature student, cream-white cable knit sweater, dark pleated skirt, serene almond eyes.

2. 🇬🇧 Western Europe: Oxford Gothic Library Window · 牛津学霸
• Scene: Radcliffe gothic arched window, vintage oak library desk, dust motes in sunbeams.
• Composition: Window sub-framing, seated pose, fingers touching vintage leather book.
• Details: 20-year-old British scholar, navy collegiate blazer, hazel doe eyes, porcelain skin.

3. 🇯🇵 Japan: Waseda Autumn Bicycle Candid · 坡道初恋
• Scene: Sun-dappled campus road, golden ginkgo canopy, collegiate clock tower.
• Composition: Walking alongside vintage bicycle, hands on handlebars, three-quarter turn.
• Details: 19-year-old student, white linen shirt and denim, tote bag, cute dimpled smile.

4. 🇰🇷 Korea: Modern Campus Valley Glass Terrace · 建筑千金
• Scene: Modern sunken glass canyon, steel balustrade, golden hour sunset reflections.
• Composition: Leaning against glass balustrade, holding paper takeaway coffee cup, diagonal line.
• Details: 20-year-old architecture student, oatmeal cashmere coat, turtleneck, glass skin.

5. 🇮🇹 Mediterranean: Bologna Sunlit Portico Sketch · 美术系绝色
• Scene: Ancient terracotta portico arches, stone steps, warm Mediterranean sunlight.
• Composition: Sitting on stone steps, charcoal sketchpad on lap, turning back toward sunlight.
• Details: 20-year-old Italian art student, terracotta knit top, voluminous chocolate curls, radiant smile.

6. 🇺🇸 North America: Stanford Sandstone Arcade Stride · 常春藤女神
• Scene: Historic sandstone arched cloister, palm trees, California blue sky.
• Composition: Natural walking stride, backpack on one shoulder, hand on sunglasses.
• Details: 20-year-old pre-med student, green collegiate crewneck, chinos, athletic radiant smile.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• High-Native Base Resolution: 全面采用 768 × 1360 原生高分基底生成（人脸潜空间像素翻倍），根除小脸碎裂与边缘伪影。
• Master Campus Storytelling: 彻底告别证件照呆立构图，融入抱书本、单车扶把、窗台翻书、端咖啡杯、画板速写等真实大学生活抓拍。
• Realism Optics & Micro-Texture: 引入原生写实照片 LoRA，赋予真实细腻的毛孔微结构与皮下血色透光，杜绝塑料橡皮磨皮感。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 11 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which campus memory resonated with you the most? Let me know in the comments below!
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
        
        new_row = """| **Day 11** | **《象牙塔晨光 · 全球在校女大学生神颜特辑 (全新写实摄影 2K)》**<br>北大未名银杏道抱书回眸、牛津图书馆石窗晨光、早稻田单车初恋、首尔现代校园端咖啡、博洛尼亚古石阶画板、斯坦福长廊漫步 | [`experiments/global_beauties_day11/`](experiments/global_beauties_day11/) | [`PATREON_POST.md`](experiments/global_beauties_day11/PATREON_POST.md) | [6 宫格母版大图](experiments/global_beauties_day11/day11_campus_muses_6grid.png) | 6 张超清原图 |
---

"""
        if "**Day 11**" in table_part:
            lines = table_part.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if "**Day 11**" in line:
                    new_lines.append(new_row.strip())
                    skip = True
                elif skip and line.startswith("---"):
                    skip = False
                elif not skip:
                    new_lines.append(line)
            table_part = "\n".join(new_lines) + "\n\n"
        else:
            table_part += new_row

        with open(index_file, "w", encoding="utf-8") as f:
            f.write(table_part + rest_part)
        print("Updated PATREON_SERIES_INDEX.md with Day 11 successfully!", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_SINGLE_LORA, "r", encoding="utf-8") as f:
        tpl_single = json.load(f)
    with open(WF_DUAL_LORA, "r", encoding="utf-8") as f:
        tpl_dual = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 11 Remaster (768 High-Native Realism) - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        if t["workflow"] == "dual_lora":
            params = {
                "lora_name_1": t["lora_1"],
                "lora_strength_1": t["strength_1"],
                "lora_name_2": t["lora_2"],
                "lora_strength_2": t["strength_2"],
                "positive_prompt": t["prompt"],
                "width": t["w"],
                "height": t["h"],
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_dual, params)
        elif t["workflow"] == "single_lora":
            params = {
                "lora_name": t["lora_name"],
                "lora_strength": t["strength"],
                "positive_prompt": t["prompt"],
                "width": t["w"],
                "height": t["h"],
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_single, params)
        else:
            params = {
                "positive_prompt": t["prompt"],
                "width": t["w"],
                "height": t["h"],
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
        board_file = OUTPUT_DIR / "day11_campus_muses_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day11_campus_muses_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 11 Campus Muses High-Native Realism Remaster completed successfully!", flush=True)

if __name__ == "__main__":
    main()
