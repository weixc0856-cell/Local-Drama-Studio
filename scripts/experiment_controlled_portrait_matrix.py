"""
Controlled Portrait Experiment Matrix:
Systematically evaluates Resolution, LoRA Strength, and Prompt Architecture
to solve facial breakdown, plastic skin, and compositional homogeneity.

Test Matrix:
- Case 1 [Baseline]: 576x1024, LoRA 0.68, Adjective Stack + Forced Smile
- Case 2 [Prompt Reform]: 576x1024, LoRA 0.68, Cinematic Shot Spec + Soft Breathing Repose
- Case 3 [High Native 768]: 768x1360, LoRA 0.55, Cinematic Shot Spec + Soft Breathing Repose
- Case 4 [Ultra Native 864]: 864x1536, LoRA 0.55, Cinematic Shot Spec + Soft Breathing Repose

Fixed Variables:
- Model: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750
- Seed: 20261221 (Fixed)
- Steps: 20, CFG: 1.0
- Subject: Chinese leading actress walking in 1960s Shanghai rain alley in silk qipao with bamboo umbrella
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
ROOT = Path(r"d:\Local-Drama-Studio")
EXP_DIR = ROOT / "experiments" / "portrait_quality_ab_test"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

PROMPT_LEGACY_ADJECTIVES = (
    "girlslikeflux_lyf5, award-winning cinematic 35mm film still of an extraordinarily gorgeous 21-year-old Chinese leading actress walking in a 1960s vintage Shanghai alleyway (王家卫大师级电影构图、21岁东方绝色天仙女主角、侧身漫步优雅回眸、打破死板证件照、环境人像中景半身、明艳从容浅笑、绝无苦相、饱满胶原蛋白、平整紧致鹅蛋脸). "
    "Master professional photographer composition: Dynamic over-the-shoulder three-quarter angle, walking under an ancient brick archway creating natural architectural sub-framing. "
    "Delicately holding a dark oiled bamboo umbrella in one slender hand, other arm resting naturally, showing slender waist and graceful posture, face occupying roughly 22 percent of frame height along the rule of thirds. "
    "Sparkling dark almond eyes filled with warm lively intelligence, sweet captivating gentle smile with upturned lip corners, relaxed open brow. "
    "Wearing a tailored high-neck emerald-green liquid silk jacquard qipao. "
    "Rain-slicked cobblestone street, soft amber streetlamp backlighting casting a golden rim on her hair, wet asphalt reflections, 50mm anamorphic lens, breathtaking cinematic depth."
)

PROMPT_CINEMATIC_SHOT_SPEC = (
    "girlslikeflux_lyf5, 35mm environmental portrait, waist-up framing with natural negative breathing room. "
    "A 21-year-old Chinese woman walking at a 35-degree three-quarter angle under a weathered brick archway in a 1960s Shanghai rain alley, turning back over her shoulder. "
    "Delicate symmetrical oval face, smooth brow, clear dark almond eyes looking back with quiet luminous poise, naturally plump rose lips slightly parted in soft calm breathing repose with relaxed natural mouth corners, realistic fine skin pores and natural warmth. "
    "Silky dark hair in a loose vintage updo with soft damp wisps framing her neck. "
    "Wearing a tailored emerald-green silk jacquard high-neck qipao showing an elegant waist and shoulder curve. "
    "Slender fingers naturally grasping the dark bamboo handle of an oiled paper umbrella. "
    "Rain-slicked stone pavement reflecting warm amber streetlamps, soft atmospheric mist, Kodak Vision3 500T 50mm f/1.8 lens, cinematic three-dimensional depth."
)

CASES = [
    {
        "id": "case1_baseline_576_legacy",
        "label": "Case 1: 基线 (576x1024 | LoRA 0.68 | 形容词+咧嘴笑)",
        "w": 576,
        "h": 1024,
        "lora_strength": 0.68,
        "prompt": PROMPT_LEGACY_ADJECTIVES
    },
    {
        "id": "case2_reform_576_shot_spec",
        "label": "Case 2: 镜头语言改革 (576x1024 | LoRA 0.68 | 呼吸感微表情)",
        "w": 576,
        "h": 1024,
        "lora_strength": 0.68,
        "prompt": PROMPT_CINEMATIC_SHOT_SPEC
    },
    {
        "id": "case3_high_native_768",
        "label": "Case 3: 高清原生 (768x1360 | LoRA 0.55 | 真实皮质)",
        "w": 768,
        "h": 1360,
        "lora_strength": 0.55,
        "prompt": PROMPT_CINEMATIC_SHOT_SPEC
    },
    {
        "id": "case4_ultra_native_864",
        "label": "Case 4: 极限原生 (864x1536 | LoRA 0.55 | 极致细节)",
        "w": 864,
        "h": 1536,
        "lora_strength": 0.55,
        "prompt": PROMPT_CINEMATIC_SHOT_SPEC
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

def wait_for_completion(pid, dst_file, timeout=300):
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
                        print(f"-> Saved {dst_file.name} in {elapsed:.1f}s", flush=True)
                        return elapsed
        time.sleep(3)
    print(f"Timeout waiting for {pid}", flush=True)
    return 0

def make_comparison_matrix(results, matrix_path, art_matrix_path):
    print("Generating side-by-side comparison matrix with face closeups...", flush=True)
    
    col_w = 480
    body_h = 760
    face_crop_size = 280
    header_h = 130
    footer_h = 60
    card_title_h = 70
    margin = 24
    
    total_w = margin + (col_w + margin) * len(results)
    total_h = header_h + margin + body_h + margin + face_crop_size + card_title_h + margin + footer_h
    
    matrix_img = Image.new("RGB", (total_w, total_h), (242, 244, 247))
    draw = ImageDraw.Draw(matrix_img)
    
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
                font_bold = ImageFont.truetype(fpath, 36)
                font_med = ImageFont.truetype(fpath, 18)
                font_sm = ImageFont.truetype(fpath, 14)
                break
            except Exception:
                continue
    if not font_bold:
        font_bold = ImageFont.load_default()
        font_med = font_bold
        font_sm = font_bold

    # Header
    draw.text((margin + 10, 25), "人像质量优化与控制变量对照实验矩阵 (Portrait Quality Controlled A/B Matrix)", fill=(20, 25, 35), font=font_bold)
    draw.text((margin + 12, 75), "单变量对比：生成分辨率 (576 vs 768 vs 864) · 提示词构架 (形容词堆叠 vs 镜头语言) · 脸部解剖真实现象", fill=(90, 100, 115), font=font_med)

    for i, r in enumerate(results):
        x = margin + i * (col_w + margin)
        y_body = header_h + margin
        
        orig_img = Image.open(r["file_path"]).convert("RGB")
        ow, oh = orig_img.size
        
        # 1. Body thumbnail
        thumb_body = orig_img.resize((col_w, body_h), Image.Resampling.LANCZOS)
        matrix_img.paste(thumb_body, (x, y_body))
        
        # 2. Crop Face Closeup (roughly upper 15%-45% of image, centered horizontally)
        fx1 = int(ow * 0.28)
        fy1 = int(oh * 0.14)
        fx2 = int(ow * 0.72)
        fy2 = int(oh * 0.44)
        face_crop = orig_img.crop((fx1, fy1, fx2, fy2)).resize((col_w, face_crop_size), Image.Resampling.LANCZOS)
        
        y_face = y_body + body_h + 16
        matrix_img.paste(face_crop, (x, y_face))
        
        # Label & Metrics
        y_text = y_face + face_crop_size + 12
        draw.text((x + 6, y_text), r["label"], fill=(25, 30, 40), font=font_med)
        stat_line = f"耗时: {r['elapsed']:.1f}s | 原始尺寸: {ow}x{oh} | LoRA: {r['lora']}"
        draw.text((x + 6, y_text + 26), stat_line, fill=(100, 110, 125), font=font_sm)

    foot_y = total_h - footer_h + 16
    draw.text((margin + 10, foot_y), "Local Drama Studio Quality Engineering | Fixed Seed: 20261221 | Steps: 20 | CFG: 1.0", fill=(140, 145, 155), font=font_sm)

    matrix_img.save(matrix_path, "PNG", quality=95)
    shutil.copy(matrix_path, art_matrix_path)
    print(f"Matrix comparison saved to: {matrix_path}", flush=True)

def main():
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_LORA, "r", encoding="utf-8") as f:
        tpl_lora = json.load(f)

    results = []

    for c in CASES:
        print(f"\n[A/B Experiment] Running {c['id']}: {c['label']}...", flush=True)
        dst_file = EXP_DIR / f"{c['id']}.png"
        
        params = {
            "lora_name": "girlslikeflux_lyf5.safetensors",
            "lora_strength": c["lora_strength"],
            "positive_prompt": c["prompt"],
            "width": c["w"],
            "height": c["h"],
            "seed": 20261221,
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": c["id"]
        }
        wf = _render(tpl_lora, params)

        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"  Queued prompt_id: {pid} ({c['w']}x{c['h']})...", flush=True)
        elapsed = wait_for_completion(pid, dst_file)
        
        results.append({
            "id": c["id"],
            "label": c["label"],
            "w": c["w"],
            "h": c["h"],
            "lora": c["lora_strength"],
            "file_path": dst_file,
            "elapsed": elapsed
        })

    matrix_path = EXP_DIR / "portrait_quality_ab_matrix.png"
    art_matrix_path = ARTIFACTS_DIR / "portrait_quality_ab_matrix.png"
    make_comparison_matrix(results, matrix_path, art_matrix_path)
    print("\nA/B Matrix test finished successfully!", flush=True)

if __name__ == "__main__":
    main()
