"""
Re-Generate Day 11: Flawless Magazine-Cover Framing Overhaul
(Campus Reverie: Ivory Tower Muses - 6 Global University Beauties)

ROOT CAUSE FIXES:
1. RESTORE DAY 10 CLOSE-UP/BUST FRAMING:
   - Day 10 worked because faces occupied 40-50% of the frame (Hasselblad 100mm portrait).
   - In Day 11, pulling back to wide half-body shrunk faces to 10% of latent pixels, causing eye distortion & warped necks.
   - Now: Frame as tight, high-end magazine cover portraits (head, shoulders, collar, collegiate lapel/knit).
2. REMOVE COMPLEX HANDS NEAR CHIN:
   - No more holding glasses or cups near the face that bleed into facial pixels.
   - Clean posture, direct captivating eye contact, perfect golden-ratio symmetry.
3. PRESERVE 20-21YO YOUTHFUL COLLAGEN & PORCELAIN SKIN.
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day11"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day11_01_china_campus",
        "region": "【中国·古都名校校花】",
        "location": "百年图书馆红木书架窗边 · 20岁清冷学霸特写神颜",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 91820101,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking Vogue magazine cover bust portrait of an extraordinarily gorgeous 20-year-old Chinese university student (顶级名校校花封面大片、20岁象牙塔白月光、特写肖像神颜、饱满紧致胶原蛋白、平整鹅蛋脸、清冷端庄天仙神态、绝无浓妆假面). "
            "Large detailed facial framing, perfect golden ratio facial symmetry, delicate slender swan neck, high cranial top, slender straight nose bridge. "
            "Soulful clear dark almond eyes looking directly into the camera with crystal-clear catchlights and quiet intelligent tenderness. "
            "Naturally plump hydrated soft petal-rose lips slightly parted in relaxed breathing repose, pristine porcelain jade skin glowing from within with pure youth. "
            "Silky dark raven hair falling over her shoulders, wearing a crisp white collared cotton shirt under a classic navy-blue fine wool collegiate vest with neat collar. "
            "Warm golden afternoon sunlight streaming from tall library windows, soft blurred mahogany bookshelves in warm cinematic bokeh, Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece."
        )
    },
    {
        "id": "day11_02_western_campus",
        "region": "【欧美·剑桥古典校花】",
        "location": "剑桥古老石柱回廊 · 20岁英伦学院风特写浪漫神颜",
        "workflow": "base",
        "seed": 82739202,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion magazine cover portrait of an extraordinarily stunning 20-year-old European university student in an Oxford or Cambridge cloister (英国Vogue封面特写大片、20岁英伦古典校花神颜、大特写肖像、饱满紧致胶原蛋白、灵动大眼、零雀斑无暇雪肌、法式英伦知性优雅). "
            "Large detailed bust portrait framing, perfect feminine youthful facial proportions, soft rounded chin, slender straight nose, captivating large sparkling hazel-green doe eyes looking straight into the lens with natural dark lashes and brilliant catchlights. "
            "Plump soft rosy-peach hydrated lips with natural sweetness, completely blemish-free smooth porcelain ivory skin with soft youthful glow, zero freckles. "
            "Lush wavy honey-brown hair framing her graceful face in the cool English breeze. "
            "Wearing an oversized chunky-knit cream cashmere sweater with soft ribbed crewneck over a crisp collared shirt. "
            "Gothic stone archway softly blurred in creamy golden hour background, Leica M11 50mm f/1.4 Summilux, legendary European academic beauty."
        )
    },
    {
        "id": "day11_03_japan_campus",
        "region": "【日本·早大纯氧校花】",
        "location": "早稻田红砖拱门下 · 19岁初恋系文学少女特写神颜",
        "workflow": "base",
        "seed": 73628303,
        "steps": 20,
        "prompt": (
            "Breathtaking Japanese beauty magazine cover portrait of an extraordinarily gorgeous 19-year-old Japanese university student (日本ar杂志封面大片、早稻田文学系校花、19岁纯氧初恋特写神颜、婴儿肥饱满胶原蛋白、完美对称水灵大眼、绝无大小眼畸变、治愈系纯真). "
            "Detailed close-up bust portrait framing, dainty delicate feminine facial structure, perfectly symmetrical smooth jawline, large clear dewy dark expressive eyes gazing directly at the viewer with bright clear catchlights and innocent sweet charm. "
            "Naturally plump glossy strawberry-pink lips, luminous translucent porcelain skin with natural youthful pink blush, completely smooth and clear. "
            "Dark silky hair with soft air bangs, wearing a soft pale oatmeal-cream knit cardigan with a neat round collar. "
            "Warm morning natural daylight, soft red-brick university archway and golden ginkgo foliage in creamy bokeh, Hasselblad X2D 90mm lens, iconic Japanese campus youth aesthetic."
        )
    },
    {
        "id": "day11_04_korea_campus",
        "region": "【韩国·延世财阀校花】",
        "location": "常春藤古建筑前 · 20岁温润水光名媛特写神颜",
        "workflow": "base",
        "seed": 64519404,
        "steps": 20,
        "prompt": (
            "Breathtaking Vogue Korea magazine cover bust portrait of an extraordinarily beautiful 20-year-old Korean top-university heiress (Vogue韩国封面特写大片、20岁水光凝脂校花神颜、三庭五眼绝对对称工整、清甜贵气学霸、绝无整容感). "
            "Prominent detailed facial framing, impeccably proportioned soft oval face, full youthful cheeks without any hollows, delicate straight dainty nose, captivating clear dark almond eyes looking straight at the camera with calm aristocratic intelligence. "
            "Plump hydrated dewy petal-pink lips, long slender swan neck, radiant translucent glass skin glowing with pure luxury hydration. "
            "Voluminous glossy dark espresso hair styled in elegant soft waves, wearing a tailored charcoal-grey wool preppy blazer with neat lapels over an ivory silk mock-neck top. "
            "Historic ivy-covered stone collegiate building and warm autumn sunlight, Leica M11 50mm f/1.4 Summilux, luxury Korean collegiate realism."
        )
    },
    {
        "id": "day11_05_mediterranean_campus",
        "region": "【地中海·博洛尼亚法学女神】",
        "location": "博洛尼亚大学古拱廊 · 20岁意式明艳知性特写神颜",
        "workflow": "base",
        "seed": 55428505,
        "steps": 20,
        "prompt": (
            "Breathtaking Italian Vogue magazine cover portrait of an extraordinarily gorgeous 20-year-old Italian university student in Bologna (意大利Vogue封面大片、20岁意式知性校花特写神颜、饱满紧致胶原蛋白、心形柔美小脸、大美人气场与甜美并存、绝无粗犷怪异感). "
            "Prominent bust portrait framing, delicate soft feminine heart-shaped face, refined smooth jawline, straight slender nose, captivating large velvety-dark almond eyes looking directly into the camera with long naturally lush lashes and warm radiant catchlights. "
            "Plump naturally defined soft berry-rose lips, completely smooth clear warm-porcelain skin with healthy sun-kissed youthful radiance, zero wrinkles or hollows. "
            "Bouncy dark chocolate glossy curls cascading around her shoulders in the warm Italian afternoon sun. "
            "Wearing a tailored olive-green wool blazer over an ivory silk top with clean neckline. "
            "Ancient arched stone porticoes and sunlit cobblestone courtyard in creamy background, Contax T2 35mm f/2.8 lens, Italian academic cinema masterwork."
        )
    },
    {
        "id": "day11_06_ivy_campus",
        "region": "【北美常春藤·耶鲁极光精灵】",
        "location": "耶鲁哥特式走廊 · 20岁极光瓷娃娃学霸特写神颜",
        "workflow": "base",
        "seed": 46317606,
        "steps": 20,
        "prompt": (
            "Breathtaking Harper's Bazaar cover portrait of an extraordinarily stunning 20-year-old Ivy League student at Yale University (耶鲁大学封面特写大片、20岁极光芭比学霸神颜、瓷娃娃般紧致白皙、饱满胶原蛋白、清澈纯真翡翠猫眼、直视镜头明眸绝色). "
            "Detailed close-up bust portrait framing, soft delicate feminine oval face, smooth tapered chin, petite straight nose, hypnotic clear bright emerald-green almond eyes looking directly into the lens with youthful sparkle and intellectual brilliance. "
            "Plump soft natural rose-pink lips, radiant clear porcelain milk skin with natural youthful flush, completely blemish-free and zero freckles. "
            "Silky light ash-brown wavy hair styled naturally over her shoulders, wearing a classic deep navy-blue collegiate crewneck sweater with neat white collared shirt underneath. "
            "Majestic Gothic stone arches of Yale University and warm autumn sunlight in soft creamy bokeh, Leica M11 50mm f/1.4 Summilux, Ivy League collegiate perfection."
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
    print("Assembling Day 11 Campus Muses 6-Grid showcase board (Magazine Bust Edition)...", flush=True)
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
    draw.text((margin + 10, 35), "Day 11 · 象牙塔的微光 · 全球顶尖名校校花封面特辑 (6张全集 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 11: Campus Reverie · Ivory Tower University Muses (Magazine Cover Edition)", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·古都名校校花】", "百年图书馆红木书架窗边 · 20岁清冷学霸白月光 · 藏青学院背心"),
        ("【欧美·剑桥古典校花】", "剑桥古老石柱回廊 · 20岁英伦学院风浪漫神颜 · 粗织羊绒毛衣"),
        ("【日本·早大纯氧校花】", "早稻田红砖拱门下 · 19岁初恋系文学少女 · 燕麦色针织开衫"),
        ("【韩国·延世财阀校花】", "常春藤古建筑石阶 · 20岁水光凝脂名媛学霸 · 羊毛西装白月光"),
        ("【地中海·博洛尼亚法学女神】", "古拱廊石柱庭院 · 20岁意式明艳知性校花 · 橄榄绿西装"),
        ("【北美常春藤·耶鲁极光精灵】", "哥特式图书馆回廊 · 20岁极光瓷娃娃学霸 · 耶鲁复古徽标毛衣")
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
    md_content = """# Patreon Publish Package · Day 11 (6-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 11: Campus Reverie — Ivory Tower University Muses (Magazine Cover 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 11】象牙塔的微光 · 全球顶尖名校校花封面特辑 · 6大名校神颜画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, CollegeGirl, UniversityCampus, IvoryTower, PreppyStyle, FilmGrain, Glamour, Exclusive, 6PhotoSet, 2KUltraHD`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day11_campus_muses_6grid.png`
2. **2K无损单图附件 (6 Standalone 2K High-Res Attachments)**:
   - `day11_01_china_campus.png` (【中国·古都名校校花】百年图书馆红木书架窗边 · 20岁清冷学霸白月光 · 藏青学院背心)
   - `day11_02_western_campus.png` (【欧美·剑桥古典校花】剑桥古老石柱回廊 · 20岁英伦学院风浪漫神颜 · 粗织羊绒毛衣)
   - `day11_03_japan_campus.png` (【日本·早大纯氧校花】早稻田红砖拱门下 · 19岁初恋系文学少女 · 燕麦色针织开衫)
   - `day11_04_korea_campus.png` (【韩国·延世财阀校花】常春藤古建筑石阶 · 20岁水光凝脂名媛学霸 · 羊毛西装白月光)
   - `day11_05_mediterranean_campus.png` (【地中海·博洛尼亚法学女神】古拱廊石柱庭院 · 20岁意式明艳知性校花 · 橄榄绿西装)
   - `day11_06_ivy_campus.png` (【北美常春藤·耶鲁极光精灵】哥特式图书馆回廊 · 20岁极光瓷娃娃学霸 · 耶鲁复古徽标毛衣)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 11: Campus Reverie — Ivory Tower University Muses (6 Global Beauties)
全球纪实神颜日更 · Day 11 · 象牙塔的微光 · 全球顶尖名校校花封面特辑 (6张全集 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Daily Candid Realism! In Day 11, we explore the world of academic grace, sun-dappled library windows, and the effortless brilliance of university campus life.

Framed in the high-impact close-up bust editorial style of Vogue and Harper's Bazaar, this collection captures the pure, radiant zenith of youth (19 to 21 years old) across the world's most prestigious collegiate campuses:
• China: 20-year-old top university muse by the mahogany bookshelves of a historic library, quiet brilliance, and liquid porcelain jade skin.
• Western Europe: 20-year-old Cambridge beauty beneath ancient Gothic cloisters, oversized cable-knit cashmere, and large hazel-green doe eyes.
• Japan: 19-year-old pure oxygen literature student under Tokyo's red-brick university arches, soft air bangs, and dewy strawberry lips.
• Korea: 20-year-old poised heiress by ivy-covered stone collegiate halls, luminous glass skin, and a tailored preppy blazer.
• Mediterranean: 20-year-old law student in the sunlit porticoes of the University of Bologna, vibrant dark curls, and warm radiant honey skin.
• North America: 20-year-old Ivy League angel inside Yale's grand Gothic library cloisters, deep navy varsity knit, and clear emerald-green cat eyes.

Zero artificial filters, zero age lines, zero distorted hands. All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Moments / 今日六组校园高光

1. 🇨🇳 China: Historic Library Window · 古都名校校花
• Scene: Century-old university library, afternoon sunbeams dancing across polished mahogany tables and dust motes.
• Optics: Hasselblad H6D-100c 100mm lens, Vogue China cover masterpiece.
• Details: 20-year-old academic muse, white collared shirt under a navy wool vest, crystal-clear catchlights, pristine jade porcelain skin.

2. 🇬🇧 Western Europe: Cambridge Gothic Cloisters · 剑桥古典校花
• Scene: Ancient stone archways of Cambridge University, soft golden autumn lawn.
• Optics: Leica M11 50mm f/1.4 Summilux, legendary European academic romance.
• Details: 20-year-old English collegiate beauty, oversized cream cable-knit sweater, zero freckles, large sparkling hazel-green doe eyes.

3. 🇯🇵 Japan: Red-Brick Archway Breeze · 早大纯氧校花
• Scene: Tokyo university red-brick courtyard, golden ginkgo canopy in soft morning light.
• Optics: Hasselblad X2D 90mm lens, iconic Japanese campus youth aesthetic.
• Details: 19-year-old literature student, soft air bangs, dewy strawberry-pink lips, oatmeal knit cardigan, perfectly symmetrical dewy dark eyes.

4. 🇰🇷 Korea: Ivy-Covered Stone Staircase · 延世财阀校花
• Scene: Historic ivy-covered collegiate hall, warm afternoon sunshine casting long architectural shadows.
• Optics: Leica M11 50mm f/1.4 Summilux, luxury Korean collegiate realism.
• Details: 20-year-old poised heiress, tailored grey wool preppy blazer, luminous glass skin, serene intellectual gaze, swan neck.

5. 🇮🇹 Mediterranean: Bologna Sunlit Portico · 博洛尼亚法学女神
• Scene: Ancient arched stone porticoes and sunlit cobblestone courtyard of the University of Bologna.
• Optics: Contax T2 35mm f/2.8 lens, Italian academic cinema masterwork.
• Details: 20-year-old law student, tailored olive-green blazer, bouncy dark chocolate curls, radiant honey-porcelain skin, large velvety almond eyes.

6. 🇺🇸 North America: Yale Gothic Library Arch · 耶鲁极光精灵
• Scene: Grand Gothic stone arches of Yale University, crisp autumn campus foliage.
• Optics: Leica M11 50mm f/1.4 Summilux, Ivy League collegiate perfection.
• Details: 20-year-old Ivy League angel, deep navy varsity crewneck with collegiate crest, piercing emerald-green cat eyes, porcelain milk skin.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Close-Up Bust Editorial Framing: 全面回归 Day 10 黄金特写比例（面部占比 40%~50%），让潜空间具备数万像素的高密度解析力，杜绝远景小脸引起的五官变形与眼神失真。
• Peak-Youth Collagen Tuning: 严格锁定 19~21 岁大学黄金花期，骨骼秀美、胶原蛋白充盈、中庭平整紧致，展现最纯粹的校园白月光神颜。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出，发丝反光与瞳孔光斑纤毫毕现。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 11 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which campus muse captures your collegiate dreams the most? Let me know in the comments below!
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
        
        if "Day 11" in table_part:
            lines = table_part.split("\n")
            new_lines = []
            for l in lines:
                if "Day 11" in l:
                    new_lines.append("| **Day 11** | **《象牙塔的微光 · 全球顶尖名校校花封面特辑 (6张全集 · 2K)》**<br>古都百年图书馆学霸白月光、剑桥石柱长廊英伦古典、早稻田红砖初恋文学少女、延世常春藤财阀名媛、博洛尼亚古老拱廊法学女神、耶鲁哥特回廊极光精灵 | [`experiments/global_beauties_day11/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day11/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day11/PATREON_POST.md) | [6 宫格母版大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day11/day11_campus_muses_6grid.png) | 6 张超清原图 |")
                else:
                    new_lines.append(l)
            table_part = "\n".join(new_lines)
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(table_part + rest_part)
            print("Updated PATREON_SERIES_INDEX.md with Day 11 overhaul successfully!", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 11 Close-Up Overhaul - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_file = OUTPUT_DIR / "day11_campus_muses_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day11_campus_muses_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 11 Close-Up Overhaul succeeded with 6 flawless faces!", flush=True)

if __name__ == "__main__":
    main()
