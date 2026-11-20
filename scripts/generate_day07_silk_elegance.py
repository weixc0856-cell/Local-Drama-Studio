"""
Generate Day 07 Collection: 《月下幽兰 · 经典高定与复古丝缎》 (Twilight Silk & Evening Elegance)
Across 4 Iconic Goddess Benchmarks:
1. China: Liu Yifei (刘亦菲 - 天仙仙气与白月光骨相)
2. Western: Audrey Hepburn & Sophie Marceau (奥黛丽·赫本鹿眸与苏菲·玛索法式柔情, 零雀斑无暇凝脂肌)
3. Japan: Akina Nakamori & Ryoko Hirosue (中森明菜绝美神韵与广末凉子极致透明感)
4. Korea: Song Hye-kyo & Han Ga-in (宋慧乔温润饱满神颜与韩佳人绝美鼻梁骨相)
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day07"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day07_01_china_silk",
        "region": "【大陆】月下清辉 · 新中式真丝白月光 (刘亦菲仙姿骨相)",
        "location": "江南园林水榭晚风 · 东方绝色",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261701,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm film photograph of an extraordinarily stunning young Chinese woman standing by a tranquil lotus pond pavilion at twilight (新中式高级感、东方绝色白月光、神仙姐姐天仙骨相、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender swan neck and graceful jawline, soulful clear dark almond eyes looking back with quiet breathtaking depth and gentle warmth. "
            "Pristine translucent porcelain jade skin glowing softly in evening dusk, natural soft peach hydrated lips. "
            "Long silky raven hair partially pinned in an elegant loose updo with delicate loose strands dancing in the evening lake breeze. "
            "Wearing an exquisite minimalist ivory-white mulberry silk modern qipao dress with subtle water-ripple sheen, flowing gracefully. "
            "Reflective dark water, ancient carved stone balustrade, and soft warm lantern glow in the background, Leica M11 50mm f/1.4 Summilux, cinematic poetry, timeless elegance."
        )
    },
    {
        "id": "day07_02_western_audrey_sophie",
        "region": "【欧美】法兰西与罗马传奇 · 赫本经典黑裙与苏菲玛索柔情",
        "location": "巴黎庄园露台黄昏 · 欧陆雕塑级神颜",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261702,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Caucasian woman standing on an ornate Parisian mansion stone balcony at dusk, combining the timeless aristocratic elegance of Audrey Hepburn and the romantic French allure of Sophie Marceau (赫本式高贵骨相、苏菲玛索法式柔情、无暇瓷白肌、绝无雀斑、绝非浓妆). "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, luminous natural evening glow. "
            "Exquisite classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel eyes with long natural dark lashes, gentle enigmatic smile with natural rosy lips. "
            "Chestnut brown hair styled in an elegant loose French chignon with soft wispy fringe bangs grazing her brow. "
            "Wearing a timeless minimalist black silk velvet evening dress with delicate thin straps, accentuating her slender collarbone and swan-like neck, single natural baroque pearl pendant. "
            "Parisian skyline, Eiffel Tower silhouette, and soft purple-gold twilight sky blurred in creamy bokeh, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day07_03_japan_akina_ryoko",
        "region": "【日本】昭和绝代神韵 · 中森明菜易碎感与广末凉子透明感",
        "location": "京都幽竹石灯晚风 · 昭和绝色画报",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261703,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily beautiful young Japanese woman, capturing the legendary melancholic beauty of Akina Nakamori and the youthful pure transparency of Ryoko Hirosue (中森明菜般的绝美神韵与广末凉子的极致透明感、昭和神颜、纯情与易碎感、绝无浓妆假面). "
            "Petite delicate Japanese facial contours, soft oval jawline, slightly tearful dewy expressive dark eyes looking directly into the camera with profound tender emotion, natural fresh nude-peach lips. "
            "Translucent glowing fair porcelain skin with subtle evening chill flush on cheeks, zero blemish, natural clear complexion. "
            "Dark silky hair styled in soft vintage wavy layers with airy wispy bangs gently lifted by the mountain breeze. "
            "Wearing a refined minimalist indigo-navy silk modern kimono-inspired wrap dress, tied loosely with a silk ribbon. "
            "Twilight bamboo grove with soft warm stone lantern glow in the background, subtle film grain, Fujifilm Pro 400H aesthetic, iconic Japanese cinema masterpiece."
        )
    },
    {
        "id": "day07_04_korea_song_hye_kyo",
        "region": "【韩国】国民顶级神颜 · 宋慧乔温润与韩佳人绝美鼻相",
        "location": "首尔江南私人会所露台 · 极简画报",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261704,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Korean woman, embodying the timeless natural beauty of Song Hye-kyo and the aristocratic facial bone structure of Han Ga-in (宋慧乔般温润饱满的国民神颜、韩佳人绝美高挺鼻梁、冷白皮财阀千金、高级名媛画报). "
            "Refined Korean facial contours, smooth elegant jawline, perfectly proportioned straight high nasal bridge, deep calm intellectual almond eyes filled with captivating charisma, naturally full hydrated soft rose MLBB lips. "
            "Immaculate cool-tone porcelain glass skin, radiant and clear with realistic micro-texture, zero heavy makeup, quiet effortless luxury. "
            "Sleek silky black hair swept smoothly over one shoulder, wearing a tailored minimalist champagne-gold bias-cut liquid silk slip dress that drapes effortlessly. "
            "Modern architectural glass lines, warm interior amber glow, and city night lights sparkling in creamy background bokeh, shot on Hasselblad X2D 90mm lens, Vogue Korea high-fashion editorial style."
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

def make_4grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 07 showcase board...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    w, h = cards[0].size  # 576, 1024
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + w * 2
    board_h = header_h + margin + (h + card_title_h) * 2 + margin + footer_h
    
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
    draw.text((margin + 10, 35), "Day 07 · 月下幽兰 · 经典高定与复古丝缎", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Twilight Silk & Haute Couture across 4 Iconic Goddess Archetypes", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】月下清辉 · 新中式真丝白月光 (刘亦菲仙姿骨相)", "江南园林水榭晚风 · 东方绝色 · 月白真丝水袖与水榭幽兰"),
        ("【欧美】法兰西与罗马传奇 · 赫本经典黑裙与苏菲玛索柔情", "巴黎庄园露台黄昏 · 欧陆雕塑级神颜 · 丝绒黑裙与珍珠天鹅颈"),
        ("【日本】昭和绝代神韵 · 中森明菜易碎感与广末凉子透明感", "京都幽竹石灯晚风 · 昭和绝色画报 · 墨蓝丝缎与含情水眸"),
        ("【韩国】国民顶级神颜 · 宋慧乔温润与韩佳人绝美鼻相", "首尔江南私人会所露台 · 极简画报 · 香槟真丝与冷白皮千金")
    ]

    positions = [
        (margin, header_h + margin),
        (margin * 2 + w, header_h + margin),
        (margin, header_h + margin + h + card_title_h + margin),
        (margin * 2 + w, header_h + margin + h + card_title_h + margin)
    ]

    for i, (card, (pos_x, pos_y), (t_main, t_sub)) in enumerate(zip(cards, positions, labels)):
        board.paste(card, (pos_x, pos_y))
        draw.rectangle([pos_x, pos_y, pos_x + w, pos_y + h], outline=(220, 222, 228), width=1)
        cap_y = pos_y + h + 10
        draw.text((pos_x + 5, cap_y), t_main, fill=(25, 25, 30), font=font_med)
        draw.text((pos_x + 5, cap_y + 28), t_sub, fill=(120, 125, 135), font=font_sm)

    foot_y = board_h - 45
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism Series | Intel Arc A750 XPU Acceleration", fill=(140, 145, 155), font=font_sm)

    board.save(board_path, quality=95)
    board.save(art_board_path, quality=95)
    print(f"Showcase board saved to: {board_path}", flush=True)

def write_patreon_md():
    md_content = """# Patreon Publish Package · Day 07

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3] Day 07: Twilight Silk & Haute Couture — Iconic Goddess Archetypes (Full Set)`
- **Alternative Title (双语备选标题)**: `【月下幽兰】经典高定与复古丝缎 · 全球纪实神颜日更 Day 07 · 4K无损胶片原图合集`
- **Tags (标签)**: `FLUX, HauteCouture, SilkDress, EveningElegance, AIPhotography, Photorealism, FilmGrain, StreetPhotography, Portraits, DailySeries`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day07_silk_elegance_4grid.png`
2. **超清无损单图附件 (Standalone High-Res Attachments)**:
   - `day07_01_china_silk.png` (【大陆】江南园林水榭晚风 · 东方绝色 · 刘亦菲仙姿骨相与月白真丝)
   - `day07_02_western_audrey_sophie.png` (【欧美】巴黎庄园露台黄昏 · 欧陆雕塑级神颜 · 赫本经典黑裙与苏菲玛索柔情)
   - `day07_03_japan_akina_ryoko.png` (【日本】京都幽竹石灯晚风 · 昭和绝色画报 · 中森明菜易碎感与广末凉子透明感)
   - `day07_04_korea_song_hye_kyo.png` (【韩国】首尔江南私人会所露台 · 极简画报 · 宋慧乔温润与韩佳人绝美鼻相)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Day 07 · Twilight Silk & Haute Couture: Global Iconic Goddess Archetypes
月下幽兰 · 经典高定与复古丝缎 · 全球纪实神颜日更

━━━━━━━━━━━━━━━━━━━━

Welcome to Day 07 of our Daily Candid Realism series!

Today marks a special milestone in our visual study: we elevate the series from everyday street candids to the pinnacle of timeless feminine beauty and haute couture evening elegance. 

We refined our four regional portraits to embody universally celebrated beauty icons:
• China: The peerless ethereal grace of Liu Yifei in flowing ivory mulberry silk.
• Western: Audrey Hepburn's aristocratic bone structure and deer-like eyes paired with Sophie Marceau's romantic French allure in timeless velvet black.
• Japan: The legendary melancholic charm of Akina Nakamori blended with the youthful transparency of Ryoko Hirosue in twilight silk.
• Korea: The natural warmth and plump elegance of Song Hye-kyo combined with Han Ga-in's exquisite nasal bridge in champagne liquid silk.

Zero heavy makeup, zero artificial AI waxiness. Pure optical cinema realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 4 Goddess Portraits / 今日四组高定漫步

1. 🇨🇳 East Asian Mulberry Silk · 江南水榭月下清辉
• Scene: Ancient stone balustrade beside a reflective twilight lotus pond, gentle lake breeze lifting silk folds.
• Optics: Leica M11 50mm f/1.4 Summilux, cinematic poetry and timeless Eastern calm.
• Details: Liu Yifei ethereal fairy bone structure, smooth swan neck, ivory-white mulberry silk modern qipao with water-ripple sheen, soulful backward glance.

2. 🇪🇺 Parisian Balcony & Little Black Dress · 赫本与苏菲玛索双重传奇
• Scene: Ornate Parisian stone balcony at dusk, soft purple-gold twilight and blurred Eiffel Tower silhouette in the distance.
• Optics: Contax T2 35mm f/2.8, legendary European cinema realism.
• Details: Classical Audrey Hepburn bone structure with Sophie Marceau romantic fringe bangs, flawless porcelain ivory skin (zero freckles), minimalist black silk velvet dress with delicate straps, single baroque pearl pendant.

3. 🇯🇵 Showa Era Ethereal Melancholy · 中森明菜神韵与广末凉子透明感
• Scene: Quiet bamboo grove beside an ancient stone lantern in Kyoto at dusk, cool twilight air.
• Optics: Fujifilm Pro 400H emulation, nostalgic Japanese cinema mood.
• Details: Akina Nakamori legendary fragile charm and Ryoko Hirosue dewy clarity, soft vintage wavy hair, translucent glowing skin, minimalist indigo-navy silk kimono-wrap gown.

4. 🇰🇷 Seoul High-Society Champagne Silk · 宋慧乔温润与韩佳人鼻相
• Scene: High-rise private lounge terrace overlooking the sparkling city lights of Gangnam, Seoul after dark.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial luxury contrast.
• Details: Song Hye-kyo natural warmth and Han Ga-in straight high nasal bridge, flawless cool-tone glass skin, sleek dark hair, tailored champagne-gold liquid silk slip dress.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Liquid Silk & Fabric Physics: 真实模拟真丝绸缎在晚风与黄昏低光下的高光流转（Specular Anisotropy）与自然垂坠感。
• Cultural Archetype Perfection: 拒绝模板化千篇一律的脸庞，深度调谐四大地域最公认的殿堂级美学特征。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 07 4-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 4 × Full High-Res Standalone Portraits (576 × 1024 无损超清原图，丝缎微光直出)

Which iconic archetype speaks to your aesthetic soul the most? Let me know in the comments below!
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
    if "Day 07" not in content:
        day07_row = "| **Day 07** | **《月下幽兰 · 经典高定与复古丝缎》**<br>新中式真丝白月光(刘亦菲)、赫本小黑裙(苏菲玛索)、昭和绝代神韵(中森明菜+广末凉子)、韩国顶级千金(宋慧乔+韩佳人) | [`experiments/global_beauties_day07/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day07/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day07/PATREON_POST.md) | [4 联排大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day07/day07_silk_elegance_4grid.png) | 4 张超清原图 |\n"
        content = content.replace("## 🚀 每次发帖 3 步操作指引", day07_row + "\n---\n\n## 🚀 每次发帖 3 步操作指引")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with Day 07!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day07 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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

    if len(generated_paths) == 4:
        board_path = OUTPUT_DIR / "day07_silk_elegance_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day07_silk_elegance_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        write_patreon_md()
        update_master_index()
        print("\nDay 07 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
