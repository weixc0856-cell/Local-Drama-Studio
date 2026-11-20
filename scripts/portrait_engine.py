"""
Local Drama Studio · Portrait Engine (v2.0)
Universal, Reusable Industrial Production Engine for High-End AI Portraiture.
Implements the PORTRAIT_PRODUCTION_SOP standard.
"""
import os
import sys
import json
import time
import re
import shutil
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_URL = "http://127.0.0.1:8188"
ROOT = Path(r"d:\Local-Drama-Studio")
WF_LORA = ROOT / "workflows" / "flux3_lora_t2i_api.json"
WF_BASE = ROOT / "workflows" / "flux3_t2i_api.json"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

TARGET_2K_W = 1152
TARGET_2K_H = 2048

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

def wait_for_completion(pid, dst_file, timeout=360):
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
                        elapsed = time.time() - start
                        print(f"  -> Saved base image: {dst_file.name} in {elapsed:.1f}s", flush=True)
                        return elapsed
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return 0

def upscale_image_to_2k_porcelain(file_path, art_file_path=None):
    img = Image.open(file_path).convert("RGB")
    ow, oh = img.size
    print(f"  Upscaling {file_path.name} ({ow}x{oh}) to 2K ({TARGET_2K_W}x{TARGET_2K_H}) with skin preservation...", flush=True)
    up = img.resize((TARGET_2K_W, TARGET_2K_H), Image.Resampling.LANCZOS)
    
    # Gentle unsharp mask for film texture & sharp catchlights
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=3))
    enhancer = ImageEnhance.Contrast(sharpened)
    final_img = enhancer.enhance(1.02)
    
    final_img.save(file_path, "PNG", quality=95)
    if art_file_path:
        shutil.copy(file_path, art_file_path)
    print(f"  -> 2K Upscale Complete: {file_path.name}", flush=True)

def assemble_6grid_board(image_paths, labels, header_main, header_sub, footer_text, board_path, art_board_path=None):
    print(f"Assembling 6-Grid showcase board: {board_path.name}...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    
    thumb_w, thumb_h = 576, 1024
    cards_thumb = [c.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS) for c in cards]
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + thumb_w * 2
    board_h = header_h + margin + (thumb_h + card_title_h) * 3 + margin + footer_h
    
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
                font_bold = ImageFont.truetype(fpath, 40)
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
    draw.text((margin + 10, 35), header_main, fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), header_sub, fill=(100, 105, 115), font=font_med)

    for idx, card in enumerate(cards_thumb):
        col = idx % 2
        row = idx // 2
        
        x = margin + col * (thumb_w + margin)
        y = header_h + margin + row * (thumb_h + card_title_h + margin)
        
        board.paste(card, (x, y))
        
        tx_main, tx_sub = labels[idx]
        text_y_main = y + thumb_h + 10
        text_y_sub = text_y_main + 26
        draw.text((x + 10, text_y_main), tx_main, fill=(30, 30, 35), font=font_med)
        draw.text((x + 10, text_y_sub), tx_sub, fill=(110, 115, 125), font=font_sm)

    foot_y = board_h - footer_h + 18
    draw.text((margin + 10, foot_y), footer_text, fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    if art_board_path:
        shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_set(tasks, output_dir, board_filename, labels, header_main, header_sub, footer_text):
    output_dir.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)
    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(tasks, 1):
        print(f"\n[Portrait Engine - {idx}/{len(tasks)}] Generating: {t['id']} ({t.get('w', 768)}x{t.get('h', 1360)})...", flush=True)
        dst_file = output_dir / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        w = t.get("w", 768)
        h = t.get("h", 1360)
        seed = t.get("seed", 20261100 + idx)
        steps = t.get("steps", 20)
        workflow_type = t.get("workflow", "base")

        if workflow_type == "lora":
            params = {
                "lora_name": t.get("lora_name", "girlslikeflux_lyf5.safetensors"),
                "lora_strength": t.get("lora_strength", 0.55),
                "positive_prompt": t["prompt"],
                "width": w,
                "height": h,
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_lora, params)
        else:
            params = {
                "positive_prompt": t["prompt"],
                "width": w,
                "height": h,
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_base, params)

        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"  Queued prompt_id: {pid} on Intel Arc A750...", flush=True)

        elapsed = wait_for_completion(pid, dst_file)
        if elapsed > 0:
            upscale_image_to_2k_porcelain(dst_file, art_file)
            generated_paths.append(dst_file)
        else:
            print(f"  Failed for {t['id']}", flush=True)

    if len(generated_paths) == len(tasks):
        board_file = output_dir / board_filename
        art_board_file = ARTIFACTS_DIR / board_filename
        assemble_6grid_board(generated_paths, labels, header_main, header_sub, footer_text, board_file, art_board_file)
        print(f"\n[Portrait Engine] Full set generated successfully ({len(generated_paths)} photos + 6-Grid board)!")
        return generated_paths
    return []
