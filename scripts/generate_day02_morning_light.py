"""
Generate Day 02 Collection: 《晨光漫溢 · 窗边与咖啡》 (Morning Light & Window Breeze)
Across 4 Cultures: Mainland China, Western Europe/US, Japan, Korea.
Criteria:
- Authentic candid morning daylight, cozy unposed moments by window sills
- Translucent natural skin, morning glow, fine hair wisps, relaxed breathing expressions
- True optical 35mm/50mm film aesthetics, zero heavy makeup, zero plastic doll feel
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day02"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day02_01_china_morning",
        "region": "【大陆】晨曦微风 · 窗前白瓷茶盏与素棉",
        "location": "清晨公寓木窗前 · 暖光漫溢",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261201,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, authentic candid 35mm film photograph of a beautiful young Chinese woman relaxing by a sunlit apartment window on a quiet morning (清晨窗边暖阳、生活抓拍、自然慵懒、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender neck and natural jawline, soft morning bedhead dark hair with wispy flyaway strands illuminated by golden side sunlight. "
            "Pristine bare skin with natural micro-texture and soft warm morning glow, natural tender pink hydrated lips, calm affectionate dark almond eyes looking softly towards the camera. "
            "Wearing an oversized cozy ivory ribbed knit cotton sweater, sleeves slightly covering her palms as she holds a warm ceramic tea cup, steam gently rising. "
            "Sheer white linen curtains billowing gently in the soft morning breeze, golden morning sunlight casting long warm shadows across the wooden floor, shot on Leica M11 50mm f/1.4 Summilux, Kodak Portra 400 warmth."
        )
    },
    {
        "id": "day02_02_western_loft",
        "region": "【欧美】纽约Loft · 阳光窗台与意式浓缩",
        "location": "红砖艺廊Loft大窗台 · 慵懒晨光",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261202,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 25-year-old Caucasian woman sitting cross-legged on a wide wooden window seat in a sun-drenched industrial loft (纽约Loft晨光、慵懒随性、真实胶片感、原生雀斑与光晕). "
            "Sculpted European bone structure, high cheekbones, sparkling amber-hazel eyes with natural laugh crinkles, delicate dusting of light freckles across her cheeks and nose bridge, completely authentic skin pores and fine texture. "
            "Tousled sun-bleached golden-brown wavy hair falling effortlessly around her shoulders, rim-lit by bright morning sun. "
            "Wearing a slouchy heather-grey oversized cashmere cardigan over a white ribbed tank top, holding a steaming white ceramic mug in both hands. "
            "Exposed red brick wall and huge industrial grid windows in the background, dust motes dancing in sunbeams, Contax T2 35mm f/2.8 lens, cinematic documentary realism."
        )
    },
    {
        "id": "day02_03_japan_tatami",
        "region": "【日本】京都町屋 · 障子格窗与晨风煎茶",
        "location": "日式町屋庭院廊边 · 纯净通透",
        "workflow": "lora",
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.68,
        "seed": 20261203,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese film portrait of an exquisite young Japanese woman kneeling gently beside an open sliding shoji screen overlooking a morning moss garden (日式町屋晨光、极致透明感、生活气息、纯净治愈). "
            "Petite delicate Japanese features, soft oval face, airy wispy fringe gently grazing her eyebrows with loose strands dancing in the morning garden breeze, clear dewy dark eyes reflecting bright morning sky. "
            "Translucent glowing porcelain skin with realistic natural texture, subtle rosy morning flush on cheeks, natural pale peach lips. "
            "Wearing a minimalist pure white cotton home blouse and soft linen trousers, delicate slender fingers resting lightly beside a traditional handcrafted ceramic green tea cup on tatami mat. "
            "Soft diffused natural daylight filtering through bamboo eaves, gentle green garden bokeh, Fujifilm Pro 400H emulation, peaceful quiet cinematic aesthetic."
        )
    },
    {
        "id": "day02_04_korea_penthouse",
        "region": "【韩国】首尔高空 · 落地全景与冰美式",
        "location": "首尔汉江晨景落地窗前 · 极简画报",
        "workflow": "lora",
        "lora_name": "girlslikeflux_cdl.safetensors",
        "lora_strength": 0.70,
        "seed": 20261204,
        "steps": 20,
        "prompt": (
            "girlslikeflux_cdl, candid editorial portrait of an extraordinarily elegant modern Korean woman standing by a floor-to-ceiling panoramic glass window in a high-rise Seoul penthouse at dawn (首尔汉江晨雾、极简知性高智感、财阀千金晨起、清透冷白肌). "
            "Refined clean Korean facial contours, smooth graceful jawline and slender neck, poised intellectual gaze looking out thoughtfully towards the morning mist over the Han River, natural MLBB soft rose hydrated lips. "
            "Immaculate cool porcelain glass skin with realistic micro-pores, zero heavy makeup, quiet effortless luxury. "
            "Sleek silky black-brown hair casually swept behind one ear, wearing luxurious minimalist ivory silk loungewear robe over a camisole. "
            "Modern minimalist marble side table with an iced Americano glass catching morning light, soft pale blue and silvery morning city glow, shot on Hasselblad X2D 90mm lens, Vogue Korea morning editorial style."
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
    print("Assembling Day 02 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 02 · 晨光漫溢 · 窗边与咖啡", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Morning Light & Window Breeze across 4 Global Cultures", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】晨曦微风 · 窗前白瓷茶盏与素棉", "清晨公寓木窗前 · 暖光漫溢 · 蓬松发丝与微温"),
        ("【欧美】纽约Loft · 阳光窗台与意式浓缩", "红砖艺廊Loft大窗台 · 慵懒晨光 · 微雀斑与自然卷"),
        ("【日本】京都町屋 · 障子格窗与晨风煎茶", "日式町屋庭院廊边 · 纯净通透 · 榻榻米与清透空气感"),
        ("【韩国】首尔高空 · 落地全景与冰美式", "首尔汉江晨景落地窗前 · 极简画报 · 冷白皮与丝缎晨袍")
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

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day02 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day02_morning_light_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day02_morning_light_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        print("\nDay 02 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
