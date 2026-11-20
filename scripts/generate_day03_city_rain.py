"""
Generate Day 03 Collection: 《雨后都市 · 伞下与霓虹倒影》 (City Rain & Reflections)
Across 4 Cultures: Mainland China, Western Europe/US, Japan, Korea.
Criteria:
- Authentic rain-slicked urban environments: reflections on wet asphalt, raindrops on umbrella canopy
- Natural damp hair wisps, subtle moisture on skin, cinematic cold-warm color grading (cool rain vs warm lights)
- True optical 35mm/50mm/85mm film photography, zero plastic doll feel
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day03"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day03_01_china_rain",
        "region": "【大陆】江南烟雨 · 青石雨巷与素伞微步",
        "location": "江南古巷细雨微蒙 · 诗意留白",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261301,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, authentic cinematic 35mm film photograph of an extraordinarily beautiful young Chinese woman walking through a misty rain-slicked ancient stone alley (江南烟雨、雨巷回眸、清冷诗意、绝无浓妆假面). "
            "Quintessential delicate East Asian classical bone structure, smooth slender neck and graceful profile, clear dark almond eyes looking back with quiet melancholy depth and soulful warmth. "
            "Pristine porcelain skin with subtle dewiness, natural soft rose petal lips, fine damp dark hair strands gently clinging to her cheek in the humid misty air. "
            "Holding a minimalist bamboo-framed oiled-paper umbrella with delicate translucent raindrops rolling off the edge. "
            "Wearing an elegant long beige double-breasted trench coat draped effortlessly over her shoulders. "
            "Wet blue-grey flagstones reflecting soft amber lanterns from ancient wooden houses, misty rain falling in soft vertical streaks, shot on Leica M11 50mm f/1.4 Summilux, cinematic Wong Kar-wai mood."
        )
    },
    {
        "id": "day03_02_western_rain",
        "region": "【欧美】伦敦雨夜 · 黑色大伞与琥珀街灯",
        "location": "伦敦西区湿漉街道 · 电影感街拍",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261302,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 25-year-old British woman standing on a rain-slicked London street at twilight (伦敦雨夜、英伦风衣、电影感真实光影、原生雀斑与微湿卷发). "
            "Sculpted European bone structure, high refined cheekbones, captivating hazel eyes glistening with reflected city lights, natural light freckles on her nose bridge, authentic skin texture and micro-pores with gentle rain mist. "
            "Tousled damp wavy honey-brown hair framed under a classic large black umbrella, raindrops caught on the black fabric. "
            "Wearing a tailored classic camel wool trench coat with the collar slightly turned up against the cold drizzle. "
            "Glossy wet asphalt reflecting red double-decker bus taillights and warm amber Victorian street lamps in creamy bokeh, Contax T2 35mm f/2.8 lens, authentic documentary realism."
        )
    },
    {
        "id": "day03_03_japan_rain",
        "region": "【日本】东京微雨 · 透明雨伞与霓虹光晕",
        "location": "涩谷/下北泽路口黄昏 · 治愈透明感",
        "workflow": "lora",
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.68,
        "seed": 20261303,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese film portrait of an exquisite young Japanese woman holding a transparent vinyl umbrella on a rainy Tokyo street at dusk (日系透明雨伞、东京微雨、极致空气感、治愈灵动). "
            "Petite delicate Japanese features, smooth oval jawline, airy damp bangs lightly separated by raindrops, big clear expressive dark eyes gazing with quiet warmth directly at the viewer, natural sheer peach lip gloss. "
            "Translucent glowing fair skin with natural soft cheek flush, fine water droplets beading on the clear plastic umbrella above her. "
            "Wearing a cozy oversized navy knit cardigan over a cream turtleneck, holding the umbrella handle with both hands. "
            "Rain-blurred Tokyo storefront neon signs and traffic lights creating beautiful colorful bokeh circles through the wet umbrella, Fujifilm Superia 400 aesthetic, nostalgic cinema mood."
        )
    },
    {
        "id": "day03_04_korea_rain",
        "region": "【韩国】首尔清潭 · 极简冷调与车流光斑",
        "location": "首尔现代都会大道雨夜 · 黑色大女主",
        "workflow": "lora",
        "lora_name": "girlslikeflux_cdl.safetensors",
        "lora_strength": 0.70,
        "seed": 20261304,
        "steps": 20,
        "prompt": (
            "girlslikeflux_cdl, candid editorial portrait of an extraordinarily elegant modern Korean woman standing under a minimalist matte-black umbrella on a rain-drenched Seoul boulevard at night (首尔雨夜、极简冷淡高智感、财阀千金气场、现代都会冷调画报). "
            "Refined clean Korean bone structure, smooth noble jawline and slender neck, calm piercing intellectual gaze, cool porcelain glass skin with realistic micro-texture, natural soft berry-tinted MLBB lips. "
            "Sleek dark straight hair neatly tucked behind ears, water drops sliding down her sharp tailored charcoal-black wool coat with structured shoulders. "
            "Wet granite sidewalk and dark glass skyscrapers reflecting long vertical streaks of cool white headlights and cyan signage, shot on Hasselblad X2D 90mm lens, Vogue Korea rainy night editorial style."
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
    print("Assembling Day 03 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 03 · 雨后都市 · 伞下与霓虹倒影", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · City Rain & Reflections across 4 Global Cultures", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】江南烟雨 · 青石雨巷与素伞微步", "江南古巷细雨微蒙 · 诗意留白 · 油纸伞与石板路反光"),
        ("【欧美】伦敦雨夜 · 黑色大伞与琥珀街灯", "伦敦西区湿漉街道 · 电影感街拍 · 英伦风衣与红巴光晕"),
        ("【日本】东京微雨 · 透明雨伞与霓虹光晕", "涩谷/下北泽路口黄昏 · 治愈透明感 · 胶片水滴与空气感"),
        ("【韩国】首尔清潭 · 极简冷调与车流光斑", "首尔现代都会大道雨夜 · 黑色大女主 · 冷白皮与湿润大衣")
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
        print(f"\n[Day03 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day03_city_rain_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day03_city_rain_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        print("\nDay 03 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
