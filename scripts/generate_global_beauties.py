"""
Day 01 Remaster: 《全球纪实人像 · 街头初遇四重奏 (全新写实摄影与大师构图 2K版)》
(Daily Candid Realism · Issue 01: Global Street Encounters Remastered)
APPLIES THE PORTRAIT_PRODUCTION_SOP v2.0 SPECIFICATION:
1. Native Base Resolution: 768 x 1360 (High-Native Sweet Spot)
2. Realism LoRA Integration: flux_realism_xlabs.safetensors (0.35-0.40)
3. Master Photographer Framing: 35-50mm, waist-up, three-quarter angles, negative breathing space, candid street props (latte cup, espresso, tote bag, leather handbag)
4. Anti-Grimace / Anti-Bitter Expression: relaxed lips in soft calm breathing repose, clear bright eyes, 20-22yo peak youthful beauty
5. 2K Ultra-HD (1152 x 2048) gentle porcelain skin upscale + 4-Grid showcase board
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
ROOT = Path(__file__).resolve().parent.parent
WF_SINGLE_LORA = ROOT / "workflows" / "flux3_lora_t2i_api.json"
WF_DUAL_LORA = ROOT / "workflows" / "flux3_dual_lora_t2i_api.json"
WF_BASE = ROOT / "workflows" / "flux3_t2i_api.json"

OUTPUT_DIR = ROOT / "experiments" / "global_beauties"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

TARGET_W = 1152
TARGET_H = 2048

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "01_china_mainland",
        "region": "【大陆·东方温润文艺女神】",
        "location": "上海巨鹿路法租界金秋 · 21岁文艺白月光捧咖啡漫步回眸",
        "workflow": "dual_lora",
        "lora_1": "girlslikeflux_lyf5.safetensors",
        "strength_1": 0.45,
        "lora_2": "flux_realism_xlabs.safetensors",
        "strength_2": 0.35,
        "w": 768,
        "h": 1360,
        "seed": 20261101,
        "steps": 20,
        "prompt": (
            "girlslikeflux_lyf5, award-winning candid 35mm street photograph of an extraordinarily gorgeous 21-year-old Chinese woman walking down Shanghai French Concession avenue in golden autumn (东方温润白月光、金秋梧桐落叶街头、大师级环境人像漫步回眸、手捧纸杯拿铁、绝无死板大头照、真实细腻毛孔与真实皮质、松弛知性神颜). "
            "Master environmental walking composition: Walking along a sidewalk covered in golden plane tree leaves, turning back over her shoulder at a 35-degree three-quarter angle, rule of thirds placement. "
            "Holding a brown takeaway paper cup of warm oat latte with both hands naturally, showing a slender waist and graceful neck, face occupying roughly 23 percent of frame. "
            "Delicate feminine facial symmetry, smooth jawline, gentle dark almond eyes with quiet soulful warmth, naturally plump rose lips slightly parted in soft calm breathing repose, realistic fine skin pores and natural warmth. "
            "Silky dark raven hair drifting gently across her cheek in the autumn breeze, wearing an oversized cream-beige soft cashmere cardigan over a white silk camisole. "
            "Historic brick villa facades and golden autumn sunlight filtering through canopy in creamy background bokeh, Leica M11 50mm f/1.4 Summilux lens, timeless candid realism."
        )
    },
    {
        "id": "02_western_chic",
        "region": "【欧美·巴黎左岸法式慵懒】",
        "location": "圣日耳曼露天咖啡馆 · 21岁法式初熟少女手托微腮闲适浅笑",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261102,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of a gorgeous 21-year-old French woman sitting at an outdoor Parisian sidewalk bistro in Saint-Germain (法式慵懒松弛感神颜、大理石圆桌托腮抓拍、真实胶片质感、灵动灰绿大鹿眸、零僵硬假面、绝美初熟少女感). "
            "Master candid cafe framing: Leaning sideways at a 45-degree angle against a small round green marble bistro table, chin resting casually on one palm, fingers softly curled. "
            "Other hand resting on the table near a white porcelain espresso cup with saucer, face occupying 24 percent of frame with rich environmental breathing space. "
            "Sculpted delicate European bone structure, soft rounded chin, captivating large sparkling grey-green doe eyes gazing with warm relaxed curiosity, a subtle tender blooming smile with relaxed lips, smooth blemish-free porcelain skin with authentic micro-pores and zero heavy freckles. "
            "Tousled wavy honey-blonde hair catching warm afternoon rim light. "
            "Wearing an unbuttoned vintage light-blue soft denim shirt with sleeves rolled to the elbows. "
            "Woven rattan green bistro chairs and historic Haussmannian Parisian stone facade in golden afternoon sunlight, Contax T2 35mm f/2.8 lens, legendary French cinema documentary."
        )
    },
    {
        "id": "03_japan_transparency",
        "region": "【日本·镰仓海风透明少女】",
        "location": "江之电沿海防波堤单车道 · 20岁清纯初恋回眸甜笑",
        "workflow": "dual_lora",
        "lora_1": "girlslikeflux_jjy.safetensors",
        "strength_1": 0.38,
        "lora_2": "flux_realism_xlabs.safetensors",
        "strength_2": 0.35,
        "w": 768,
        "h": 1360,
        "seed": 20261103,
        "steps": 20,
        "prompt": (
            "girlslikeflux_jjy, authentic candid Japanese 35mm film photograph of an extraordinarily adorable 20-year-old Japanese young beauty walking along the coastal road in Kamakura (日系极致透明感、海风拂面回眸抓拍、单肩帆布包、灵动水汪汪大眼、治愈甜美初恋笑容、绝无死板大头照、真实清透日光皮质). "
            "Master candid walking composition: Strolling beside the green coastal road barrier overlooking the sparkling blue ocean, turning back over her shoulder at a three-quarter angle. "
            "Single cream canvas tote bag slung over one shoulder, one hand holding the tote strap, relaxed breezy posture, face occupying roughly 23 percent of frame. "
            "Dainty delicate feminine features, soft smooth jawline, large clear dark doe eyes with crystal-clear catchlights, naturally plump glossy peach lips slightly parted in soft breathing repose, pristine translucent fair skin with natural soft flush on cheeks and realistic fine skin pores. "
            "Dark silky bob hair with wispy air bangs dancing in the Pacific ocean breeze. "
            "Wearing a clean white linen short-sleeved collared shirt and high-waist navy blue pleated skirt. "
            "Sparkling azure Pacific sea waves and coastal railway crossing in warm afternoon summer sunlight, authentic Fujifilm Pro 400H colors, iconic Japanese youth film aesthetics."
        )
    },
    {
        "id": "04_korea_hannam_chic",
        "region": "【韩国·汉南洞现代都会千金】",
        "location": "现代美术馆露台花岗岩石阶 · 21岁清冷水光千金从容侧影",
        "workflow": "single_lora",
        "lora_name": "flux_realism_xlabs.safetensors",
        "strength": 0.40,
        "w": 768,
        "h": 1360,
        "seed": 20261104,
        "steps": 20,
        "prompt": (
            "High-fashion candid 35mm editorial portrait of an extraordinarily beautiful 21-year-old Korean heiress descending the granite steps of a contemporary art museum in Hannam-dong, Seoul (首尔汉南洞、顶级高智感千金、现代都会极简画报、手提极简皮包石阶从容回眸、绝无硬朗男性化、水光凝脂真实皮质、高贵清甜从容). "
            "Master architectural portrait framing: Descending minimalist grey granite museum steps, body turned at an elegant 35-degree three-quarter silhouette, rule of thirds diagonal line. "
            "Carrying a petite minimalist black leather handbag in one hand, slender waist accentuated by tailored fit, face occupying 23 percent of frame. "
            "Impeccably proportioned soft feminine oval face, full youthful cheeks without harsh angles, delicate straight nose, captivating dark almond eyes with poised intelligent warmth, naturally plump dewy petal-pink lips in soft breathing repose, luminous translucent glass skin with realistic micro-pores under soft daylight. "
            "Glossy dark espresso hair cascading smoothly down her back, wearing an oversized tailored charcoal grey wool blazer over a black silk camisole. "
            "Modern exposed concrete architecture, bamboo grove and distant city skyline in warm golden hour light, Leica M11 50mm Summilux lens, Vogue Korea luxury realism."
        )
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
                        print(f"-> Saved base: {dst_file.name} in {elapsed:.1f}s", flush=True)
                        return True
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return False

def upscale_image_to_2k_porcelain(file_path, art_file_path):
    img = Image.open(file_path).convert("RGB")
    print(f"  Upscaling {file_path.name} to 2K (1152x2048) with cinematic skin protection...", flush=True)
    up = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=3))
    enhancer = ImageEnhance.Contrast(sharpened)
    final_img = enhancer.enhance(1.02)
    final_img.save(file_path, "PNG", quality=95)
    shutil.copy(file_path, art_file_path)
    print(f"  -> 2K Upscale Complete: {file_path.name}", flush=True)

def make_4grid_board(image_paths, board_path, art_board_path):
    print("Assembling Day 01 Street Encounters (Master Realism) 4-Grid showcase board...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    
    thumb_w, thumb_h = 576, 1024
    cards_thumb = [c.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS) for c in cards]
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + thumb_w * 2
    board_h = header_h + margin + (thumb_h + card_title_h) * 2 + margin + footer_h
    
    board = Image.new("RGB", (board_w, board_h), (245, 245, 247))
    draw = ImageDraw.Draw(board)
    
    font_bold = None
    font_med = None
    font_sm = None
    for fpath in [
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyhbd.ttc"),
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf"),
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc")
    ]:
        if os.path.exists(fpath):
            try:
                font_bold = ImageFont.truetype(fpath, 42)
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
    draw.text((margin + 10, 35), "Day 01 · 全球纪实神颜四重奏 · 街头初遇 (写实大作 · 2K超清)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Daily Candid Realism · Issue 01: Global Street Encounters (Master Realism 2K Edition)", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【大陆·东方温润文艺女神】", "上海巨鹿路法租界金秋 · 21岁文艺白月光捧咖啡漫步回眸"),
        ("【欧美·巴黎左岸法式慵懒】", "圣日耳曼露天咖啡馆 · 21岁法式初熟少女手托微腮闲适浅笑"),
        ("【日本·镰仓海风透明少女】", "江之电沿海防波堤单车道 · 20岁清纯初恋回眸甜笑"),
        ("【韩国·汉南洞现代都会千金】", "现代美术馆露台花岗岩石阶 · 21岁清冷水光千金从容侧影")
    ]

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
    draw.text((margin + 10, foot_y), "Local Drama Studio | Daily Candid Realism 4-Pack Series | High-Native Realism Edition", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Day 01 (4-Photo Set · 2K Ultra-HD)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Daily Candid Realism · 全球纪实神颜日更`
- **Recommended Title (推荐标题)**: `[FLUX.3 Daily] Day 01: Global Street Encounters — Candid Realism Quartet (Full 2K Set)`
- **Alternative Title (双语备选标题)**: `【神颜日更 01】全球纪实人像 · 街头初遇四重奏 · 4大都会写实画报 · 2K超清`
- **Tags (标签)**: `FLUX, DailyCandid, Photorealism, StreetEncounters, CandidPortrait, LeicaM11, 35mmFilm, FilmGrain, Glamour, Exclusive, 4PhotoSet, 2KUltraHD`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `global_beauties_4grid.png`
2. **2K无损单图附件 (4 Standalone 2K High-Res Attachments)**:
   - `01_china_mainland.png` (【大陆·东方温润文艺女神】上海巨鹿路法租界金秋 · 21岁文艺白月光捧咖啡漫步回眸)
   - `02_western_chic.png` (【欧美·巴黎左岸法式慵懒】圣日耳曼露天咖啡馆 · 21岁法式初熟少女手托微腮闲适浅笑)
   - `03_japan_transparency.png` (【日本·镰仓海风透明少女】江之电沿海防波堤单车道 · 20岁清纯初恋回眸甜笑)
   - `04_korea_hannam_chic.png` (【韩国·汉南洞现代都会千金】现代美术馆露台花岗岩石阶 · 21岁清冷水光千金从容侧影)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Daily Candid Realism · Day 01: Global Street Encounters — Candid Realism Quartet (4 Iconic Muses)
全球纪实神颜日更 · Day 01 · 全球纪实人像 · 街头初遇四重奏 (写实大作 · 2K超清)

━━━━━━━━━━━━━━━━━━━━

Welcome to the premiere issue of Daily Candid Realism! Today, we introduce authentic 35mm documentary realism across four distinct cultural aesthetics around the world.

Rendered in high-native resolution (768×1360 native base) and real photographic optics, this collection moves far beyond static studio poses. Each shot captures natural metropolitan life through master environmental composition: dynamic walking turns, cafe table sub-framing, holding oat lattes, and natural sea-breeze movement:

• Mainland China (Shanghai French Concession): 21-year-old literary muse walking under golden plane tree canopy, holding a warm paper cup of oat latte, turning back with a serene tender smile.
• Western Europe (Parisian Sidewalk Cafe): 21-year-old French muse leaning on a round marble bistro table in Saint-Germain, chin resting casually on palm beside an espresso cup, natural sun-kissed warmth.
• Japan (Kamakura Seaside Coastal Breeze): 20-year-old pure transparency muse beside coastal railway crossing, canvas tote bag, Pacific breeze tossing soft bangs, sweet dimpled smile.
• Korea (Seoul Hannam-dong Art Gallery Steps): 21-year-old minimalist heiress descending modern granite museum steps, holding a sleek leather handbag, poised composed gaze and luminous glass skin.

All standalone downloads rendered in true 2K Ultra-HD (1152 × 2048) with high-density facial resolution and delicate porcelain skin preservation.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 4 Moments / 今日四组高光

1. 🇨🇳 Mainland China: Shanghai French Concession Autumn Walk · 梧桐暖阳
• Scene: Historic brick villas, falling golden plane tree leaves, afternoon sunbeams.
• Composition: Dynamic 3/4 walking turn, holding warm takeaway latte cup, rule of thirds.
• Details: 21-year-old literary muse, cream cashmere cardigan, white camisole, serene almond eyes.

2. 🇫🇷 Western Europe: Saint-Germain Sidewalk Cafe · 左岸慵懒
• Scene: Parisian outdoor bistro, round marble table, rattan cafe chairs, golden backlight.
• Composition: 45-degree angle lean, chin resting on palm, espresso cup on table.
• Details: 21-year-old French muse, soft light-blue denim shirt, tousled honey waves, hazel-green doe eyes.

3. 🇯🇵 Japan: Kamakura Coastal Railway Crossing · 镰仓海风
• Scene: Green coastal railing, sparkling blue Pacific ocean waves, golden afternoon light.
• Composition: Seaside walking turn, single canvas tote bag, three-quarter angle.
• Details: 20-year-old student, white linen shirt and navy pleated skirt, cute dimpled smile.

4. 🇰🇷 Korea: Hannam-dong Gallery Granite Steps · 汉南都会
• Scene: Contemporary museum exterior, minimalist granite steps, modern concrete lines.
• Composition: Descending museum steps, diagonal body posture, holding leather handbag.
• Details: 21-year-old heiress, oversized charcoal wool blazer, black silk camisole, luminous glass skin.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• High-Native Base Resolution: 全面采用 768 × 1360 原生高分基底生成（人脸潜空间像素翻倍），根除小脸碎裂与边缘伪影。
• Master Street Storytelling: 彻底告别证件照呆立构图，融入纸杯咖啡、大理石托腮、帆布包海风漫步、石阶回眸等生动街拍动作。
• Realism Optics & Micro-Texture: 引入原生写实照片 LoRA，赋予真实细腻的毛孔微结构与皮下血色透光，杜绝塑料橡皮磨皮感。
• 2K Ultra-HD Resolution: 1152 × 2048 规格无损超清输出。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Day 01 4-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 4 × Full High-Res Standalone Portraits (1152 × 2048 (2K Ultra-HD) 无损超清原图)

Which street encounter captured your heart the most? Let me know in the comments below!
"""
    patreon_file = OUTPUT_DIR / "PATREON_POST.md"
    with open(patreon_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated PATREON_POST.md at: {patreon_file}", flush=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(WF_SINGLE_LORA, "r", encoding="utf-8") as f:
        tpl_single = json.load(f)
    with open(WF_DUAL_LORA, "r", encoding="utf-8") as f:
        tpl_dual = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[Day 01 Remaster (768 High-Native Realism) - {idx}/4] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        if t["workflow"] == "dual_lora":
            params = {
                "lora_name_1": t["lora_1"],
                "lora_strength_1": t["strength_1"],
                "lora_name_2": t["lora_2"],
                "lora_strength_2": t["strength_2"],
                "positive_prompt": t["prompt"],
                "width": t["w"],
                "height": t["h"],
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_dual, params)
        else:
            params = {
                "lora_name": t["lora_name"],
                "lora_strength": t["strength"],
                "positive_prompt": t["prompt"],
                "width": t["w"],
                "height": t["h"],
                "seed": t["seed"],
                "steps": t["steps"],
                "cfg": 1.0,
                "filename_prefix": t["id"]
            }
            wf = _render(tpl_single, params)

        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"  Queued prompt_id: {pid} on Intel Arc A750...", flush=True)

        ok = wait_for_completion(pid, dst_file)
        if ok:
            upscale_image_to_2k_porcelain(dst_file, art_file)
            generated_paths.append(dst_file)
        else:
            print(f"  Failed for {t['id']}", flush=True)

    if len(generated_paths) == 4:
        board_file = OUTPUT_DIR / "global_beauties_4grid.png"
        art_board_file = ARTIFACTS_DIR / "global_beauties_4grid.png"
        make_4grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        print("\nDay 01 Street Encounters High-Native Realism Remaster completed successfully!", flush=True)

if __name__ == "__main__":
    main()
