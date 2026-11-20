"""
Generate a Professional High-End Luxury Commercial Campaign:
Theme: "Guan Shan Hai · Cold Jade" Oriental Haute Perfume (东方高定香水《观山海·冷香》商业广告全案)
Engine: Pure Native FLUX.3 Klein (Q4_K_M) - Unrivaled Physical Lighting & Material Rendering
1. Hero Master Shot: The iconic celadon bottle resting on mirror-still water
2. Macro Ingredient Shot: Aged agarwood, pine needles, crystal frost & amber resin
3. Editorial Mood Shot: Minimalist bamboo shadow, architectural space & quiet morning light
4. Sensory Dynamic Shot: High-speed liquid splash & frozen crystalline water droplets
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
WF_NATIVE = r"d:\Local-Drama-Studio\workflows\flux3_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "commercial_luxury_perfume"
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

CAMPAIGN_SHOTS = [
    {
        "id": "ad_01_hero_bottle",
        "title": "Ad 01【旗舰产品主视觉 · 静水流深】",
        "seed": 20263301,
        "prompt": (
            "breathtaking award-winning luxury commercial studio product photograph of an ultra-luxury minimalist oriental perfume bottle (东方高定奢华香水旗舰大片、极简天圆地方美学). "
            "A geometric heavyweight frosted celadon-cyan glass bottle with subtle jade green tint, crowned with a cylindrical brushed matte titanium metal cap. "
            "The bottle stands solitary on a pristine mirror-like shallow black water surface with delicate micro-ripples and perfect glassy reflection. "
            "Crisp crystal-clear condensation water droplets beaded on the glass surface. One controlled razor-sharp linear specular highlight carving the edge of the bottle. "
            "Soft wisp of ethereal incense smoke drifting in the background. Minimalist deep charcoal and ink-grey studio backdrop, generous blank copy zone in upper third for luxury brand typography, "
            "shot on Hasselblad H6D-100c, 100mm f/2.8 Macro lens, masterwork commercial advertising campaign, 8k resolution, zero plastic look, unmatched optical fidelity"
        )
    },
    {
        "id": "ad_02_macro_ingredients",
        "title": "Ad 02【微距核心香材 · 寒木生香】",
        "seed": 20263302,
        "prompt": (
            "extreme macro commercial ingredient photography for luxury haute perfumery (高定香氛天然原材微距大片). "
            "In extreme close-up, a piece of dark textured aged agarwood (沉香木) alongside fragrant mountain pine needles and delicate white wild winter plum blossom. "
            "A drop of glowing golden amber resin oozing naturally from the wood fiber, with melting frosty morning dew drops glistening like diamonds on the pine needles. "
            "One water droplet magnifies the wood grain underneath with microscopic precision. Ultra-shallow depth of field, creamy smooth out-of-focus background with soft warm bokeh. "
            "Natural raking side light sculpting organic tactile textures, professional studio food and botanical commercial shoot, masterclass lighting, 8k"
        )
    },
    {
        "id": "ad_03_editorial_bamboo_shadow",
        "title": "Ad 03【空间意境大片 · 竹影空山】",
        "seed": 20263303,
        "prompt": (
            "high-end contemporary architectural editorial commercial photograph for luxury lifestyle perfume (当代东方极简空间与光影大片). "
            "Inside a tranquil modern brutalist concrete and warm cedarwood tea salon. Soft early morning golden sunlight streams through a fine woven bamboo screen, "
            "casting rhythmic linear shadows across a textured raw basalt stone pedestal. The frosted celadon perfume bottle rests quietly in the geometric light beam, "
            "casting a long, poetic translucent cyan shadow. A single minimalist bronze vase holding a slender bare winter branch in the background. "
            "Generous negative space, harmonious wabi-sabi aesthetics, architectural magazine cover style, Leica SL2, 35mm f/2 Summicron, understated quiet luxury"
        )
    },
    {
        "id": "ad_04_fluid_splash",
        "title": "Ad 04【极速凝固动势 · 冰泉破浪】",
        "seed": 20263304,
        "prompt": (
            "breathtaking 1/8000s high-speed motion-freeze commercial beverage and perfume advertisement (极速动态定格水花大片、冰泉破空). "
            "The luxury frosted celadon perfume bottle is captured mid-air, surrounded by an explosive, sculptural wave of crystal-clear mineral water splashing dramatically around it. "
            "Air bubbles and suspended micro water droplets frozen in mid-flight with pristine optical transparency. Dramatic directional rim lighting catching every water droplet like floating crystals. "
            "Cool azure blue and pristine white gradient background, fresh invigorating kinetic energy, perfect commercial beverage and cosmetic splash photography, Profoto studio strobe, 8k masterpiece"
        )
    }
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_NATIVE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated = []

    for idx, shot in enumerate(CAMPAIGN_SHOTS):
        dst_path = OUTPUT_DIR / f"{shot['id']}.png"
        art_path = ARTIFACTS_DIR / f"{shot['id']}.png"

        print(f"\n=======================================================")
        print(f"[{idx+1}/4] Rendering Campaign: {shot['title']}")
        print(f"=======================================================")

        params = {
            "positive_prompt": shot["prompt"],
            "width": 576,
            "height": 1024,
            "seed": shot["seed"],
            "steps": 20,
            "cfg": 1.0,
            "filename_prefix": f"ad_{shot['id']}"
        }

        wf = _render(template, params)
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
                            print(f"[SUCCESS] {shot['id']} finished in {elapsed:.1f}s -> {dst_path}")
                            generated.append(dst_path)
                break

    # Stitch 4-Shot Campaign Presentation Board
    if len(generated) == 4:
        print("\nStitching 4-Shot Commercial Campaign Master Board...")
        images = [Image.open(p) for p in generated]
        w, h = images[0].size
        board = Image.new("RGB", (w * 4 + 30, h), color=(15, 15, 18))
        for i, img in enumerate(images):
            board.paste(img, (i * (w + 10), 0))

        board_path = OUTPUT_DIR / "luxury_perfume_campaign_board.png"
        board_art = ARTIFACTS_DIR / "luxury_perfume_campaign_board.png"
        board.save(board_path, quality=95)
        board.save(board_art, quality=95)
        print(f"[ALL DONE] Commercial Campaign Master Board saved to:\n{board_art}")

if __name__ == "__main__":
    main()
