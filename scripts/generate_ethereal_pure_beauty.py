"""
Generate Ethereal Pure Beauty (清冷出尘 · 仙品绝代神颜)
Rejecting any heavy makeup, dark styling, or garishness (拒绝浓艳系，拒绝大红唇与暗黑浓妆).
Focus:
- Ethereal, transcendent immortal fairy aesthetic (月下瑶台 / 出尘谪仙)
- Pure translucent porcelain jade skin, natural soft nude-pink lips
- Aristocratic Eastern bone structure (lyf5)
- Diaphanous flowing moon-white silk, gentle night breeze, soft silvery rim lighting
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
OUTPUT_DIR = ROOT / "experiments" / "ethereal_fairy"
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

    prompt = (
        "girlslikeflux_lyf5, breathtaking cinematic portrait of an otherworldly ethereal young East Asian fairy maiden standing at the edge of a misty tranquil mountain pond under soft moonlit night (清冷脱俗、仙气出尘、绝世独立、不食人间烟火、毫无浓艳俗气). "
        "Supreme delicate classical bone structure, smooth noble brow bone, high straight slender jade nose, graceful jawline and slender swan-like neck. "
        "Clear, crystal-pure dark almond eyes filled with tranquil depth and soft starlight catchlights, delicate natural eyelashes, pristine natural bare skin glowing with translucent luminous porcelain jade clarity. "
        "Natural subtle nude pale-pink hydrated petal lips in soft tranquil repose (绝无浓妆、绝无艳红、清水出芙蓉). "
        "Long silky jet-black hair cascading down gracefully, delicate wispy flyaway strands drifting softly in the gentle midnight breeze across her cheek. "
        "Wearing pure flowing ethereal moon-white and sheer mist-cyan diaphanous silk robes, fluttering gently with divine weightlessness. "
        "Soft, diffused silvery moonlight filtering through ancient bamboo mist, casting a delicate luminous halo rim light along her silhouette and hair strands, faint floating starlight motes in the background, 85mm f/1.2 lens, shallow depth of field, authentic film grain, poetic and sublime Eastern aesthetic masterpiece."
    )

    params = {
        "lora_name": "girlslikeflux_lyf5.safetensors",
        "lora_strength": 0.78,
        "positive_prompt": prompt,
        "width": 576,
        "height": 1024,
        "seed": 20261188,
        "steps": 22,
        "cfg": 1.0,
        "filename_prefix": "ethereal_fairy_pure"
    }

    wf = _render(template, params)
    res = queue_prompt(wf)
    pid = res["prompt_id"]
    print(f"Queued prompt_id: {pid} on Intel Arc A750...")

    dst_path = OUTPUT_DIR / "ethereal_fairy_pure.png"
    art_path = ARTIFACTS_DIR / "ethereal_fairy_pure.png"

    start_time = time.time()
    while True:
        hist = get_history(pid)
        if pid in hist:
            outputs = hist[pid].get("outputs", {})
            for nid, nout in outputs.items():
                if "images" in nout and len(nout["images"]) > 0:
                    img_info = nout["images"][0]
                    subfolder = img_info.get("subfolder", "")
                    fname = img_info.get("filename", "")
                    comfy_out = ROOT / "output"
                    if subfolder:
                        comfy_out = comfy_out / subfolder
                    src_file = comfy_out / fname
                    if not src_file.exists():
                        d_output = Path(r"D:\DramaStudio\ComfyUI\output")
                        if subfolder:
                            d_output = d_output / subfolder
                        src_file = d_output / fname

                    if src_file.exists():
                        shutil.copy(src_file, dst_path)
                        shutil.copy(src_file, art_path)
                        print(f"Success! Output saved to: {dst_path}")
                        print(f"Artifact copied to: {art_path}")
                        return
        elapsed = time.time() - start_time
        print(f"Waiting for generation... elapsed: {int(elapsed)}s")
        time.sleep(5)

if __name__ == "__main__":
    main()
