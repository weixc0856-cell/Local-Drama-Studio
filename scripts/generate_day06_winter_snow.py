"""
Generate Day 06 Collection: 《雪霁初晴 · 冬日纯白毛衣与围巾》 (First Snow & Winter Warmth)
Across 4 Cultures: Mainland China, Western Europe/US, Japan, Korea.
Criteria:
- Authentic winter snowy daylight: soft falling snow, frosty breath, cozy knitwear & cashmere
- Western beauty specifically refined: Inspired by Audrey Hepburn & Sophie Marceau, flawless porcelain skin, zero freckles, aristocratic classical facial symmetry
- True optical 35mm/50mm/85mm film photography
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
WF_LORA = r"d:\Local-Drama-Studio\workflows\flux3_lora_t2i_api.json"
WF_BASE = r"d:\Local-Drama-Studio\workflows\flux3_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day06"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day06_01_china_snow",
        "region": "【大陆】红墙白雪 · 故宫角楼回眸与白羊绒",
        "location": "故宫雪后红墙掩映 · 绝美东方骨相",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261601,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, authentic cinematic 35mm film photograph of an extraordinarily beautiful young Chinese woman in a gentle winter snowfall beside an ancient red palace wall (红墙白雪、冬日回眸、清冷绝美、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender neck and graceful jawline, soulful intelligent dark almond eyes with soft snowflakes caught on her eyelashes. "
            "Pristine translucent porcelain jade skin with subtle cold-air rosy flush on cheeks, natural pale rose hydrated lips. "
            "Wearing an elegant long ivory-white double-faced cashmere coat and a thick cream wool scarf tucked around her neck, dark hair dusted with fine snowflakes. "
            "Ancient vermilion palace wall and snow-dusted corner tower in soft out-of-focus background, gentle winter snowflakes drifting in the air, shot on Leica M11 50mm f/1.4 Summilux, cinematic poetry."
        )
    },
    {
        "id": "day06_02_western_audrey_snow",
        "region": "【欧美】雪域木屋 · 赫本式古典神颜与苏菲玛索柔情",
        "location": "阿尔卑斯雪山木屋露台 · 无暇凝脂肌",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261602,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an extraordinarily beautiful young European woman in a snowy alpine setting with the timeless aristocratic elegance of Audrey Hepburn and the romantic French allure of Sophie Marceau (赫本式高贵骨相、苏菲玛索法式柔情、无暇瓷白肌、绝无雀斑、绝非浓妆). "
            "Flawless, perfectly clear smooth porcelain ivory skin, completely blemish-free and zero freckles, radiant natural winter glow. "
            "Aristocratic classical bone structure, noble high straight nasal bridge, captivating wide deer-like hazel-brown eyes framed by long dark eyelashes, subtle natural laugh lines with an enchanting graceful smile, natural soft pink hydrated lips. "
            "Silky chestnut brown hair loosely styled with gentle French fringe bangs, delicate crystalline snowflakes melting in her hair. "
            "Wearing an oversized cozy cream-white chunky cable-knit mohair sweater, hands holding a warm steaming white mug. "
            "Rustic wooden alpine chalet balcony and snow-capped pine mountains softly blurred in the bright winter sunlight, Contax T2 35mm f/2.8 lens, legendary European cinema realism."
        )
    },
    {
        "id": "day06_03_japan_otaru_snow",
        "region": "【日本】小樽初雪 · 《情书》纯情回忆与毛线耳罩",
        "location": "北海道小樽雪景街角 · 纯净治愈感",
        "workflow": "lora",
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.68,
        "seed": 20261603,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese film portrait of an exquisite young Japanese woman standing in a heavy quiet snowfall in Otaru, Hokkaido (小樽初雪、情书纯情美学、极致透明感与纯净治愈). "
            "Petite delicate Japanese features, soft youthful oval face, airy wispy fringe dusted with powdery white snowflakes, big dewy expressive dark eyes looking straight into the lens with tender warmth, natural rosy peach winter lip gloss. "
            "Translucent glowing fair skin with natural chilly winter pink flush on cheeks and nose tip. "
            "Wearing fluffy plush white earmuffs, an oversized classic navy blue wool duffle coat with wooden toggle buttons, and a voluminous cream knitted scarf. "
            "Soft snowy street lamps and falling snow creating gentle white bokeh circles, Fujifilm Pro 400H emulation, nostalgic Japanese winter cinema aesthetic."
        )
    },
    {
        "id": "day06_04_korea_namsan_snow",
        "region": "【韩国】南山初雪 · 极简白绒大衣与财阀千金",
        "location": "首尔南山雪景庭园 · 现代都会知性",
        "workflow": "lora",
        "lora_name": "girlslikeflux_cdl.safetensors",
        "lora_strength": 0.70,
        "seed": 20261604,
        "steps": 20,
        "prompt": (
            "girlslikeflux_cdl, candid editorial portrait of an extraordinarily elegant modern Korean woman standing on a snow-covered pavilion terrace overlooking winter Seoul (首尔初雪、现代财阀千金极简高智感、冷白皮画报美学). "
            "Refined clean Korean facial contours, smooth noble jawline and slender neck, calm poised intellectual dark eyes, immaculate cool-tone porcelain glass skin, natural soft berry-tinted MLBB hydrated lips. "
            "Sleek silky dark hair parted neatly, fine crystalline snow particles resting on her shoulders. "
            "Wearing a tailored minimalist off-white double-breasted wool-cashmere trench coat belted at the waist, quiet luxury styling. "
            "Snow-laden branches and modern Seoul city skyline softly visible through winter mist, shot on Hasselblad X2D 90mm lens, Vogue Korea winter editorial style."
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
    print("Assembling Day 06 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 06 · 雪霁初晴 · 冬日纯白毛衣与围巾", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · First Snow & Winter Warmth across 4 Global Cultures", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】红墙白雪 · 故宫角楼回眸与白羊绒", "故宫雪后红墙掩映 · 绝美东方骨相 · 白羊绒大衣与雪落长睫"),
        ("【欧美】雪域木屋 · 赫本式古典神颜与苏菲玛索柔情", "阿尔卑斯雪山露台 · 无暇凝脂瓷白肌 · 零雀斑与粗针毛衣"),
        ("【日本】小樽初雪 · 《情书》纯情回忆与毛线耳罩", "北海道小樽雪景街角 · 纯净治愈感 · 牛角扣大衣与温暖小鹿眼"),
        ("【韩国】南山初雪 · 极简白绒大衣与财阀千金", "首尔南山雪景庭园 · 现代都会知性 · 冷白皮与系带羊绒大衣")
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
    md_content = """# Patreon Publish Package · Day 06

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3] Day 06: First Snow & Winter Warmth — China, Alps, Hokkaido & Seoul (Full Set)`
- **Alternative Title (双语备选标题)**: `【雪霁初晴】冬日白毛衣与围巾 · 全球纪实神颜日更 Day 06 · 4K无损胶片原图合集`
- **Tags (标签)**: `FLUX, WinterSnow, FirstSnow, CozyKnitwear, AIPhotography, Photorealism, FilmGrain, StreetPhotography, Portraits, DailySeries`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `day06_winter_snow_4grid.png`
2. **超清无损单图附件 (Standalone High-Res Attachments)**:
   - `day06_01_china_snow.png` (【大陆】故宫雪后红墙掩映 · 绝美东方骨相 · 白羊绒大衣与雪落长睫)
   - `day06_02_western_audrey_snow.png` (【欧美】阿尔卑斯雪山露台 · 无暇凝脂瓷白肌 · 赫本古典骨相与粗针毛衣)
   - `day06_03_japan_otaru_snow.png` (【日本】北海道小樽雪景街角 · 纯净治愈感 · 牛角扣大衣与温暖小鹿眼)
   - `day06_04_korea_namsan_snow.png` (【韩国】首尔南山雪景庭园 · 现代都会知性 · 冷白皮与系带羊绒大衣)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Day 06 · First Snow & Winter Warmth: Global Snowscapes & Cozy Knitwear
雪霁初晴 · 冬日纯白毛衣与围巾 · 全球纪实神颜日更

━━━━━━━━━━━━━━━━━━━━

Welcome to Day 06 of our Daily Candid Realism series!

There is an ethereal purity in the first snowfall—the quiet hush of snow-covered streets, frosty breath catching the winter daylight, cozy oversized knitwear, and the contrast between chilly air and warm rosy expressions.

In today's series, we travel through four winter wonderland scenes across the globe: the crimson walls of Beijing's Forbidden City, an Alpine wooden chalet balcony, a snowy street corner in Otaru, Hokkaido, and a minimalist pavilion overlooking snow-dusted Seoul.

Special aesthetic tuning for our Western portrait today: refined with the aristocratic classical bone structure of Audrey Hepburn and the romantic French warmth of Sophie Marceau—flawless, clear porcelain ivory skin, completely free of blemishes or freckles, paired with chunky cream cable-knit mohair.

Zero heavy makeup, zero artificial AI waxiness. Pure optical winter warmth on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 4 Winter Moments / 今日四组雪境回眸

1. 🇨🇳 Crimson Walls & Winter Snow · 故宫角楼回眸与白羊绒
• Scene: Ancient vermilion palace wall dusted with pristine white snow, snowflakes gently drifting in the cold air.
• Optics: Leica M11 50mm f/1.4 Summilux, cinematic historical grandeur.
• Details: Elegant ivory-white double-faced cashmere coat with thick cream scarf, snowflakes resting on long eyelashes, pure delicate bone structure with cold-air rosy flush on cheeks.

2. 🇪🇺 Alpine Chalet & Hepburn Elegance · 雪山木屋与赫本古典神颜
• Scene: Rustic wooden chalet balcony overlooking snow-capped pine peaks bathed in crisp morning winter sunlight.
• Optics: Contax T2 35mm f/2.8, legendary European cinema realism.
• Details: Classical Audrey Hepburn bone structure blended with Sophie Marceau romantic warmth, flawless clear porcelain skin (zero freckles), wide expressive deer-like hazel eyes, chunky cream cable-knit sweater holding a steaming mug.

3. 🇯🇵 Hokkaido Otaru Nostalgia · 小樽初雪与情书纯情美学
• Scene: Quiet snow-blanketed street in Otaru, Hokkaido, soft snowflakes creating gentle creamy bokeh around vintage street lamps.
• Optics: Fujifilm Pro 400H emulation, quintessential nostalgic winter cinema mood.
• Details: Fluffy plush white earmuffs, classic navy blue wool duffle coat with toggle buttons, cream knitted scarf, dewy expressive eyes filled with tender warmth.

4. 🇰🇷 Seoul Namsan Pavilion · 现代都会千金与极简白绒大衣
• Scene: Minimalist pavilion terrace with panoramic views of snow-covered Seoul through soft winter mist.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial contrast.
• Details: Cool porcelain glass skin, tailored minimalist off-white belted wool-cashmere coat, sleek dark hair with snow particles on the shoulders, calm poised intellectual gaze.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Snowfall & Cold-Air Subsurface Scattering: 精确呈现低温环境下鼻尖与双颊的自然粉嫩微红冻感（Cold-Air Rosy Flush），以及雪花在发丝与睫毛上融化的物理微细节。
• Western Aesthetic Refinement: 针对欧美面容进行高阶古典化调配，彻底剔除过度雀斑假象，还原赫本式雕塑级五官对称度与凝脂白雪肌。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 06 4-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 4 × Full High-Res Standalone Portraits (576 × 1024 无损超清原图，发丝雪花直出)

Which winter scene makes you want to wrap up in a warm scarf the most? Tell me in the comments below!
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
    if "Day 06" not in content:
        day06_row = "| **Day 06** | **《雪霁初晴 · 冬日纯白毛衣与围巾》**<br>故宫红墙白雪、阿尔卑斯赫本古典神颜、小樽初雪情书感、首尔南山极简白大衣 | [`experiments/global_beauties_day06/`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day06/) | [`PATREON_POST.md`](file:///d:/Local-Drama-Studio/experiments/global_beauties_day06/PATREON_POST.md) | [4 联排大图](file:///d:/Local-Drama-Studio/experiments/global_beauties_day06/day06_winter_snow_4grid.png) | 4 张超清原图 |\n"
        content = content.replace("## 🚀 每次发帖 3 步操作指引", day06_row + "\n---\n\n## 🚀 每次发帖 3 步操作指引")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with Day 06!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day06 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day06_winter_snow_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day06_winter_snow_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        write_patreon_md()
        update_master_index()
        print("\nDay 06 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
