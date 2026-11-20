"""
Generate Day 05 Collection: 《文艺黄昏 · 黑胶唱片与复古书店》 (Golden Hour Nostalgia · Vinyl Shop & Bookstores)
Across 4 Cultures: Mainland China, Western Europe/US, Japan, Korea.
Criteria:
- Authentic golden hour interior light: warm mahogany shelves, dust motes in sunbeams, vinyl crates, vintage books
- Natural unposed literary warmth, zero heavy makeup, authentic skin textures & film grain (Kodak Gold/Portra)
- Auto-generate PATREON_POST.md and update PATREON_SERIES_INDEX.md
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
WF_LORA = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")
WF_BASE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_t2i_api.json")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day05"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day05_01_china_bookstore",
        "region": "【大陆】旧时光书店 · 暖阳书架与静读侧颜",
        "location": "独立老书店窗边 · 梧桐斜阳",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261501,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, authentic candid 35mm film photograph of an extraordinarily beautiful young Chinese woman standing in a quiet vintage bookstore at golden hour (复古书店、捧书静读、文艺侧颜、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender neck and natural jawline, peaceful focused gaze reading an open hardcover book with quiet warmth and soulful intelligence. "
            "Pristine translucent porcelain skin, natural soft peach hydrated lips, flyaway dark hair strands illuminated by low-angle golden sunset light pouring through tall wooden windows. "
            "Wearing an oversized warm cream-beige knit sweater over a vintage white collared shirt. "
            "Surrounded by towering warm dark mahogany bookshelves filled with antique books, dust motes dancing in warm sunbeams, shot on Leica M11 50mm f/1.4 Summilux, Kodak Gold 200 nostalgic warmth."
        )
    },
    {
        "id": "day05_02_western_vinyl",
        "region": "【欧美】诺丁山黑胶店 · 复古银耳麦与金棕卷发",
        "location": "伦敦诺丁山复古唱片行 · 暖调午后",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261502,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 25-year-old British woman browsing vintage vinyl records in a cozy retro record store in London (诺丁山唱片店、复古大耳机、慵懒英伦、自然卷发与微雀斑). "
            "Sculpted European bone structure, high refined cheekbones, sparkling amber-hazel eyes with a playful gentle smile, delicate dusting of light freckles across her nose and cheeks, authentic skin texture with visible micro-pores. "
            "Voluminous wavy golden-brown hair spilling naturally over classic vintage silver over-ear headphones, backlit by warm golden sunset light streaming through the storefront glass. "
            "Wearing a slouchy distressed brown leather bomber jacket over a striped cotton tee, fingers casually flipping through a wooden crate of vinyl records. "
            "Colorful vinyl record album covers and retro music posters softly blurred in the background, Contax T2 35mm f/2.8 lens, authentic documentary warmth."
        )
    },
    {
        "id": "day05_03_japan_jimbocho",
        "region": "【日本】神保町古书店 · 暖木书架间的清澈眼眸",
        "location": "东京神保町旧书街 · 昭和治愈感",
        "workflow": "lora",
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.68,
        "seed": 20261503,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese film portrait of an exquisite young Japanese woman peeking from between two wooden bookshelves in a narrow vintage bookstore in Jimbocho, Tokyo (神保町古书店、书架间隙回眸、昭和文艺、极致透明感与纯真). "
            "Petite delicate Japanese features, soft oval face, airy wispy bangs gently framing her forehead, dark hair loosely gathered in a casual low bun with loose tendrils, big dewy expressive dark eyes looking directly into the camera with tender warmth, natural fresh nude-peach lip gloss. "
            "Translucent fair porcelain skin, holding an old Japanese poetry book close to her chest. "
            "Wearing a cozy oversized navy knit cardigan over a soft linen blouse. "
            "Floor-to-ceiling wooden shelves stacked with weathered vintage paperbacks, warm incandescent tungsten light bulbs glowing gently overhead, Fujifilm Pro 400H emulation, nostalgic Japanese cinema mood."
        )
    },
    {
        "id": "day05_04_korea_samcheong",
        "region": "【韩国】三清洞艺文空间 · 黑胶唱机与极简知性",
        "location": "首尔三清洞独立艺廊 · 极简画报",
        "workflow": "lora",
        "lora_name": "girlslikeflux_cdl.safetensors",
        "lora_strength": 0.70,
        "seed": 20261504,
        "steps": 20,
        "prompt": (
            "girlslikeflux_cdl, candid editorial portrait of an extraordinarily elegant modern Korean woman seated at a minimalist natural oak table in a sunlit art bookstore and vinyl listening lounge in Samcheong-dong, Seoul (首尔三清洞黑胶艺廊、极简知性高智感、财阀千金书卷气、冷白皮画报). "
            "Refined clean Korean facial contours, smooth elegant jawline and slender swan-like neck, calm intellectual dark eyes with direct poised gaze, natural soft rose MLBB hydrated lips. "
            "Flawless cool-tone porcelain glass skin with realistic micro-pores, zero heavy makeup, quiet understated luxury. "
            "Sleek silky dark hair parted in the middle, wearing a tailored minimalist dark charcoal double-breasted coat over a cream silk knit top. "
            "A vintage minimalist turntable spinning a vinyl record on the wooden table beside her, warm sunset rays cutting across the concrete wall in the background, shot on Hasselblad X2D 90mm lens, Vogue Korea editorial style."
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
    print("Assembling Day 05 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 05 · 文艺黄昏 · 黑胶唱片与复古书店", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Vinyl Shops & Vintage Bookstores across 4 Global Cultures", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】旧时光书店 · 暖阳书架与静读侧颜", "独立老书店窗边 · 梧桐斜阳 · 捧书静读与发丝微光"),
        ("【欧美】诺丁山黑胶店 · 复古银耳麦与金棕卷发", "伦敦诺丁山复古唱片行 · 暖调午后 · 皮夹克与翻检黑胶"),
        ("【日本】神保町古书店 · 暖木书架间的清澈眼眸", "东京神保町旧书街 · 昭和治愈感 · 书架间隙与清澈小鹿眼"),
        ("【韩国】三清洞艺文空间 · 黑胶唱机与极简知性", "首尔三清洞独立艺廊 · 极简画报 · 冷白皮与胶片唱机")
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
    md_content = """# Patreon Publish Package · Day 05

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3] Day 05: Golden Hour Nostalgia — Vinyl Records & Bookstores in China, London, Tokyo & Seoul (Full Set)`
- **Alternative Title (双语备选标题)**: `【文艺黄昏】黑胶唱片与复古书店 · 全球纪实神颜日更 Day 05 · 4K无损胶片原图合集`
- **Tags (标签)**: `FLUX, VinylRecords, VintageBookstore, GoldenHour, AIPhotography, Photorealism, FilmGrain, StreetPhotography, Portraits, DailySeries`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day05_vinyl_books_4grid.png`
2. **超清无损单图附件 (Standalone High-Res Attachments)**:
   - `day05_01_china_bookstore.png` (【大陆】独立老书店窗边 · 梧桐斜阳 · 捧书静读与发丝微光)
   - `day05_02_western_vinyl.png` (【欧美】伦敦诺丁山复古唱片行 · 暖调午后 · 皮夹克与翻检黑胶)
   - `day05_03_japan_jimbocho.png` (【日本】东京神保町旧书街 · 昭和治愈感 · 书架间隙与清澈小鹿眼)
   - `day05_04_korea_samcheong.png` (【韩国】首尔三清洞独立艺廊 · 极简画报 · 冷白皮与胶片唱机)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Day 05 · Golden Hour Nostalgia: Global Vinyl & Bookstore Candids
文艺黄昏 · 黑胶唱片与复古书店 · 全球纪实神颜日更

━━━━━━━━━━━━━━━━━━━━

Welcome to Day 05 of our Daily Candid Realism series!

There is a quiet, timeless charm in the golden hour light of indie bookstores and vintage record shops. The warm amber rays slanting through dust-moted glass windows, the tactile texture of weathered book spines, the rhythmic flipping of vinyl record sleeves, and the peaceful focus of someone lost in literature or music.

In today's series, we captured this nostalgic literary warmth across four global cultural spaces: a quiet independent bookstore in China, a retro Notting Hill vinyl shop in London, an antique bookshop in Jimbocho, Tokyo, and a contemporary vinyl art lounge in Samcheong-dong, Seoul.

Warm tungsten highlights, authentic 35mm film grain, and natural unposed expressions. Zero heavy glam makeup, zero artificial AI waxiness.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 4 Nostalgic Moments / 今日四组文艺慢步

1. 🇨🇳 East Asian Literary Warmth · 旧时光书店捧读
• Scene: Warm dark mahogany bookshelves illuminated by low-angle golden sunset light through tall windows, dust motes floating in sunbeams.
• Optics: Leica M11 50mm f/1.4 Summilux, Kodak Gold 200 nostalgic warmth.
• Details: Cozy cream-beige knit sweater over a white collared shirt, holding an open hardcover book with focused peaceful intelligence, loose flyaway hair rim-lit by sunset.

2. 🇬🇧 London Notting Hill Vinyl Crate · 复古银耳麦与金棕卷发
• Scene: Sun-drenched vintage record shop in Notting Hill, colorful vinyl sleeves and retro posters in creamy bokeh.
• Optics: Contax T2 35mm f/2.8, warm amber afternoon documentary texture.
• Details: Slouchy distressed brown leather bomber jacket over a striped tee, classic vintage silver over-ear headphones, tousled golden-brown waves, fingers casually flipping through vinyl crates with a playful smile.

3. 🇯🇵 Tokyo Jimbocho Book Stacks · 书架间隙的清澈眼眸
• Scene: Narrow antique bookstore in Jimbocho with floor-to-ceiling stacks of weathered paperbacks, warm tungsten bulb glow.
• Optics: Fujifilm Pro 400H emulation, nostalgic airy Japanese cinema mood.
• Details: Peeking from between tall wooden bookshelves holding an old poetry collection, oversized navy knit cardigan, loose low bun, big dewy dark eyes looking directly into the camera.

4. 🇰🇷 Seoul Samcheong-dong Listening Lounge · 黑胶唱机与极简知性
• Scene: Minimalist modern oak table in a sunlit art bookstore and vinyl lounge, warm low-angle sunset rays cutting across concrete walls.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial luxury contrast.
• Details: Cool-toned porcelain glass skin, tailored minimalist dark charcoal coat, poised intellectual gaze, sitting beside a vintage turntable spinning vinyl.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Low-Angle Golden Hour Lighting: 模拟黄昏时分 15 度超低角夕阳穿透老玻璃窗的漫散射光晕（Volumetric Light），呈现温润真实的胶片层次感。
• Tactile Textures: 精准再现磨损纸页、皮革夹克、黑胶纹理与木质书架的物理级触感细节。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 05 4-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 4 × Full High-Res Standalone Portraits (576 × 1024 无损超清原图，书香黑胶直出)

Are you more drawn to the quiet bookstore corner or the vinyl headphone vibe? Share your favorite in the comments below!
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
    if "Day 05" not in content:
        day05_row = "| **Day 05** | **《文艺黄昏 · 黑胶唱片与复古书店》**<br>独立老书店窗边、伦敦黑胶唱片行、神保町古书架、首尔三清洞黑胶艺廊 | [`experiments/global_beauties_day05/`](experiments/global_beauties_day05/) | [`PATREON_POST.md`](experiments/global_beauties_day05/PATREON_POST.md) | [4 联排大图](experiments/global_beauties_day05/day05_vinyl_books_4grid.png) | 4 张超清原图 |\n"
        content = content.replace("## 🚀 每次发帖 3 步操作指引", day05_row + "\n---\n\n## 🚀 每次发帖 3 步操作指引")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with Day 05!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day05 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day05_vinyl_books_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day05_vinyl_books_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        write_patreon_md()
        update_master_index()
        print("\nDay 05 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
