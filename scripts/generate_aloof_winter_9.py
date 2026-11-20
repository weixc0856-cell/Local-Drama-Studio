"""
Batch generation script for 9-grid Cinematic Oriental Winter Aloof Beauty Series
Focus: Rich environmental storytelling, varied shot framing (wide, medium, framed, over-shoulder),
eliminating 'only big-face close-ups' while maintaining the approved alive, aloof, ethereal aesthetic.
"""
from __future__ import annotations

import os
import sys
import json
import time
import re
import shutil
import urllib.request
from PIL import Image

BASE_URL = "http://127.0.0.1:8188"
WORKFLOW_TEMPLATE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")
OUTPUT_DIR = str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "aloof_winter_9\output")
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

# Never route localhost through system/env proxy
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

SCENES = [
    {
        "id": "01_xue_ye_quan_jing",
        "title": "雪野长卷 (远景/环境大景)",
        "seed": 20261201,
        "prompt": "girlslikeflux_jjy, breathtaking wide cinematic 35mm film photograph of an exquisite young Chinese woman standing solitary in an expansive snow-covered winter field (远景大景、天地一色、空灵留白). Full environmental framing, vast snowy landscape with distant frost-covered pine mountains under a pale silver sky. She stands poised in the lower-third golden section, wearing a flowing ivory-white wool trench coat and thick cream cashmere scarf. Soft winter wind sweeping her coat and sending loose wisps of hair and air bangs dancing across her face. Clear, calm, unapproachable aloof expression gazing into the silent white expanse, pure East Asian delicate bone structure. Authentic 35mm film grain, expansive poetic negative space, masterpiece."
    },
    {
        "id": "02_ting_xuan_du_li",
        "title": "寒轩听雪 (中景/建筑框景)",
        "seed": 20261202,
        "prompt": "girlslikeflux_jjy, cinematic medium shot of an exquisite young Chinese woman leaning gently on the dark wooden railing of a traditional winter pavilion (中景构图、倚轩凭栏、借景融情). Pure East Asian delicate facial features, smooth flat brow bone, small refined chin, soft air bangs framing forehead. Delicate hand resting gracefully on the snow-dusted carved railing. Framed in the foreground by soft out-of-focus pine branches heavy with white snow. Wearing an ivory knit coat and cozy cream-white woolen scarf. Overcast soft winter daylight illuminating her cool porcelain skin with subtle side shadow, calm aloof and soulful gaze, natural relaxed breathing lips, authentic film still."
    },
    {
        "id": "03_wo_shuang_hui_mou",
        "title": "握霜回眸 (中近景/过肩叙事)",
        "seed": 20261203,
        "prompt": "girlslikeflux_jjy, medium close-up cinematic portrait, 3/4 over-the-shoulder angle of an exquisite young Chinese woman turning back in a winter forest (中近景回眸、过肩光影、灵动有神). Delicate slender fingers softly tucking the thick cream-white cashmere woolen scarf closer to her neck. Soft wispy air bangs and cheek-framing flyaway hair blowing gently in the winter breeze. Clear dark almond eyes looking back with piercing intelligence and quiet aloof calm, brilliant direct sunlight catchlights reflecting in her pupils. Natural sheer peach lips in relaxed repose. Dark evergreen pine trees blurred softly in deep out-of-focus bokeh background, golden winter rim lighting, 85mm f/1.4, authentic film grain."
    },
    {
        "id": "04_zhi_san_xue_zhong",
        "title": "素伞拂雪 (中景/雪中动态)",
        "seed": 20261204,
        "prompt": "girlslikeflux_jjy, cinematic medium full shot of an exquisite young Chinese woman holding a vintage minimalist oiled-paper umbrella under gentle falling winter snow (中景撑伞、漫天微雪、出世离尘). Standing solitary on a snow-covered flagstone garden path. Light snowflakes drifting through the air, catching the light. She holds the umbrella poised at an angle, half-turned toward the camera with quiet aloof dignity. Elegant long white winter coat, voluminous cream scarf, delicate East Asian bone structure, air bangs, tranquil breathing expression, cool cyan and pristine white cinematic color grading, 35mm film still."
    },
    {
        "id": "05_chuang_ying_ning_si",
        "title": "幽窗映雪 (光影框景/虚实交错)",
        "seed": 20261205,
        "prompt": "girlslikeflux_jjy, cinematic framed shot of an exquisite young Chinese woman standing beside an antique wooden lattice window misted with winter frost (幽窗映影、冷暖双色温、电影感框景). Outside the window is cold blue snowy daylight, while behind her glows subtle warm amber lantern light. Her delicate profile and aloof contemplative expression are softly reflected in the misted glass pane. Pure porcelain skin, wispy air bangs, loose hair strands, cream cashmere scarf, naturally relaxed parted lips, profound quiet storytelling depth, Wong Kar-wai style cinematic chiaroscuro, 8k masterpiece."
    },
    {
        "id": "06_xue_jie_du_xing",
        "title": "雪阶独步 (全景/纵深构图)",
        "seed": 20261206,
        "prompt": "girlslikeflux_jjy, breathtaking full-length cinematic shot of an exquisite young Chinese woman walking up ancient stone steps covered in pristine white snow (全景纵深、拾阶而上、孤绝脱俗). Leading between towering silent winter bamboo and snow-dusted rockeries. She is caught in mid-stride, turning back slightly over her shoulder, her elegant white coat swaying in the motion. Thick cream-white scarf loosely draped, air bangs fluttering in the cold wind. Poised solitary elegance, deep perspective leading lines, authentic 35mm film texture."
    },
    {
        "id": "07_han_mei_ying_shuang",
        "title": "寒梅拂雪 (中近景/植物借景)",
        "seed": 20261207,
        "prompt": "girlslikeflux_jjy, cinematic medium close-up shot with botanical foreground framing (寒梅拂雪、红白映衬、东方雅韵). In the foreground, a delicate branch of crimson winter plum blossoms laden with crisp white snow cuts across the composition. Behind the blossoms, she stands looking upward with serene, aloof contemplation. Golden winter sunlight filters through the branches, casting dappled light across her delicate East Asian features, air bangs, and cream-white cashmere scarf. Translucent skin, soulful sparkling eyes, peaceful breathing lips, Hasselblad portrait."
    },
    {
        "id": "08_lan_ting_yuan_tiao",
        "title": "凭栏远眺 (中远景/环境叙事)",
        "seed": 20261208,
        "prompt": "girlslikeflux_jjy, medium-wide cinematic shot of an exquisite young Chinese noble woman standing at a stone lakeside pavilion overlooking a vast misty frozen lake (中远景环境叙事、寒潭烟水、孤高自许). Winter mist drifting over the ice and distant snow-capped hills. She stands with upright noble posture, hands tucked warmly into her coat, looking out across the water with detached solitary grace. Winter wind blowing her hair and the fringes of her white scarf, breathtaking atmospheric scale, cinematic 2.39:1 widescreen mood, 35mm film grain."
    },
    {
        "id": "09_mu_se_lan_diao",
        "title": "暮雪蓝调 (中景/蓝调时刻光影)",
        "seed": 20261209,
        "prompt": "girlslikeflux_jjy, breathtaking cinematic blue hour portrait of an exquisite young Chinese woman at winter dusk (蓝调时刻、冷暖光影、电影质感大片). Deep rich indigo-blue twilight sky. In the background, traditional courtyard eaves glow with warm soft amber lantern bokeh. A subtle golden side rim light sculpts her delicate jawline, soft air bangs, and fluffy white cashmere scarf. Clear soulful dark eyes reflecting warm pinpoints of lantern light, tranquil aloof expression, soft natural breathing lips, 35mm Kodak Portra film still, masterpiece."
    }
]

def queue_prompt(prompt_workflow):
    data = json.dumps({"prompt": prompt_workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/prompt", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_history(prompt_id):
    req = urllib.request.Request(f"{BASE_URL}/history/{prompt_id}")
    with OPENER.open(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(WORKFLOW_TEMPLATE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated_paths = []
    
    for idx, scene in enumerate(SCENES):
        dst_path = os.path.join(OUTPUT_DIR, f"{scene['id']}.png")
        art_path = os.path.join(ARTIFACTS_DIR, f"winter_aloof_{scene['id']}.png")

        print(f"\n=======================================================")
        print(f"[{idx+1}/9] Scene: {scene['title']} ({scene['id']})")
        print(f"=======================================================")

        params = {
            "lora_name": "girlslikeflux_jjy.safetensors",
            "lora_strength": 0.80,
            "positive_prompt": scene["prompt"],
            "width": 576,
            "height": 1024,
            "seed": scene["seed"],
            "steps": 16,
            "cfg": 1.0,
            "filename_prefix": f"winter_scene_{scene['id']}"
        }

        wf = _render(template, params)
        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"Queued prompt_id: {pid} (waiting for render...)")

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
                            print(f"Finished {scene['id']} in {elapsed:.1f}s -> {dst_path}")
                            generated_paths.append(dst_path)
                break

    # Build 3x3 contact sheet
    print("\nStitching 3x3 contact sheet...")
    images = [Image.open(p) for p in generated_paths]
    w, h = images[0].size
    grid_img = Image.new("RGB", (w * 3, h * 3), color=(18, 18, 20))
    for i, img in enumerate(images):
        col = i % 3
        row = i // 3
        grid_img.paste(img, (col * w, row * h))

    grid_output = os.path.join(OUTPUT_DIR, "oriental_winter_cinematic_3x3_grid.png")
    grid_art = os.path.join(ARTIFACTS_DIR, "oriental_winter_cinematic_3x3_grid.png")
    grid_img.save(grid_output, quality=95)
    grid_img.save(grid_art, quality=95)
    print(f"3x3 Contact sheet saved successfully to: {grid_art}")

if __name__ == "__main__":
    main()
