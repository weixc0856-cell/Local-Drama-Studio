"""
Render our absolute crowning masterpiece:
"Snowy Dusk Lantern Beauty" (雪夜掌灯 · 寒梅顾影)
The pinnacle of cinematic East Asian aesthetic portraiture.
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
OUTPUT_DIR = ROOT / "experiments" / "absolute_masterpiece"
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

    # 1. Reuse two proven legendary champion images
    pic1_src = ROOT / "experiments" / "cinematic_masterpiece_9" / "output" / "01_wo_shuang_hui_mou.png"
    pic2_src = ROOT / "experiments" / "dunhuang_feitian" / "output" / "dunhuang_feitian_01_00001_.png"
    
    pic1_dst = ARTIFACTS_DIR / "champion_01_wo_shuang_hui_mou.png"
    pic2_dst = ARTIFACTS_DIR / "champion_02_dunhuang_feitian.png"
    
    if pic1_src.exists():
        shutil.copyfile(pic1_src, pic1_dst)
    if pic2_src.exists():
        shutil.copyfile(pic2_src, pic2_dst)

    # 2. Render the third crowning jewel: "Snowy Dusk Lantern Beauty"
    with open(WF_SINGLE, "r", encoding="utf-8") as f:
        template = json.load(f)

    prompt = (
        "girlslikeflux_jjy, breathtaking 35mm cinematic film portrait of an extraordinarily beautiful young Chinese woman holding a traditional delicate paper lantern in a quiet snowy dusk courtyard (雪夜掌灯、寒梅顾影、神颜清冷、绝世独立). "
        "Pure and refined East Asian facial structure, smooth flat brow bone without deep eye sockets, delicate petite nose with soft refined tip, small slender oval face with smooth jawline. "
        "Wispy air bangs and cheek-framing tendrils casually blown by winter breeze, fine snowflakes gently falling and melting on her dark hair and eyelashes. "
        "Clear luminous dark almond eyes looking slightly aside with soulful aloof composure, brilliant warm candlelight pinpoints reflecting inside her pupils, living breathing presence (毫无死感与假感). "
        "Tender naturally relaxed lips softly parted by a millimeter, sheer coral-peach hydration. "
        "Holding an antique wooden hexagonal paper lantern glowing with soft warm amber light, illuminating her cool porcelain skin with subtle chiaroscuro. "
        "A snow-laden crimson winter plum blossom branch in soft foreground bokeh. Deep indigo-blue twilight background (蓝调时刻), authentic 35mm film grain, 85mm f/1.4, masterpiece."
    )

    params = {
        "lora_name": "girlslikeflux_jjy.safetensors",
        "lora_strength": 0.80,
        "positive_prompt": prompt,
        "width": 576,
        "height": 1024,
        "seed": 20261128,
        "steps": 20,
        "cfg": 1.0,
        "filename_prefix": "champion_03_snow_lantern"
    }

    wf = _render(template, params)
    res = queue_prompt(wf)
    pid = res["prompt_id"]
    print(f"Queued masterpiece prompt_id: {pid} on Intel Arc A750...")

    dst_path = OUTPUT_DIR / "champion_03_snow_lantern.png"
    art_path = ARTIFACTS_DIR / "champion_03_snow_lantern.png"

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
                        print(f"[SUCCESS] Finished in {elapsed:.1f}s -> {dst_path}")
            break

    # 3. Stitch 3-champion showcase board
    images = [
        Image.open(pic1_dst),
        Image.open(pic2_dst),
        Image.open(art_path)
    ]
    w, h = images[0].size
    board = Image.new("RGB", (w * 3 + 20, h), color=(18, 18, 22))
    for i, img in enumerate(images):
        board.paste(img, (i * (w + 10), 0))

    board_path = OUTPUT_DIR / "oriental_champion_trio_board.png"
    board_art = ARTIFACTS_DIR / "oriental_champion_trio_board.png"
    board.save(board_path, quality=95)
    board.save(board_art, quality=95)
    print(f"[DONE] Champion Trio Showcase Board saved to:\n{board_art}")

if __name__ == "__main__":
    main()
