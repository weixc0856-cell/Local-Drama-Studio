"""
Generate Day 08 Collection: 《夏夜微醺 · 露天酒吧与城市天际线》 (Twilight Rooftop & Midnight Cocktails)
Across 4 Iconic Goddess Benchmarks:
1. China: Liu Yifei (刘亦菲 - 外滩夜色与香槟微风仙姿)
2. Western: Audrey Hepburn & Sophie Marceau (奥黛丽·赫本鹿眸与苏菲·玛索法式柔情, 零雀斑无暇冷白肌)
3. Japan: Akina Nakamori & Takako Matsu (中森明菜绝美易碎神韵与松隆子温润贵气, 六本木夜色)
4. Korea: Jun Ji-hyun & Song Hye-kyo (全智贤霸气松弛感与宋慧乔温润饱满神颜, 江南天台财阀千金)
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
        "region": "【大陆】外滩夜色 · 维港天际线与香槟微风 (刘亦菲仙姿)",
        "location": "外滩高空露天吧 · 晚风与江景流光",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261801,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, breathtaking cinematic 35mm film photograph of an extraordinarily stunning young Chinese woman at an open-air rooftop lounge overlooking the Shanghai Bund skyline at twilight (外滩高空夜景、天际线流光、神仙姐姐天仙骨相、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender swan neck and graceful collarbone, soulful clear dark almond eyes looking back with quiet breathtaking depth and gentle warmth. "
            "Pristine translucent porcelain jade skin illuminated by warm flickering candle glow and cool city bokeh, natural soft rosy peach hydrated lips. "
            "Long silky raven hair blown gracefully by the high-altitude river breeze with loose strands dancing in the air. "
            "Wearing an elegant modern pearl-white silk halterneck slip dress, holding a slender crystal flute of champagne with gentle bubbles. "
            "Glistening Huangpu River reflections and glowing historic colonial architecture in creamy out-of-focus background, Leica M11 50mm f/1.4 Summilux, cinematic poetry, timeless elegance."
        )
    },
    {
        "id": "day08_02_western_rooftop",
        "region": "【欧美】巴黎夜色 · 塞纳河露台与赫本苏菲玛索传奇",
        "location": "巴黎蒙马特高地露台吧 · 欧陆神颜",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261802,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Caucasian woman seated at an intimate Parisian rooftop terrace bar at dusk, combining the timeless aristocratic elegance of Audrey Hepburn and the romantic French allure of Sophie Marceau (赫本式高贵骨相、苏菲玛索法式柔情、无暇瓷白肌、绝无雀斑、绝非浓妆). "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, luminous soft candlelight illumination. "
            "Exquisite classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel-brown eyes with long natural dark lashes, gentle enchanting smile, natural soft rose lips. "
            "Chestnut brown wavy hair casually swept into a loose French chignon with delicate wispy bangs, a few loose curls framing her neck. "
            "Wearing an off-the-shoulder minimalist black silk top with delicate spaghetti straps, delicate gold pendant, holding a chilled French 75 cocktail glass. "
            "Warm amber candle on the small bistro table, purple-navy twilight Paris skyline and distant glowing Eiffel Tower lights softly blurred in creamy bokeh, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day08_03_japan_roppongi",
        "region": "【日本】港区微醺 · 六本木天台与中森明菜易碎神韵",
        "location": "东京六本木高空露台 · 昭和绝色画报",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261803,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm Japanese film photograph of an extraordinarily beautiful young Japanese woman leaning gently against the glass balcony of a high-rise Tokyo rooftop lounge, capturing the legendary melancholic beauty of Akina Nakamori and the timeless elegance of Takako Matsu (中森明菜般的绝美神韵与松隆子的温婉贵气、昭和绝色、微醺醉人、清冷与易碎感、绝无浓妆假面). "
            "Petite delicate Japanese facial contours, soft oval jawline, slightly dewy expressive dark eyes looking thoughtfully at the viewer with profound tender emotion, natural fresh nude-peach lip gloss. "
            "Translucent glowing fair porcelain skin softly reflecting warm ambient fairy lights, zero blemish, natural clear complexion. "
            "Dark silky shoulder-length hair gently swept by the Tokyo night breeze, wearing an elegant midnight-blue silk camisole and a draped fine cashmere cardigan off one shoulder. "
            "Holding a coupe glass with a pink lychee martini, glowing Tokyo Tower and endless sea of sparkling metropolitan city lights blurred in colorful creamy circles in the background, Fujifilm Pro 400H emulation, iconic Japanese cinema masterpiece."
        )
    },
    {
        "id": "day08_04_korea_gangnam_lounge",
        "region": "【韩国】首尔江南天台 · 全智贤气场与宋慧乔温润神颜",
        "location": "首尔江南私人无边际水景露台 · 财阀千金画报",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261804,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily gorgeous Korean woman at an exclusive Seoul Gangnam private rooftop lounge, embodying the effortless natural charisma of Jun Ji-hyun and the timeless natural beauty of Song Hye-kyo (全智贤霸气松弛感神颜与宋慧乔温润端庄、顶级财阀千金夜宴、冷白皮画报美学). "
            "Refined Korean facial contours, smooth elegant jawline, straight noble high nasal bridge, deep calm intellectual almond eyes filled with captivating magnetic charisma, naturally full hydrated soft rose MLBB lips. "
            "Immaculate cool-tone porcelain glass skin, radiant and clear with realistic micro-texture, zero heavy makeup, quiet understated luxury. "
            "Sleek dark straight hair tucked behind one ear revealing a diamond drop earring, wearing an oversized tailored charcoal-grey silk blazer draped over an ivory silk satin slip top. "
            "Infinity reflection pool, subtle warm outdoor fireplace glow, and towering Seoul neon glass skyscrapers sparkling in creamy background bokeh, shot on Hasselblad X2D 90mm lens, Vogue Korea high-fashion editorial style."
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
    print("Assembling Day 08 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 08 · 夏夜微醺 · 露天酒吧与城市天际线", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Twilight Rooftop & Midnight Cocktails across 4 Iconic Goddesses", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】外滩夜色 · 维港天际线与香槟微风 (刘亦菲仙姿)", "外滩高空露天吧 · 晚风与江景流光 · 珍珠白挂脖裙与清冷回眸"),
        ("【欧美】巴黎夜色 · 塞纳河露台与赫本苏菲玛索传奇", "巴黎蒙马特露台吧 · 欧陆神颜 · 烛光微醺与吊带黑裙"),
        ("【日本】港区微醺 · 六本木天台与中森明菜易碎神韵", "东京六本木高空露台 · 昭和绝色画报 · 墨蓝真丝与东京塔流光"),
        ("【韩国】首尔江南天台 · 全智贤气场与宋慧乔温润神颜", "首尔江南私人无边际水景露台 · 财阀千金画报 · 炭黑西装与香槟丝绸")
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
    md_content = """# Patreon Publish Package · Day 08

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3] Day 08: Twilight Rooftop & Midnight Cocktails — 4 Iconic Goddesses (Full Set)`
- **Alternative Title (双语备选标题)**: `【夏夜微醺】露天酒吧与城市天际线 · 全球纪实神颜日更 Day 08 · 4K无损胶片原图合集`
- **Tags (标签)**: `FLUX, RooftopBar, CitySkyline, Cocktails, Nightlife, AIPhotography, Photorealism, FilmGrain, Portraits, DailySeries`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day08_rooftop_cocktails_4grid.png`
2. **超清无损单图附件 (Standalone High-Res Attachments)**:
   - `day08_01_china_skyline.png` (【大陆】外滩高空露天吧 · 晚风与江景流光 · 刘亦菲仙姿骨相)
   - `day08_02_western_rooftop.png` (【欧美】巴黎蒙马特高地露台吧 · 欧陆神颜 · 赫本鹿眸与苏菲玛索柔情)
   - `day08_03_japan_roppongi.png` (【日本】东京六本木高空露台 · 昭和绝色画报 · 中森明菜易碎神韵与松隆子温润)
   - `day08_04_korea_gangnam_lounge.png` (【韩国】首尔江南私人无边际露台 · 财阀千金画报 · 全智贤霸气与宋慧乔温润)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Day 08 · Twilight Rooftop & Midnight Cocktails: Global Goddess Candids
夏夜微醺 · 露天酒吧与城市天际线 · 全球纪实神颜日更

━━━━━━━━━━━━━━━━━━━━

Welcome to Day 08 of our Daily Candid Realism series!

As night falls over the world's most glamorous metropolises, high-altitude rooftop terraces turn into captivating cinematic sanctuaries. Warm flickering candlelight meets cool neon city bokeh, high-altitude night breezes gently lift flowing silk, and a glass of chilled champagne catches the ambient glow of the urban skyline.

Tonight, we present our four iconic goddess archetypes in relaxed evening allure:
• China: Liu Yifei's ethereal elegance over the glowing Bund skyline in pearl-white silk.
• Western: Audrey Hepburn & Sophie Marceau's romantic European charm over the twilight Paris rooftops in minimalist black silk.
• Japan: Akina Nakamori's breathtaking melancholic beauty & Takako Matsu's noble poise over the glowing Tokyo Tower skyline.
• Korea: Jun Ji-hyun's effortless charisma & Song Hye-kyo's warm goddess aura over an exclusive Gangnam infinity pool lounge.

Zero heavy makeup, zero artificial AI waxiness. Pure optical cinema realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Tonight's 4 Midnight Moments / 今夜四组天际漫步

1. 🇨🇳 Shanghai Bund Skyline · 外滩天际线与香槟微风
• Scene: Open-air rooftop lounge overlooking the historic Shanghai Bund and modern Lujiazui towers at twilight, river reflections shimmering like liquid gold.
• Optics: Leica M11 50mm f/1.4 Summilux, cinematic poetry and timeless Eastern calm.
• Details: Liu Yifei ethereal fairy bone structure, pearl-white silk halterneck slip dress, river breeze dancing in her dark hair, holding a slender crystal flute of champagne.

2. 🇫🇷 Montmartre Paris Rooftop · 烛光微醺与赫本苏菲玛索传奇
• Scene: Intimate Parisian rooftop terrace bar at dusk, warm candle flickering on a small marble table, soft purple-gold twilight and blurred Eiffel Tower silhouette.
• Optics: Contax T2 35mm f/2.8, legendary European cinema realism.
• Details: Classical Audrey Hepburn bone structure with Sophie Marceau romantic fringe bangs, flawless porcelain ivory skin (zero freckles), minimalist black silk slip top, chilled French 75 cocktail.

3. 🇯🇵 Roppongi Tokyo Twilight · 六本木天台与中森明菜易碎神韵
• Scene: High-rise Tokyo rooftop glass balcony overlooking a sparkling sea of metropolitan city lights and the glowing orange Tokyo Tower.
• Optics: Fujifilm Pro 400H emulation, nostalgic Japanese cinema mood.
• Details: Akina Nakamori fragile melancholic beauty and Takako Matsu noble grace, dark wavy hair in the night breeze, midnight-blue silk camisole with off-shoulder knit, pink lychee martini.

4. 🇰🇷 Gangnam Midnight Infinity Lounge · 全智贤气场与宋慧乔神颜
• Scene: Exclusive Seoul private rooftop terrace with an infinity reflection pool and glowing outdoor fireplace overlooking neon glass skyscrapers.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial luxury contrast.
• Details: Jun Ji-hyun magnetic charisma and Song Hye-kyo natural warmth, flawless cool-tone glass skin, tailored charcoal-grey silk blazer over an ivory satin camisole, diamond drop earrings.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Low-Light Film Emulation: 克服暗光人像的模糊与噪点，精细还原微弱烛光与城市散景在冷白无暇肌肤上的柔和过渡。
• Glass & Fluid Caustics: 精准渲染高脚水晶杯、香槟气泡与马提尼液面的物理级折射光斑。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 08 4-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 4 × Full High-Res Standalone Portraits (576 × 1024 无损超清原图，天际流光直出)

Which city's rooftop view would you want to sip a midnight drink at tonight? Tell me in the comments below!
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
    if "Day 08" not in content:
        day08_row = "| **Day 08** | **《夏夜微醺 · 露天酒吧与城市天际线》**<br>上海外滩香槟(刘亦菲)、巴黎蒙马特烛光(赫本+苏菲玛索)、东京六本木微醺(中森明菜+松隆子)、首尔江南无边水景(全智贤+宋慧乔) | [`experiments/global_beauties_day08/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/PATREON_POST.md) | [4 联排大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day08/day08_rooftop_cocktails_4grid.png) | 4 张超清原图 |\n"
        content = content.replace("## 🚀 每次发帖 3 步操作指引", day08_row + "\n---\n\n## 🚀 每次发帖 3 步操作指引")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with Day 08!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day08 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day08_rooftop_cocktails_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day08_rooftop_cocktails_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        write_patreon_md()
        update_master_index()
        print("\nDay 08 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
