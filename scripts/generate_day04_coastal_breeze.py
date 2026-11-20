"""
Generate Day 04 Collection: 《夏末海风 · 沿海公路与碧海蓝天》 (Coastal Breeze & Ocean Vistas)
Across 4 Cultures: Mainland China, Western Europe/US, Japan, Korea.
Criteria:
- Authentic coastal environments: open coastal highways, ocean seawalls, sea spray, wind-blown hair dynamics
- Natural sun-kissed skin glow, realistic micro-textures, authentic wind motion, zero plastic doll feel
- True optical 35mm/50mm/90mm film photography
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
OUTPUT_DIR = ROOT / "experiments" / "global_beauties_day04"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "day04_01_china_coastal",
        "region": "【大陆】环岛公路 · 海风白衬衫与灿烂初阳",
        "location": "海南/万宁滨海公路 · 自由漫游",
        "workflow": "lora",
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.72,
        "seed": 20261401,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, authentic candid 35mm film photograph of an extraordinarily beautiful young Chinese woman standing beside a sun-drenched coastal highway in tropical Hainan (滨海公路自驾、海风吹拂、自由灵动、绝无浓妆假面). "
            "Delicate East Asian classical bone structure, smooth slender neck and graceful jawline, radiant genuine smile with bright joyful almond eyes looking towards the camera. "
            "Sun-kissed glowing skin with natural micro-texture and fine pores, natural dewy peach lips. "
            "Long silky dark hair vigorously blown by the warm ocean breeze with strands dancing across her laughing face. "
            "Wearing a crisp oversized white linen button-down shirt fluttering in the wind over a simple cotton tank, sleeves loosely rolled. "
            "Turquoise ocean waves crashing against coastal rocks and tropical palm tree shadows in the bright sunny background, shot on Leica M11 50mm f/1.4 Summilux, vibrant natural daylight, Kodak Portra 400 warmth."
        )
    },
    {
        "id": "day04_02_western_highway",
        "region": "【欧美】加州一号公路 · 黄金海岸复古敞篷",
        "location": "加州大瑟尔海岸悬崖公路 · 绝美落日",
        "workflow": "base",
        "lora_name": None,
        "lora_strength": 0.0,
        "seed": 20261402,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 25-year-old Caucasian woman seated in a vintage convertible on the Pacific Coast Highway in California at golden hour (加州一号公路、复古敞篷车、黄金海岸落日、海风飞扬卷发). "
            "Sculpted European bone structure, high refined cheekbones, sparkling warm hazel eyes with natural laugh lines, delicate dusting of natural freckles across her sun-warmed nose bridge and cheeks, authentic skin texture with visible micro-pores. "
            "Voluminous wavy golden-blonde hair violently whipped by coastal wind with radiant golden backlit rim light, vintage tortoiseshell sunglasses pushed up into her hair. "
            "Wearing a casual slouchy off-white knitted tank top, dainty layered gold chains. "
            "Steep coastal cliffs, winding asphalt highway, and the endless sparkling Pacific Ocean glowing in molten orange sunset light in the background, Contax T2 35mm f/2.8 lens, cinematic documentary realism."
        )
    },
    {
        "id": "day04_03_japan_okinawa",
        "region": "【日本】冲绳离岛 · 堤坝草帽与纯白棉裙",
        "location": "冲绳竹富岛防波堤 · 盛夏碧海",
        "workflow": "lora",
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.68,
        "seed": 20261403,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese film portrait of an exquisite young Japanese woman standing on a concrete seawall overlooking a crystal-clear turquoise sea in Okinawa (冲绳夏日防波堤、海风拂面、草帽纯白棉裙、极致透明感与纯真). "
            "Petite delicate Japanese features, soft youthful oval face, airy wispy fringe blown sideways by ocean breeze, big expressive dark eyes filled with pure summer clarity and tenderness, natural fresh nude-peach lip gloss. "
            "Translucent fair porcelain skin with natural soft flush on sun-warmed cheeks, holding down a wide-brimmed woven straw hat with one delicate slender hand against the sea wind. "
            "Wearing a breezy pure white cotton sleeveless sundress fluttering in the wind, simple canvas shoulder tote. "
            "Pristine bright emerald-blue ocean water sparkling in the afternoon sun with white sea foam, Fujifilm Pro 400H emulation, quintessential nostalgic Japanese summer cinema aesthetic."
        )
    },
    {
        "id": "day04_04_korea_jeju",
        "region": "【韩国】济州海岸 · 玄武岩露台与度假千金",
        "location": "济州岛黑色玄武岩海景露台 · 极简画报",
        "workflow": "lora",
        "lora_name": "girlslikeflux_cdl.safetensors",
        "lora_strength": 0.70,
        "seed": 20261404,
        "steps": 20,
        "prompt": (
            "girlslikeflux_cdl, candid editorial portrait of an extraordinarily elegant modern Korean woman standing by a glass railing on the oceanfront terrace of a minimalist modern cafe in Jeju Island (济州岛海景露台、玄武岩与碧海、财阀千金度假画报、冷白皮极简高级感). "
            "Refined clean Korean facial contours, smooth elegant jawline, calm intellectual dark eyes with direct poised gaze, natural soft rose MLBB hydrated lips. "
            "Flawless cool-tone porcelain glass skin with realistic micro-texture, zero heavy makeup, quiet understated luxury. "
            "Sleek dark straight hair blowing gracefully in the ocean wind, wearing an oversized flowing champagne silk resort shirt over a white ribbed crop top and wide-leg linen trousers. "
            "Dramatic black volcanic basalt rocks meeting deep sapphire ocean waves in the background, modern architectural concrete lines, shot on Hasselblad X2D 90mm lens, Vogue Korea resort editorial style."
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
    print("Assembling Day 04 showcase board...", flush=True)
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
    draw.text((margin + 10, 35), "Day 04 · 夏末海风 · 沿海公路与碧海蓝天", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Late Summer Coastal Breeze across 4 Global Shores", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆】环岛公路 · 海风白衬衫与灿烂初阳", "海南/万宁滨海公路 · 自由漫游 · 碧海椰影与开朗笑容"),
        ("【欧美】加州一号公路 · 黄金海岸复古敞篷", "加州大瑟尔海岸公路 · 绝美落日 · 金发飞扬与复古墨镜"),
        ("【日本】冲绳离岛 · 堤坝草帽与纯白棉裙", "冲绳竹富岛防波堤 · 盛夏碧海 · 纯白棉裙与治愈透明感"),
        ("【韩国】济州海岸 · 玄武岩露台与度假千金", "济州岛黑色玄武岩海景露台 · 极简画报 · 冷白皮与香槟丝绸")
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
        print(f"\n[Day04 - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
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
        board_path = OUTPUT_DIR / "day04_coastal_breeze_4grid.png"
        art_board_path = ARTIFACTS_DIR / "day04_coastal_breeze_4grid.png"
        make_4grid_board(generated_paths, board_path, art_board_path)
        print("\nDay 04 completed successfully!", flush=True)

if __name__ == "__main__":
    main()
