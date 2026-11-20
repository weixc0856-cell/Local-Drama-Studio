"""
Final 9-Grid Cinematic Oriental Beauty Masterpiece Batch Script
Harmonizes top-tier aesthetic face fidelity with rich cinematic environmental storytelling.
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
OUTPUT_DIR = str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "cinematic_masterpiece_9\output")
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

SCENES = [
    {
        "id": "01_wo_shuang_hui_mou",
        "title": "握霜回眸 · 幽林斜阳",
        "pre_existing": str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "aloof_winter_9\output\03_wo_shuang_hui_mou.png"),
        "seed": 20261102,
        "prompt": "girlslikeflux_jjy, medium close-up cinematic portrait, 3/4 over-the-shoulder angle of an exquisite young Chinese woman turning back in a winter forest (中近景回眸、过肩光影、灵动有神). Delicate slender fingers softly tucking the thick cream-white cashmere woolen scarf closer to her neck. Soft wispy air bangs and cheek-framing flyaway hair blowing gently in the winter breeze. Clear dark almond eyes looking back with piercing intelligence and quiet aloof calm, brilliant direct sunlight catchlights reflecting in her pupils. Natural sheer peach lips in relaxed repose. Dark evergreen pine trees blurred softly in deep out-of-focus bokeh background, golden winter rim lighting, 85mm f/1.4, authentic film grain."
    },
    {
        "id": "02_xian_yang_fu_mian",
        "title": "斜阳拂面 · 细雪微温",
        "pre_existing": str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "winter_aloof_test\output\winter_aloof_02_00001_.png"),
        "seed": 20261120,
        "prompt": "girlslikeflux_jjy, breathtaking cinematic 35mm film photograph of an exquisite young Chinese woman with effortless natural beauty and quiet aloof grace (纯正东方骨相、小清新伪素颜、清冷疏离、毫无假感与死感). Quintessential delicate East Asian facial features, smooth flat brow bone with zero deep eye sockets, delicate petite nose with soft refined tip, small slender V-line oval face with a dainty pointed chin and smooth jawline. Soft wispy air bangs and delicate face-framing tendrils casually draping across her forehead and temples, windblown fine flyaways dancing across cheek and eyes. Clear luminous dark brown almond eyes with crisp direct winter sunlight catchlights reflecting in her pupils, pure soulful gaze, quiet aloof composure yet breathing with vivid life. Tender naturally relaxed lips softly parted by a millimeter (透气微张), subtle sheer peach hydration, completely natural lip lines, no smile, no sadness, peaceful living presence. Thick cozy cream-white fluffy cashmere knit scarf wrapped around neck and chin, off-white wool sweater. Golden winter sunlight slicing at a 45-degree angle creating warm rim lights and soft cinematic depth, authentic 35mm film grain, 85mm portrait, masterpiece."
    },
    {
        "id": "03_yang_shou_ning_guang",
        "title": "仰首凝光 · 寒木飞金 (参考图1构图)",
        "pre_existing": None,
        "seed": 20261303,
        "prompt": "girlslikeflux_jjy, medium cowboy shot (thighs up) of an extraordinarily beautiful young Chinese woman in a winter forest, head tilted gracefully upward looking into a beam of golden sunlight streaming through tall pine branches (仰首凝光、纯正东方神颜、天鹅颈). Small delicate V-line oval face, smooth jawline, slender swan neck catching radiant rim light. Soft wispy air bangs and loose dark hair blown back gently by cold breeze. Mesmerizing dark almond eyes reflecting the warm sunbeam, quiet yearning aloof expression filled with poetry and depth. Tender sheer peach lips naturally parted. Wearing a structured dark charcoal-black wool trench coat contrasting with white snow. Deep dark shadowed forest background, glowing dust and snow particles dancing in the sunbeam, 35mm Panavision anamorphic film still, high contrast chiaroscuro masterpiece."
    },
    {
        "id": "04_yue_tai_can_ying",
        "title": "月台残影 · 疾风回眸 (参考图2构图)",
        "pre_existing": None,
        "seed": 20261304,
        "prompt": "girlslikeflux_jjy, breathtaking 35mm film still from a 1990s Wong Kar-wai cinematic masterpiece. An extraordinarily beautiful young Chinese woman with pure exquisite East Asian bone structure and effortless quiet aloof elegance (精致绝美东方骨相、清冷出尘、极度好看). Small slender V-line oval face with a dainty refined chin and smooth delicate jawline, soft wispy air bangs casually draping across her forehead, delicate fine dark hair swept gently by the wind of an arriving train. Mesmerizing, crystal-clear dark brown almond eyes with sharp luminous catchlights reflecting overhead lights. Naturally tender lips softly parted by a millimeter (透气微张), subtle sheer natural peach hydration, no harsh dark lipstick, breathing living beauty. Wearing an oversized heavy black wool trench coat with structured collar. 3/4 over-the-shoulder angle on a subway station platform at night. Beside her, a bright orange and white train rushes past in dramatic dynamic motion blur (动态列车残影). Overhead fluorescent tube lights create powerful leading lines in one-point perspective, 35mm Kodak film grain, masterwork."
    },
    {
        "id": "05_chuang_ying_ning_si",
        "title": "幽窗映雪 · 冷暖双温",
        "pre_existing": None,
        "seed": 20261305,
        "prompt": "girlslikeflux_jjy, cinematic medium shot of an extraordinarily beautiful young Chinese woman leaning gently near an antique wooden lattice window misted with frost (幽窗映影、冷暖双温对撞、电影感框景). Outside is cold cyan-blue winter daylight, while behind her a warm amber lantern casts soft golden light on her hair and porcelain cheek. Her delicate silhouette and contemplative aloof expression are softly mirrored in the misted glass. Small refined oval face, soft wispy air bangs, crystal-clear dark eyes, tender lips naturally relaxed. Wrapped in a cozy cream cashmere knit scarf and soft sweater. Wong Kar-wai cinematic lighting and atmospheric mood, 85mm f/1.4, authentic 35mm film still."
    },
    {
        "id": "06_su_san_wei_xue",
        "title": "素伞微雪 · 漫天飘白",
        "pre_existing": None,
        "seed": 20261306,
        "prompt": "girlslikeflux_jjy, medium shot of an extraordinarily beautiful young Chinese woman holding a vintage cream-white oiled-paper umbrella against gentle falling winter snow (中景撑伞、漫天微雪、出世离尘). Poised on a snow-covered flagstone pathway, slight angle toward camera. Crisp snowflakes drifting through the air, catching soft directional winter sunlight. Small delicate V-line face, soft wispy air bangs, mesmerizing dark eyes with sharp catchlights, serene unapproachable aloof grace. Ivory-white winter coat and thick fluffy cream cashmere scarf. Cool cyan and soft white cinematic color palette, rich fabric texture, 35mm film grain, masterpiece."
    },
    {
        "id": "07_kuang_ye_can_yuan",
        "title": "旷野长风 · 残垣独步 (参考图3构图)",
        "pre_existing": None,
        "seed": 20261307,
        "prompt": "girlslikeflux_jjy, cinematic medium-full shot of an extraordinarily beautiful young Chinese woman walking through a vast windswept winter landscape (旷野长风、古迹残垣、西西里式电影感、极度好看). Towering ancient classical stone arches and weathered stone colonnades in the deep background under a pale azure winter sky. Tall golden dry grass and snow patches swaying in the brisk wind. She walks forward with poised noble composure, long winter coat and cream scarf billowing dynamically in the gust of wind, fine dark hair and air bangs swept across her cheek. Direct golden winter sunlight carving sharp sculptural light and shadow across her exquisite East Asian facial features. Clear soulful dark eyes looking forward with solitary majestic detachment, 35mm anamorphic film still, epic cinematic scale."
    },
    {
        "id": "08_han_mei_fu_xue",
        "title": "寒梅拂雪 · 红白相映",
        "pre_existing": None,
        "seed": 20261308,
        "prompt": "girlslikeflux_jjy, medium close-up cinematic portrait with botanical foreground framing (寒梅拂雪、红白映衬、东方雅韵、神颜灵动). In the upper foreground, a delicate branch of crimson winter plum blossoms laden with crisp white snow cuts gracefully across the frame. Behind the blossoms, she stands looking upward with serene, aloof contemplation. Golden winter sunlight filters through the flowers, casting dappled light across her delicate porcelain skin, soft air bangs, and fluffy white cashmere scarf. Clear sparkling almond eyes, tender naturally parted lips, breathing vitality, shallow depth of field, Hasselblad portrait masterpiece."
    },
    {
        "id": "09_mu_se_lan_diao",
        "title": "暮雪蓝调 · 暖灯微顾",
        "pre_existing": None,
        "seed": 20261309,
        "prompt": "girlslikeflux_jjy, breathtaking cinematic blue hour portrait of an extraordinarily beautiful young Chinese woman at winter dusk (蓝调时刻、冷暖光影、电影大片、神颜回眸). Deep rich indigo-blue twilight sky. In the background, traditional wooden courtyard eaves glow with warm soft amber lantern bokeh. A subtle golden side rim light sculpts her delicate jawline, soft air bangs, and fluffy white cashmere scarf. Clear soulful dark eyes reflecting warm pinpoints of lantern light, tranquil aloof expression, soft natural breathing lips, 35mm Kodak Vision3 film still, masterpiece."
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
    for _ in range(10):
        try:
            with OPENER.open(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            time.sleep(3)
    return {}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(WORKFLOW_TEMPLATE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated_paths = []
    
    for idx, scene in enumerate(SCENES):
        dst_path = os.path.join(OUTPUT_DIR, f"{scene['id']}.png")
        art_path = os.path.join(ARTIFACTS_DIR, f"masterpiece_{scene['id']}.png")

        print(f"\n=======================================================")
        print(f"[{idx+1}/9] Scene: {scene['title']} ({scene['id']})")
        print(f"=======================================================")

        # Check pre-existing verified master files
        if scene["pre_existing"] and os.path.exists(scene["pre_existing"]):
            print(f"Reusing verified approved master asset: {scene['pre_existing']}")
            shutil.copyfile(scene["pre_existing"], dst_path)
            shutil.copyfile(scene["pre_existing"], art_path)
            generated_paths.append(dst_path)
            continue

        if os.path.exists(dst_path) and os.path.getsize(dst_path) > 100000:
            print(f"File already generated, using: {dst_path}")
            shutil.copyfile(dst_path, art_path)
            generated_paths.append(dst_path)
            continue

        # Check if already generated in ComfyUI output
        potential_comfy = os.path.join(str(Path(__file__).resolve().parent.parent / "runtime" / "ComfyUI" / "output"), f"master_{scene['id']}_00001_.png")
        if os.path.exists(potential_comfy) and os.path.getsize(potential_comfy) > 100000:
            print(f"Found existing output in ComfyUI output, copying: {potential_comfy}")
            shutil.copyfile(potential_comfy, dst_path)
            shutil.copyfile(potential_comfy, art_path)
            generated_paths.append(dst_path)
            continue

        params = {
            "lora_name": "girlslikeflux_jjy.safetensors",
            "lora_strength": 0.82,
            "positive_prompt": scene["prompt"],
            "width": 576,
            "height": 1024,
            "seed": scene["seed"],
            "steps": 16,
            "cfg": 1.0,
            "filename_prefix": f"master_{scene['id']}"
        }

        wf = _render(template, params)
        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"Queued prompt_id: {pid} (rendering...)")

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
    grid_img = Image.new("RGB", (w * 3, h * 3), color=(15, 15, 18))
    for i, img in enumerate(images):
        col = i % 3
        row = i // 3
        grid_img.paste(img, (col * w, row * h))

    grid_output = os.path.join(OUTPUT_DIR, "oriental_cinematic_masterpiece_3x3_grid.png")
    grid_art = os.path.join(ARTIFACTS_DIR, "oriental_cinematic_masterpiece_3x3_grid.png")
    grid_img.save(grid_output, quality=95)
    grid_img.save(grid_art, quality=95)
    print(f"\n[DONE] Master 3x3 contact sheet saved to:\n{grid_art}")

if __name__ == "__main__":
    main()
