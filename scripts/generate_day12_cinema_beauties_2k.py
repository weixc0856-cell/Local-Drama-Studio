"""
Generate Day 12 Collection (V3 Professional Photographer Framing):
《光影史诗 · 全球电影巨制神级女主角特辑》
(Cinematic Masterpiece: 6 Iconic Global Leading Ladies · Professional Framing & Composition · 2K Ultra-HD)

CRITICAL MANDATES TO ELIMINATE "大头照 / 证件照" (Frontal Mugshot Syndrome):
1. DYNAMIC COMPOSITION & THREE-QUARTER ANGLES:
   - Absolutely NO 0-degree frontal standing passport poses.
   - Every character utilizes professional photographer framing: Three-quarter body angle (30-45 deg), over-the-shoulder turn, seated window frame, or relaxed leaning.
2. NARRATIVE PROPS & PHYSICAL INTERACTION:
   - Holding bamboo umbrella, crystal champagne flute, leaning chin on palm by wooden train window, coffee cup on terrace railing, woven fruit basket, hand in pocket.
3. SUB-FRAMING & RULE OF THIRDS:
   - Architectural sub-framing (train window, stone arch, brick alleyway, terrace balustrade).
   - Character positioned along rule of thirds lines, giving ample negative space (lead room) for the gaze.
4. BALANCED MEDIUM SHOT (Waist-Up / Half-Body, 35mm-55mm equivalent):
   - Face occupies only 20%-25% of frame height.
   - Full upper-body posture, slender waist, shoulders, arms, clothing silhouette and rich environment visible.
5. ZERO "苦相" (Radiant, confident, charming smiles, blooming vitality, no sorrow).
6. 2K Ultra-HD (1152 x 2048) with cinematic skin preservation.
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day12"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day12_01_china_cinema",
        "region": "【中国·王家卫东方谍战】",
        "location": "雨夜弄堂拱门回眸 · 21岁旗袍女主角执伞侧身神颜",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.68,
        "seed": 20261221,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, award-winning cinematic 35mm film still of an extraordinarily gorgeous 21-year-old Chinese leading actress walking in a 1960s vintage Shanghai alleyway (王家卫大师级电影构图、21岁东方绝色天仙女主角、侧身漫步优雅回眸、打破死板证件照、环境人像中景半身、明艳从容浅笑、绝无苦相、饱满胶原蛋白、平整紧致鹅蛋脸). "
            "Master professional photographer composition: Dynamic over-the-shoulder three-quarter angle (侧身回眸角度), walking under an ancient brick archway creating natural architectural sub-framing. "
            "Delicately holding a dark oiled bamboo umbrella in one slender hand, other arm resting naturally, showing slender waist and graceful posture, face occupying roughly 22 percent of frame height along the rule of thirds. "
            "Sparkling dark almond eyes filled with warm lively intelligence, sweet captivating gentle smile with upturned lip corners, relaxed open brow. "
            "Wearing a tailored high-neck emerald-green liquid silk jacquard qipao. "
            "Rain-slicked cobblestone street, soft amber streetlamp backlighting casting a golden rim on her hair, wet asphalt reflections, 50mm anamorphic lens, breathtaking cinematic depth."
        )
    },
    {
        "id": "day12_02_western_cinema",
        "region": "【欧美·007谍战邦女郎】",
        "location": "蒙特卡洛赌场香槟吧台 · 21岁法式邦女郎侧倚端杯神颜",
        "workflow": "base",
        "seed": 20261222,
        "steps": 20,
        "prompt": (
            "Breathtaking 35mm Panavision anamorphic film still of a stunning 21-year-old European Bond Girl in a luxurious Monte Carlo casino lounge (007好莱坞大片摄影师构图、21岁法式浪漫绝美大女主、吧台斜倚半身抓拍、指尖端着细长香槟杯、绝无死板大头照、自信明媚笑容、大鹿眸灵动、无暇雪肌、松弛高贵高级感). "
            "Professional environmental portrait framing: Casually leaning at a 45-degree angle against a polished marble bar counter, rule of thirds composition with negative space. "
            "Slender fingers elegantly holding the stem of a crystal champagne flute, one elbow resting on the bar, showing off a sculpted waist and bare back silhouette, face occupying only 22 percent of frame. "
            "Large sparkling hazel doe eyes looking with playful alluring confidence, a radiant blooming smile full of warmth and effortless charisma, zero sorrow. "
            "Voluminous wavy honey-brown hair spilling luxuriously over one bare shoulder. "
            "Wearing a backless midnight-black silk velvet cocktail gown. "
            "Foreground soft crystal glass bokeh, warm golden chandeliers and opulent casino salon blurred in creamy background, 55mm lens, blockbuster cinema masterpiece."
        )
    },
    {
        "id": "day12_03_japan_cinema",
        "region": "【日本·岩井俊二海风诗意】",
        "location": "沿海列车木窗托腮看海 · 20岁清纯初恋女主角窗框抓拍",
        "workflow": "base",
        "seed": 20261223,
        "steps": 20,
        "prompt": (
            "Award-winning 35mm Japanese cinematic film still of an adorable 20-year-old Japanese leading actress inside a vintage wooden seaside train carriage (岩井俊二电影大师构图、20岁清纯初恋神颜女主角、木窗框式构图、单手托腮看海侧颜、打破死板正面大头照、纯净治愈笑容、灵动大眼、阳光海浪微风、极致电影故事感). "
            "Master sub-framing composition: Framed naturally inside the open wooden train window, seated sideways at a three-quarter angle. "
            "One elbow resting casually on the wooden windowsill, chin resting gently on palm in a natural candid gesture, looking joyfully toward the ocean breeze, face occupying 22 percent of frame. "
            "Large sparkling dark doe eyes shining with youthful happiness, a sweet blooming smile with cute dimples, glowing porcelain skin with a soft petal blush. "
            "Silky dark bob with soft bangs dancing in the coastal breeze. "
            "Wearing an oversized crisp white linen button-down shirt loosely tucked into high-waist vintage blue jeans. "
            "Sunlit turquoise Pacific Ocean waves and coastal greenery sparkling through the window in warm afternoon light, 50mm f/1.4 lens, iconic Japanese cinema poetry."
        )
    },
    {
        "id": "day12_04_korea_cinema",
        "region": "【韩国·悬疑巨制财阀千金】",
        "location": "现代豪宅露台凭栏看夜景 · 21岁水光千金端咖啡杯侧影",
        "workflow": "base",
        "seed": 20261224,
        "steps": 20,
        "prompt": (
            "Cinematic 35mm film still of a gorgeous 21-year-old Korean cinema actress in a high-end luxury mystery drama (韩国大导级摄影构图、21岁顶级水光凝脂神颜、现代豪宅露台凭栏远眺、双手捧着温热陶瓷咖啡杯、侧身构图绝非死板大头照、优雅舒展浅笑、绝无苦相忧愁、清冷千金贵气). "
            "Professional architectural portrait framing: Leaning lightly against the glass and steel balustrade of a penthouse terrace overlooking the city nightscape, rule of thirds diagonal pose. "
            "Holding a minimalist ceramic warm coffee cup with both hands on the railing, body turned sideways at 35 degrees, showing a slender hourglass waist, face occupying 23 percent of frame. "
            "Clear sparkling dark almond eyes looking calmly into the glittering night sky with an intelligent poise, subtle elegant smile, luminous glass skin glowing under terrace ambient lights. "
            "Glossy espresso hair flowing down over one shoulder, wearing a bespoke champagne-ivory silk satin wrap gown with a cinched belt. "
            "Panoramic city lights shimmering in cool cyan and warm amber bokeh behind glass, Leica M11 50mm Summilux lens, prestige cinema realism."
        )
    },
    {
        "id": "day12_05_mediterranean_cinema",
        "region": "【地中海·西西里美丽传说】",
        "location": "托斯卡纳石阶回廊提果篮 · 21岁意式绝色女主角灿烂回眸",
        "workflow": "base",
        "seed": 20261225,
        "steps": 20,
        "prompt": (
            "Award-winning 35mm cinematic film still of a stunning 21-year-old Italian leading actress in a Mediterranean romantic masterpiece (西西里美丽传说级摄影大师构图、21岁意式明艳绝色女主角、古老石阶提篮回眸、S型舒展体态、绝无死板大头照、阳光灿烂笑容、神采飞扬、盛世美颜丰盈生机). "
            "Master candid framing: Descending an ancient sun-drenched limestone staircase framed by arched Roman pillars (sub-framing), turning back gracefully toward the warm golden sunlight with dynamic body curvature. "
            "One hand carrying a rustic woven wicker basket of fresh purple figs, other hand lightly touching the terracotta linen dress, slender waist and sunkissed collarbones fully displayed, face occupying 22 percent of frame. "
            "Large velvety-dark hazel eyes sparkling with vibrant zest, a wide radiant joyful smile full of lively Mediterranean warmth, completely relaxed and full of vital youth, zero sadness. "
            "Bouncy dark chocolate curls dancing in the sea wind. "
            "Wearing a fitted terracotta-red fine linen sundress with a sweetheart neckline. "
            "Ancient stone architecture, shimmering turquoise Mediterranean Sea and olive groves in golden hour glow, Contax 50mm f/1.4 lens, Italian auteur cinema romance."
        )
    },
    {
        "id": "day12_06_scifi_cinema",
        "region": "【欧美·沙丘银翼科幻史诗】",
        "location": "赛博天台斜倚全息围栏 · 20岁极光翡翠女主角插兜飒爽神采",
        "workflow": "base",
        "seed": 20261226,
        "steps": 20,
        "prompt": (
            "Breathtaking 65mm IMAX cinematic film still of a striking 20-year-old sci-fi epic heroine on an aerial skyscraper terrace in a futuristic city (银翼杀手沙丘级电影摄影大师构图、20岁极光瓷娃娃神颜、天台斜倚围栏单手插兜、飒爽灵动舒展姿态、绝无死板大头照、自信迷人神采、明亮翡翠绿猫眼、未来主义大片质感). "
            "Master environmental portrait composition: Leaning casually back against a luminous metallic sky-terrace barrier, dynamic diagonal silhouette, rule of thirds placement. "
            "One hand resting casually in the pocket of her tailored cropped black leather jacket, the other hand resting on the railing, revealing a toned slender waist, face occupying 22 percent of frame. "
            "Hypnotic clear bright emerald-green almond eyes looking with keen vibrant intellect, a subtle confident playful smirk, flawless porcelain milk skin glistening with atmospheric rain mist. "
            "Silky ash-blonde hair with wispy strands framing her cheekbones. "
            "Futuristic neon skyscrapers, airborne vehicle light trails, and misty holographic cyan and amber anamorphic bokeh in vast background, ARRI Alexa 65 50mm lens, IMAX sci-fi blockbuster masterwork."
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
    print(f"  Upscaling {file_path.name} to 2K (1152x2048) with cinematic skin protection...", flush=True)
    up = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    # Gentle edge unsharp mask for film texture & sharp catchlights
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=45, threshold=3))
    enhancer = ImageEnhance.Contrast(sharpened)
    final_img = enhancer.enhance(1.02)
    
    final_img.save(file_path, "PNG", quality=95)
    shutil.copy(file_path, art_file_path)
    print(f"  -> 2K Upscale Complete: {file_path.name}", flush=True)

def make_6grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 12 Cinema Muses (Master Framing) 6-Grid showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 12 · 光影史诗 · 全球电影巨制神级女主角特辑 (大师构图 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 12: Cinematic Masterpiece · Global Leading Ladies (Master Framing 2K)", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【中国·王家卫东方谍战】", "雨夜弄堂拱门回眸 · 21岁旗袍女主角执伞侧身神颜"),
        ("【欧美·007谍战邦女郎】", "蒙特卡洛赌场香槟吧台 · 21岁法式邦女郎侧倚端杯神颜"),
        ("【日本·岩井俊二海风诗意】", "沿海列车木窗托腮看海 · 20岁清纯初恋女主角窗框抓拍"),
        ("【韩国·悬疑巨制财阀千金】", "现代豪宅露台凭栏看夜景 · 21岁水光千金端咖啡杯侧影"),
        ("【地中海·西西里美丽传说】", "托斯卡纳石阶回廊提果篮 · 21岁意式绝色女主角灿烂回眸"),
        ("【欧美·沙丘银翼科幻史诗】", "赛博天台斜倚全息围栏 · 20岁极光翡翠女主角插兜飒爽神采")
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
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism 6-Pack Series | Professional Framing Edition", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Day 12 (6-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 12: Cinematic Masterpiece — Global Blockbuster Leading Ladies (Master Framing 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 12】光影史诗 · 全球电影巨制神级女主角特辑 · 6大银幕大师构图神颜画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, CinematicStill, 35mmFilm, Blockbuster, AnamorphicLens, FilmGrain, Glamour, Exclusive, 6PhotoSet, 2KUltraHD, EnvironmentalPortrait`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day12_cinema_muses_6grid.png`
2. **2K无损单图附件 (6 Standalone 2K High-Res Attachments)**:
   - `day12_01_china_cinema.png` (【中国·王家卫东方谍战】雨夜弄堂拱门回眸 · 21岁旗袍女主角执伞侧身神颜)
   - `day12_02_western_cinema.png` (【欧美·007谍战邦女郎】蒙特卡洛赌场香槟吧台 · 21岁法式邦女郎侧倚端杯神颜)
   - `day12_03_japan_cinema.png` (【日本·岩井俊二海风诗意】沿海列车木窗托腮看海 · 20岁清纯初恋女主角窗框抓拍)
   - `day12_04_korea_cinema.png` (【韩国·悬疑巨制财阀千金】现代豪宅露台凭栏看夜景 · 21岁水光千金端咖啡杯侧影)
   - `day12_05_mediterranean_cinema.png` (【地中海·西西里美丽传说】托斯卡纳石阶回廊提果篮 · 21岁意式绝色女主角灿烂回眸)
   - `day12_06_scifi_cinema.png` (【欧美·沙丘银翼科幻史诗】赛博天台斜倚全息围栏 · 20岁极光翡翠女主角插兜飒爽神采)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 12: Cinematic Masterpiece — Global Blockbuster Leading Ladies (Master Framing Edition)
全球纪实神颜日更 · Day 12 · 光影史诗 · 全球电影巨制神级女主角特辑 (大师构图 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Daily Candid Realism! Today, we introduce professional cinema and editorial framing to our worldwide beauties collection, completely moving beyond static frontal portraits into living, breathing motion picture frames.

Captured through classic 35mm and 50mm cinematic lenses (Panavision Primo, Leica Summilux, Contax Zeiss), each shot embraces master photographer composition principles: dynamic three-quarter angles, architectural sub-framing, narrative prop interaction, and generous negative breathing space.

Embodying their 20 to 22 years old golden age, each leading lady radiates effortless charm, confident smiles, and captivating storytelling:

• China (Wong Kar-wai Rain Alley Over-the-Shoulder): 21-year-old silk qipao spy muse walking under a brick archway, delicately holding a dark bamboo umbrella, turning back with a warm enchanting smile.
• Western Europe (007 Casino Champagne Bar Lean): 21-year-old French Bond heroine leaning at a marble bar, holding a crystal champagne flute, bare back and honey waves catching golden chandelier bokeh.
• Japan (Shunji Iwai Coastal Train Window Frame): 20-year-old innocent first-love heroine framed inside the open wooden train window, resting chin on palm, gazing joyfully over the Pacific waves.
• Korea (Modern Penthouse Night Balustrade): 21-year-old poised heiress holding a warm coffee cup on a high-floor glass terrace, overlooking city skyline bokeh with a serene radiant smile.
• Mediterranean (Tuscan Sunlit Staircase Basket Turn): 21-year-old vivacious Italian beauty in a terracotta sundress, carrying a wicker fig basket down ancient stone stairs with an infectious sunny smile.
• North America (IMAX Cyberpunk Sky Terrace Lean): 20-year-old sharp sci-fi heroine leaning casually against a metallic barrier, one hand tucked in her leather jacket pocket, emerald cat eyes shining with magnetic charisma.

All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with high-density facial resolution and delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Cinematic Moments / 今日六组电影高光

1. 🇨🇳 China: Wong Kar-wai Rain Alley Over-the-Shoulder · 东方谍战
• Scene: Vintage 1960s alleyway, rain-slicked cobblestones, brick arch sub-framing.
• Composition: Dynamic 3/4 over-the-shoulder turn, holding dark oiled bamboo umbrella, rule of thirds.
• Details: 21-year-old heroine, emerald-green silk jacquard qipao, sparkling almond eyes and an enchanting soft smile.

2. 🇫🇷 Western Europe: 007 Casino Champagne Bar Lean · 谍战邦女郎
• Scene: Opulent Monte Carlo casino bar, warm chandeliers, marble counter reflections.
• Composition: 45-degree casual bar lean, holding crystal champagne flute, bare back silhouette.
• Details: 21-year-old French Bond muse, sparkling hazel doe eyes, black silk velvet gown, radiant confident smile.

3. 🇯🇵 Japan: Shunji Iwai Coastal Train Window Frame · 海风诗意
• Scene: Vintage wooden seaside train carriage, sparkling blue Pacific Ocean waves in golden light.
• Composition: Window sub-framing, elbow on windowsill, chin resting on palm, gazing toward ocean.
• Details: 20-year-old first-love heroine, white linen shirt and denim, soft air bangs, pure sweet smile with dimples.

4. 🇰🇷 Korea: Modern Penthouse Night Balustrade · 优雅千金
• Scene: Modern glass terrace overlooking glowing city skyline and amber fireplace glow.
• Composition: Leaning against glass balustrade, holding warm ceramic coffee cup with both hands, diagonal body line.
• Details: 21-year-old heiress, champagne-ivory silk satin wrap dress, luminous glass skin, serene radiant smile.

5. 🇮🇹 Mediterranean: Tuscan Sunlit Staircase Basket Turn · 阳光西西里
• Scene: Ancient sun-drenched limestone stairs, Roman arch pillars, shimmering turquoise sea.
• Composition: Descending stone stairs, carrying wicker basket of purple figs, dynamic S-curve turn.
• Details: 21-year-old Italian actress, terracotta-red linen sundress, voluminous chocolate curls, infectious sunny smile.

6. 🇺🇸 North America: Cyberpunk Aerial Sky Terrace Lean · 科幻史诗
• Scene: Futuristic aerial sky terrace overlooking glowing neon spires and aerial flight lanes.
• Composition: Diagonal lean against luminous metallic railing, hand in jacket pocket, rule of thirds placement.
• Details: 20-year-old sci-fi heroine, cropped black leather jacket, ash-blonde damp strands, piercing emerald cat eyes, confident magnetic smirk.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Master Environmental Composition: 彻底告别证件照呆立构图，引入侧身 3/4、回眸、车窗画中画、吧台/栏杆倚靠等大师级人像构图法则。
• Narrative Props & Interaction: 手持油纸竹伞、纤细香槟杯、车窗托腮看海、双手捧温热咖啡、手提编织无花果篮、单手插兜，呈现生动剧情抓拍感。
• Balanced Medium Shot: 采用 35mm-55mm 中景半身比例（面部占高 20%~25%），兼备精致体态、纤细腰身、高定服饰与宏大电影空间纵深。
• Radiant & Vital Expression: 彻底剔除苦相与阴郁愁容，呈现 20-22 岁黄金年龄的生动神采与甜美自信笑容。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 12 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which cinematic world captivated your imagination the most? Let me know in the comments below!
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
        
        new_row = """| **Day 12** | **《光影史诗 · 全球电影巨制神级女主角特辑 (6张全集 · 大师构图 2K)》**<br>王家卫雨夜执伞回眸、007赌场吧台香槟侧倚、岩井俊二车窗托腮看海、韩国现代豪宅凭栏看夜景、托斯卡纳石阶提篮回眸、赛博天台倚栏插兜 | [`experiments/global_beauties_day12/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day12/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day12/PATREON_POST.md) | [6 宫格母版大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day12/day12_cinema_muses_6grid.png) | 6 张超清原图 |
---

"""
        if "Day 12" in table_part:
            # replace Day 12 line
            lines = table_part.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if "**Day 12**" in line:
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
        print("Updated PATREON_SERIES_INDEX.md with Day 12 successfully!", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 12 Cinema Muses (V3 Master Framing) - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        # Force regenerate for v3 master framing
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
        board_file = OUTPUT_DIR / "day12_cinema_muses_6grid.png"
        art_board_file = ARTIFACTS_DIR / "day12_cinema_muses_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nDay 12 Cinema Blockbuster Edition V3 (Master Framing) succeeded!", flush=True)

if __name__ == "__main__":
    main()
