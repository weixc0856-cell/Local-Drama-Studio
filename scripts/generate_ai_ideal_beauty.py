"""
Render AI's Ideal Beauty Definition:
"Pure East Asian Soulful Ethereal Beauty · Morning Breeze & Pure Light" (纯正东方骨相 · 清水芙蓉 · 初恋白月光神颜)
Focus:
- Perfect bone structure (delicate flat brow bone, refined petite nose, dainty oval jawline)
- Soulful intelligent eyes with pristine catchlights (eyes filled with life, calm depth, zero dead look)
- 1mm breathing relaxed parted lips (natural sheer peach hydration)
- Windblown flyaway hair strands catching golden rim light
- Effortless living presence, authentic natural film texture
"""
import os
import sys
import json
import time
import re
import shutil
import urllib.request
from pathlib import Path
from PIL import Image

BASE_URL = "http://127.0.0.1:8188"
WF_SINGLE = r"d:\Local-Drama-Studio\workflows\flux3_lora_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "ideal_beauty"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

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

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_SINGLE, "r", encoding="utf-8") as f:
        template = json.load(f)

    # The AI's ultimate definition of beauty:
    # Natural, effortless, soulful, aristocratic pure bone structure, breathing living presence.
    prompt = (
        "girlslikeflux_jjy, breathtaking natural candid 35mm film portrait of an extraordinarily beautiful young Chinese woman with effortless natural elegance and soulful presence (清水出芙蓉、纯正东方神颜、一眼万年、毫无假感与死感). "
        "Quintessential exquisite East Asian delicate facial structure, smooth flat brow bone with zero harsh eye sockets, delicate petite nose with soft refined tip, small slender V-line oval face with a dainty pointed chin and smooth jawline. "
        "Long silky dark hair gently blown by a soft summer morning breeze, delicate wispy air bangs casually grazing her forehead, fine flyaway strands dancing across her cheek and eyes. "
        "Clear, crystal-pure dark almond eyes looking directly into the camera with quiet intelligence, tenderness, and soulful aloof composure, brilliant pinpoint morning sunlight catchlights sparkling in her pupils. "
        "Naturally relaxed lips softly parted by a single millimeter (透气微张呼吸感), subtle sheer natural peach hydration, completely authentic fine lip lines, peaceful living breathing presence. "
        "Wearing a soft, slightly oversized minimalist ivory-cream linen blouse, collarbone subtly visible. "
        "Soft golden morning sunlight filtering at a 45-degree angle through green leaves, casting delicate rim light on her hair and porcelain jawline. "
        "Lush out-of-focus green garden bokeh in the background, authentic 35mm Kodak Portra film grain, shot on 85mm f/1.2 lens, true cinematic masterpiece, timeless beauty."
    )

    params = {
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.82,
        "positive_prompt": prompt,
        "width": 576,
        "height": 1024,
        "seed": 20261109,
        "steps": 22,
        "cfg": 1.0,
        "filename_prefix": "ai_ideal_beauty"
    }

    wf = _render(template, params)
    res = queue_prompt(wf)
    pid = res["prompt_id"]
    print(f"Queued prompt_id: {pid} on Intel Arc A750...")

    dst_path = OUTPUT_DIR / "ai_ideal_beauty.png"
    art_path = ARTIFACTS_DIR / "ai_ideal_beauty.png"

    start_time = time.time()
    while True:
        time.sleep(3)
        h = get_history(pid)
        if pid in h:
            outputs = h[pid]["outputs"]
            for node_id, node_out in outputs.items():
                if "images" in node_out:
                    for img_meta in node_out["images"]:
                        fn = img_meta["filename"]
                        sub = img_meta.get("subfolder", "")
                        src_path = os.path.join(r"d:\Local-Drama-Studio\runtime\ComfyUI\output", sub, fn)
                        shutil.copyfile(src_path, dst_path)
                        shutil.copyfile(src_path, art_path)
                        elapsed = time.time() - start_time
                        print(f"[SUCCESS] AI Ideal Beauty finished in {elapsed:.1f}s -> {dst_path}")
            break

if __name__ == "__main__":
    main()
