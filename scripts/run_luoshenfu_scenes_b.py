"""
Batch render 5 storyboard keyframes for "Luo Shen Fu" (洛神赋):
Style: Route B (Guofeng Manhua CG / Thick-Coating Anime)
Hardware: FLUX.3 Klein + Intel Arc A750 8GB
"""
import os
import sys
import json
import time
import re
import shutil
import urllib.request
from PIL import Image

BASE_URL = "http://127.0.0.1:8188"
WF_SINGLE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_lora_t2i_api.json")
WF_DUAL = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_dual_lora_t2i_api.json")

OUTPUT_DIR = str(Path(os.environ.get("DRAMA_OUTPUT_ROOT", Path(__file__).resolve().parent.parent / "studio_data")) / "experiments" / "luoshenfu_style_comparison\scenes")
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

SCENES = [
    {
        "id": "S01_luo_river_dusk",
        "title": "S01【洛水暮色】黄昏日暮，车马暂歇",
        "wf": WF_SINGLE,
        "params": {
            "lora_name": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength": 0.65,
            "positive_prompt": (
                "chinese anime, guofeng manhua illustration, breathtaking wide cinematic landscape, "
                "vast Luo river at twilight dusk (日暮黄昏、洛水苍茫、大景空灵). "
                "Golden and purple sunset glow reflecting on misty rippling water, ancient Chinese royal carriage "
                "and resting horses on the grassy riverbank, atmospheric evening mist, floating lotus leaves, "
                "poetic negative space, Makoto Shinkai clouds, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261101,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "lsf_s01_dusk"
        }
    },
    {
        "id": "S02_scholar_rocks",
        "title": "S02【岸畔伫立】曹植立岩，凭虚远眺",
        "wf": WF_SINGLE,
        "params": {
            "lora_name": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength": 0.65,
            "positive_prompt": (
                "chinese anime, guofeng manhua illustration, medium wide shot, "
                "young noble ancient Chinese scholar-poet standing by mossy riverbank rocks (岸畔伫立、凭虚远眺、玄衣博带). "
                "Three-quarter back view over shoulder, wearing elegant deep navy-black Wei-Jin scholar robe with wide draped sleeves, "
                "gazing into the vast misty river at dusk, wind blowing hair ribbons and robe hem, "
                "mysterious magical glowing atmosphere on the distant water, cinematic lighting, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261102,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "lsf_s02_scholar"
        }
    },
    {
        "id": "S03_goddess_arrival",
        "title": "S03【凌波初现】翩若惊鸿，婉若游龙",
        "wf": WF_DUAL,
        "params": {
            "lora_name_1": "characters\\immortal_lady_v1.safetensors",
            "lora_strength_1": 0.65,
            "lora_name_2": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength_2": 0.55,
            "positive_prompt": (
                "girlslikeflux_lyf5, chinese anime, guofeng manhua illustration, semi-realistic cel shading, "
                "full-body shot of ethereal ancient Chinese goddess floating gracefully above the misty water surface of Luo river (凌波微步、吴带当风、神性初临). "
                "Wei-Jin dynasty classical beauty, high classical cloud bun hairstyle with subtle jade hairpins, "
                "wearing layered pale celadon and ivory silk Wei-Jin hanfu with wide draped sleeves, "
                "luminous translucent ribbons swirling in calligraphy curves around her, glowing water ripples beneath her feet, "
                "bioluminescent river mist, starlit night sky, cinematic rim lighting, clean lineart, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261103,
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": "lsf_s03_arrival"
        }
    },
    {
        "id": "S04_goddess_portrait",
        "title": "S04【神妃仙颜】轻云蔽月，流风回雪",
        "wf": WF_DUAL,
        "params": {
            "lora_name_1": "characters\\immortal_lady_v1.safetensors",
            "lora_strength_1": 0.65,
            "lora_name_2": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength_2": 0.55,
            "positive_prompt": (
                "girlslikeflux_lyf5, chinese anime, guofeng manhua illustration, semi-realistic cel shading, "
                "medium close-up cinematic portrait of the ethereal ancient Chinese goddess turning back with a soulful gaze (回眸凝视、目盼心思、轻云蔽月、流风回雪). "
                "Refined oval face, delicate willow-leaf eyebrows, clear soulful almond eyes with brilliant golden light catchlights, "
                "tender relaxed lips with subtle sheer peach hydration. "
                "High classical cloud bun hairstyle adorned with delicate freshwater pearls and jade hairpins, "
                "soft flyaway hair strands dancing in cold river breeze. "
                "Wearing layered pale celadon and ivory silk Wei-Jin collar with draped ribbons, "
                "glowing bioluminescent river background, moonlit water droplets, cinematic rim lighting, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261182,
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": "lsf_s04_portrait"
        }
    },
    {
        "id": "S05_parting_sorrow",
        "title": "S05【怅然归隐】恨人神之殊途，怅神光之渐隐",
        "wf": WF_SINGLE,
        "params": {
            "lora_name": "styles\\chinese_manhua_v1.safetensors",
            "lora_strength": 0.65,
            "positive_prompt": (
                "chinese anime, guofeng manhua illustration, wide atmospheric shot of the mystical Luo river under serene moonlight (恨人神之殊途、怅神光之渐隐、洛水空茫). "
                "Ethereal glowing silhouette of the goddess dissolving gently into luminous river mist and floating lotus blossoms, "
                "solitary rippling waves expanding on dark moonlit water, vast poetic negative space, "
                "melancholic tranquil mood, cool cyan and indigo color grading, Makoto Shinkai night sky with faint falling stars, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261105,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "lsf_s05_sorrow"
        }
    }
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    generated_paths = []
    
    for idx, scene in enumerate(SCENES):
        dst_path = os.path.join(OUTPUT_DIR, f"{scene['id']}.png")
        art_path = os.path.join(ARTIFACTS_DIR, f"{scene['id']}.png")

        print(f"\n=======================================================")
        print(f"[{idx+1}/5] Generating: {scene['title']}")
        print(f"=======================================================")

        # If already exists and large enough, skip
        if os.path.exists(dst_path) and os.path.getsize(dst_path) > 100000:
            print(f"Existing file found, skipping: {dst_path}")
            shutil.copyfile(dst_path, art_path)
            generated_paths.append(dst_path)
            continue

        with open(scene["wf"], "r", encoding="utf-8") as f:
            template = json.load(f)

        wf = _render(template, scene["params"])
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
                            src_path = os.path.join(str(Path(__file__).resolve().parent.parent / "runtime" / "ComfyUI" / "output"), sub, fn)
                            shutil.copyfile(src_path, dst_path)
                            shutil.copyfile(src_path, art_path)
                            elapsed = time.time() - start_time
                            print(f"[SUCCESS] {scene['id']} finished in {elapsed:.1f}s -> {dst_path}")
                            generated_paths.append(dst_path)
                break

    # Stitch 5-grid storyboard contact sheet
    if len(generated_paths) == 5:
        print("\nStitching 5-shot storyboard strip...")
        images = [Image.open(p) for p in generated_paths]
        w, h = images[0].size
        strip = Image.new("RGB", (w * 5 + 40, h), color=(18, 18, 22))
        for i, img in enumerate(images):
            strip.paste(img, (i * (w + 10), 0))
        
        strip_path = os.path.join(OUTPUT_DIR, "luoshenfu_5shot_storyboard_strip.png")
        strip_art = os.path.join(ARTIFACTS_DIR, "luoshenfu_5shot_storyboard_strip.png")
        strip.save(strip_path, quality=95)
        strip.save(strip_art, quality=95)
        print(f"[DONE] Storyboard strip saved to:\n{strip_art}")

if __name__ == "__main__":
    main()
