"""
Render the "Jaw-Dropping Masterpiece Beauty" (惊艳天花板 · 极北雪夜孤绝大女主):
Moving far beyond "cute/ordinary pretty" to "overwhelming cinematic awe & aristocratic divinity":
- Obsidian black heavy coat with fur collar contrasting with snow-white porcelain skin
- Aloof, aristocratic, unapproachable divine bone structure (high nasal bridge, phoenix almond eyes with ice crystals)
- Tragic, poetic, breathtaking movie grandeur (Wong Kar-wai / Zhang Yimou aesthetic peak)
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
WF_SINGLE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "experiments" / "jaw_dropping_beauty"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

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

    # Overwhelming Cinematic Beauty: High Contrast, Tragic Grandeur, High-Fashion Aristocracy
    prompt = (
        "girlslikeflux_lyf5, breathtaking cinematic 35mm film still of an unapproachably stunning, divine East Asian empress in a violent snow blizzard (绝世惊艳、盛世神颜、生人勿近、气场封神). "
        "Peerless aristocratic bone structure, knife-sharp elegant jawline, high straight slender nasal bridge, cold piercing dark phoenix almond eyes reflecting distant firelight, "
        "frost and delicate crystalline snowflakes clinging to her long dark eyelashes, subtle melancholic crimson tint around the outer eye corners conveying immense tragic depth. "
        "Full tender lips in a neutral defiant expression, sheer dark berry-red hydration. "
        "Voluminous jet-black silky hair violently whipping across the frame in a fierce icy gale, stray tendrils crossing her pale porcelain cheek. "
        "Wearing a majestic, structured midnight-black heavy wool trench cloak with a voluminous dark fur collar, stark high-contrast against the blinding white blizzard. "
        "Dramatic low-key cinematic lighting, sharp golden sunrise rim light slicing through the dark blue storm clouds, illuminating her profile with glowing crystalline snow particles suspended in mid-air. "
        "Shot on Panavision 70mm anamorphic lens, IMAX movie still, masterclass chiaroscuro, Zhang Yimou style visual power, 8k resolution, awe-inspiring beauty."
    )

    params = {
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.82,
        "positive_prompt": prompt,
        "width": 576,
        "height": 1024,
        "seed": 20261199,
        "steps": 24,
        "cfg": 1.0,
        "filename_prefix": "jaw_dropping_queen"
    }

    wf = _render(template, params)
    res = queue_prompt(wf)
    pid = res["prompt_id"]
    print(f"Queued prompt_id: {pid} on Intel Arc A750...")

    dst_path = OUTPUT_DIR / "jaw_dropping_queen.png"
    art_path = ARTIFACTS_DIR / "jaw_dropping_queen.png"

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
                        src_path = os.path.join(str(Path(__file__).resolve().parent.parent / "runtime" / "ComfyUI" / "output"), sub, fn)
                        shutil.copyfile(src_path, dst_path)
                        shutil.copyfile(src_path, art_path)
                        elapsed = time.time() - start_time
                        print(f"[SUCCESS] Jaw-dropping Masterpiece finished in {elapsed:.1f}s -> {dst_path}")
            break

if __name__ == "__main__":
    main()
