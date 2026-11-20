"""
Generate the legendary meme: "Lin Daiyu Uprooting the Weeping Willow" (林黛玉倒拔垂杨柳)
Combining delicate sickly beauty Lin Daiyu with monstrous Lu Zhishen brute strength.
Version 1: Epic Guofeng Anime Action Style (国漫热血高燃暴走版)
Version 2: Traditional Gongbi High-Contrast Satire Style (古典工笔红楼仕女反差版)
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
WF_DUAL = r"d:\Local-Drama-Studio\workflows\flux3_dual_lora_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "daiyu_uproots_willow"
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

TASKS = [
    {
        "id": "daiyu_willow_action_anime",
        "title": "版本一【国漫热血暴走版】倒拔垂杨柳 · 力拔山兮林妹妹",
        "wf": WF_DUAL,
        "params": {
            "lora_name_1": "characters\\scholar_maiden_v1.safetensors",
            "lora_strength_1": 0.70,
            "lora_name_2": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength_2": 0.55,
            "positive_prompt": (
                "girlslikeflux_cdl, chinese anime, guofeng manhua illustration, dynamic wide angle action shot of delicate sickly beauty Lin Daiyu uprooting a giant ancient weeping willow tree with monstrous superhuman strength (林黛玉倒拔垂杨柳、反差神作、力拔山兮气盖世). "
                "Delicate East Asian oval face with knitted sad eyebrows (两弯似蹙非蹙罥烟眉), tearful soulful almond eyes with fierce determined glare, natural rosy lips. High classical bun with freshwater pearls and jade hairpins, loose strands of dark hair wildly blowing in violent wind. "
                "Wearing exquisite traditional pale lilac and white silk hanfu robe with rolled-up wide sleeves showing slender white porcelain arms. She is deep in a martial horse stance (扎马步), slender hands and arms firmly hugging the massive thick trunk of an enormous weeping willow tree, physically lifting and tearing the entire massive tree out of the ground! "
                "Massive twisted roots ripping through explosive cracked soil and mud flying into the air, weeping green willow leaves and broken branches swirling in shockwave air distortion, terrified crows flying away from the canopy. "
                "Set in ancient Grand View Garden (大观园潇湘馆旁) with bamboo grove and traditional courtyard wall in background. Dramatic low-angle cinematic lighting, glowing dust particles, dynamic motion blur, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261118,
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": "daiyu_willow_anime"
        }
    },
    {
        "id": "daiyu_willow_gongbi_satire",
        "title": "版本二【古典工笔冷幽默版】大观园仕女图 · 黛玉神力震乾坤",
        "wf": WF_SINGLE,
        "params": {
            "lora_name": "characters\\scholar_maiden_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_cdl, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, elegant high classical Chinese fine-line painting of Lin Daiyu uprooting a huge weeping willow tree (工笔重彩、大观园奇景、林黛玉倒拔垂杨柳、反差冷幽默). "
                "Slender elegant young noble lady Lin Daiyu, delicate fragile oval face, melancholy willow-leaf eyebrows, quiet composed expression while exerting earth-shattering brute strength. Elegant high bun with jade hairpin and coral bead, wearing authentic Ming-Qing style layered pale celadon and orchid pink silk lady robe, embroidered bamboo hem. "
                "Both slender delicate hands firmly gripping the thick gnarled trunk of an ancient weeping willow, effortlessly pulling the massive tree upward out of the earth. Huge gnarly tree roots dangling with clumps of loose dirt, weeping willow branches sweeping the air. "
                "Traditional Grand View Garden courtyard setting, carved stone railing, stone pathway, bamboo stalks, soft diffused mineral colors, poetic negative space, masterwork gongbi composition"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261119,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "daiyu_willow_gongbi"
        }
    }
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    generated = []

    for idx, task in enumerate(TASKS):
        dst_path = OUTPUT_DIR / f"{task['id']}.png"
        art_path = ARTIFACTS_DIR / f"{task['id']}.png"

        print(f"\n=======================================================")
        print(f"[{idx+1}/2] Rendering: {task['title']}")
        print(f"=======================================================")

        with open(task["wf"], "r", encoding="utf-8") as f:
            template = json.load(f)

        wf = _render(template, task["params"])
        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"Queued prompt_id: {pid} on Intel Arc A750...")

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
                            print(f"[SUCCESS] {task['id']} finished in {elapsed:.1f}s -> {dst_path}")
                            generated.append(dst_path)
                break

    # Stitch comparison side-by-side
    if len(generated) == 2:
        print("\nStitching comparison poster...")
        im1 = Image.open(generated[0])
        im2 = Image.open(generated[1])
        w, h = im1.size
        comp = Image.new("RGB", (w * 2 + 20, h), color=(18, 18, 22))
        comp.paste(im1, (0, 0))
        comp.paste(im2, (w + 20, 0))

        comp_path = OUTPUT_DIR / "daiyu_uprooting_willow_comparison.png"
        comp_art = ARTIFACTS_DIR / "daiyu_uprooting_willow_comparison.png"
        comp.save(comp_path, quality=95)
        comp.save(comp_art, quality=95)
        print(f"[DONE] Comparison poster saved to:\n{comp_art}")

if __name__ == "__main__":
    main()
