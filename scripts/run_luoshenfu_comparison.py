"""
Generate and compare two distinct aesthetic styles for "Luo Shen Fu" (洛神赋):
Style A: Traditional Chinese Gongbi / Classical Painting (工笔水墨绘本风)
Style B: Guofeng Semi-Realistic Anime / Manhua CG (国漫唯美CG厚涂风)
"""
from __future__ import annotations

import os
import sys
import json
import time
import re
import shutil
import subprocess
import urllib.request
from PIL import Image

BASE_URL = "http://127.0.0.1:8188"
WORKFLOW_SINGLE_LORA = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")
WORKFLOW_DUAL_LORA = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_dual_lora_t2i_api.json")
OUTPUT_DIR = str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "luoshenfu_style_comparison\output")
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

def is_comfy_running() -> bool:
    try:
        req = urllib.request.Request(f"{BASE_URL}/system_stats")
        with OPENER.open(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_comfy_started():
    if is_comfy_running():
        print("[INFO] ComfyUI is already running and responding at 8188.")
        return None
    
    print("[INFO] Starting ComfyUI server in background...")
    comfy_dir = str(Path(__file__).resolve().parent.parent / "runtime" / "ComfyUI")
    comfy_py = os.path.join(comfy_dir, ".venv", "Scripts", "python.exe")
    args = [comfy_py, "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-auto-launch"]
    proc = subprocess.Popen(args, cwd=comfy_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for i in range(45):
        time.sleep(2)
        if is_comfy_running():
            print(f"[INFO] ComfyUI ready after { (i+1)*2 }s!")
            return proc
    raise TimeoutError("ComfyUI did not become ready within 90 seconds.")

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
        "id": "style_a_gongbi",
        "title": "路线 A：新中式工笔淡雅美学 (Gongbi Fine-Line)",
        "workflow_template": WORKFLOW_SINGLE_LORA,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, "
                "ethereal ancient Chinese goddess, Wei-Jin dynasty classical beauty, "
                "refined oval face, delicate willow-leaf eyebrows, serene and melancholic almond eyes, "
                "high classical cloud bun hairstyle with subtle jade and pearl hairpins, "
                "wearing layered pale celadon and ivory silk Wei-Jin hanfu with wide draped sleeves and flowing translucent ribbons. "
                "Standing gracefully on the misty nocturnal Luo riverbank, soft rippling water, floating lotus leaves, "
                "delicate ink wash texture, subtle mineral pigments, misty riverside atmosphere, soft diffused moonlight, "
                "poetic negative space, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261181,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "luoshenfu_style_a_gongbi"
        }
    },
    {
        "id": "style_b_guofeng_anime",
        "title": "路线 B：唯美国漫厚涂CG风 (Guofeng Manhua CG)",
        "workflow_template": WORKFLOW_DUAL_LORA,
        "params": {
            "lora_name_1": "characters\\immortal_lady_v1.safetensors",
            "lora_strength_1": 0.65,
            "lora_name_2": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength_2": 0.55,
            "positive_prompt": (
                "girlslikeflux_lyf5, chinese anime, guofeng manhua illustration, semi-realistic cel shading, "
                "ethereal ancient Chinese goddess, Wei-Jin dynasty classical beauty, "
                "refined oval face, delicate willow-leaf eyebrows, serene and melancholic almond eyes, "
                "high classical cloud bun hairstyle with subtle jade and pearl hairpins, "
                "wearing layered pale celadon and ivory silk Wei-Jin hanfu with wide draped sleeves and flowing translucent ribbons. "
                "Luminous flowing hair, bioluminescent water mist, standing beside the mystical Luo river under starlit night sky, "
                "cinematic rim lighting, Makoto Shinkai inspired starry sky and luminous clouds, clean lineart, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261182,
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": "luoshenfu_style_b_anime"
        }
    }
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    server_proc = ensure_comfy_started()
    generated_images = []

    try:
        for idx, task in enumerate(TASKS):
            print(f"\n=======================================================")
            print(f"[{idx+1}/2] Generating: {task['title']}")
            print(f"=======================================================")
            
            with open(task["workflow_template"], "r", encoding="utf-8") as f:
                template = json.load(f)
            
            wf = _render(template, task["params"])
            res = queue_prompt(wf)
            pid = res["prompt_id"]
            print(f"Queued prompt_id: {pid} (rendering on A750 XPU)...")
            
            start_time = time.time()
            saved_file = None
            
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
                                dst_path = os.path.join(OUTPUT_DIR, f"{task['id']}.png")
                                art_path = os.path.join(ARTIFACTS_DIR, f"{task['id']}.png")
                                shutil.copyfile(src_path, dst_path)
                                shutil.copyfile(src_path, art_path)
                                saved_file = dst_path
                                elapsed = time.time() - start_time
                                print(f"[SUCCESS] {task['id']} finished in {elapsed:.1f}s -> {dst_path}")
                    break
            
            if saved_file:
                generated_images.append(saved_file)
        
        # Create comparison side-by-side composite
        if len(generated_images) == 2:
            print("\nGenerating side-by-side comparison board...")
            img_a = Image.open(generated_images[0])
            img_b = Image.open(generated_images[1])
            w, h = img_a.size
            
            comp = Image.new("RGB", (w * 2 + 20, h), color=(18, 18, 22))
            comp.paste(img_a, (0, 0))
            comp.paste(img_b, (w + 20, 0))
            
            comp_path = os.path.join(OUTPUT_DIR, "luoshenfu_style_comparison_ab.png")
            comp_art = os.path.join(ARTIFACTS_DIR, "luoshenfu_style_comparison_ab.png")
            comp.save(comp_path, quality=95)
            comp.save(comp_art, quality=95)
            print(f"[DONE] Comparison board saved to:\n{comp_art}")

    finally:
        pass

if __name__ == "__main__":
    main()
