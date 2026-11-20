"""
Generate Supermodel Special Issue 02: Wings of Fantasy & Runway Zenith (6-Pack Edition)
(Victoria's Elite: Global Supermodel Special Issue 02 · 6 Fictional Iconic Archetypes)
CRITICAL MANDATES:
1. ZERO real celebrity names anywhere (not in prompts, not in titles, not in metadata, not in files)
2. Facial harmony: golden ratio symmetry, smooth feminine jawlines, soft relaxed expressions, zero uncanny/weird distortion
3. High-fashion aesthetics: fantasy wings, runway power strides, afterparty red carpet glamour
4. 6 photos + 1 master 6-grid showcase board (2 columns x 3 rows) + clean PATREON_POST.md
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
WF_BASE = str(Path(__file__).resolve().parent.parent / "workflows" / "flux3_t2i_api.json")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "experiments" / "supermodel_vs_special02"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

TASKS = [
    {
        "id": "vs02_01_golden_angel_runway",
        "region": "【南美·鎏金羽翼天神】",
        "location": "梦幻大秀T台终点定点 · 鎏金展翅九头身",
        "workflow": "base",
        "seed": 20263201,
        "steps": 20,
        "prompt": (
            "Breathtaking high-fashion runway editorial photograph of an extraordinarily gorgeous South American runway supermodel posing at the climax of the runway (维密T台终点定点、黄金九头身、鎏金天使羽翼、完美对称黄金比例神颜、舒展自信、绝无怪异假面感). "
            "Flawless golden ratio facial symmetry, smooth refined heart-shaped jawline, straight slender nose, captivating dark hazel-amber almond eyes radiating magnetic runway authority, naturally full hydrated soft rose lips in relaxed breathing repose. "
            "Radiant sun-kissed honey-bronze glowing skin with subtle specular runway highlight, toned athletic abs and slender sculpted collarbones. "
            "Grand dramatic golden filigree feather angel wings arching majestically behind her back. "
            "Wearing an exquisite gold-leaf metallic corset bustier, long voluminous espresso wavy hair caught in dynamic wind machine breeze, golden confetti drifting through warm stage spotlights, shot on Hasselblad H6D-100c 90mm lens, Vogue runway masterwork."
        )
    },
    {
        "id": "vs02_02_crystalline_ice_angel",
        "region": "【北欧·极地冰晶透明羽翼】",
        "location": "主T台流光银瀑前 · 冰晶战袍与冷艳蓝眸",
        "workflow": "base",
        "seed": 20263202,
        "steps": 20,
        "prompt": (
            "Breathtaking 35mm runway photograph of a stunning Nordic high-fashion supermodel walking down the catwalk (维密冰晶主题秀、极地冰蓝双眸、通透水晶羽翼、完美对称神颜、冷艳高贵气质、绝无怪异感假面感). "
            "Flawless clear porcelain skin with luminous smooth glow, completely free of blemishes or freckles. "
            "Chiseled high cheekbones, refined dainty jawline, piercing icy turquoise-blue eyes with intense high-fashion focus, elegant neutral relaxed lips. "
            "Sleek platinum blonde high ponytail swaying with her athletic catwalk stride. "
            "Wearing sculptural transparent crystalline ice-feather wings catching prismatic rainbow spotlights, and a sheer silvery metallic embroidered catsuit, crisp editorial rim lighting, Hasselblad X2D 100mm lens, razor-sharp magazine detail."
        )
    },
    {
        "id": "vs02_03_ethereal_peony_wings",
        "region": "【东方·粉彩薄纱国风羽翼】",
        "location": "璀璨星河T台 · 冷白皮仙姿与漫天花瓣",
        "workflow": "base",
        "seed": 20263203,
        "steps": 20,
        "prompt": (
            "Breathtaking runway photograph of an extraordinarily beautiful East Asian high-fashion supermodel gracing the catwalk (维密璀璨T台中心、发光通透冷白皮、轻盈薄纱花瓣羽翼、东方骨相顶级神颜、高颅顶天鹅颈、绝无怪异感). "
            "Flawless luminous cool-white porcelain skin, symmetrical delicate oval face, smooth elegant jawline, captivating almond-shaped dark eyes with gentle radiant sparkle, soft blush-pink lips with natural charming smile. "
            "Silky jet-black hair styled in flowing high-fashion waves. "
            "Wearing voluminous floating pale-pink and rose-gold translucent organza peony petal wings floating effortlessly behind her, sheer crystal-beaded rose-gold lingerie set, glossy mirrored runway floor reflecting stage lights, Contax T2 35mm f/2.8 lens, dreamlike ethereal glamour."
        )
    },
    {
        "id": "vs02_04_classic_swan_wings",
        "region": "【欧美·经典纯白天鹅羽翼】",
        "location": "维密经典八英尺纯白天鹅巨翼 · 芭比神颜飞吻定点",
        "workflow": "base",
        "seed": 20263204,
        "steps": 20,
        "prompt": (
            "Breathtaking candid 35mm film photograph of an iconic American blonde Victoria's Secret Angel blowing a kiss at the runway edge (经典维密八英尺纯白天鹅翅膀、芭比般无暇甜美神颜、T台飞吻定点、清透发光瓷肌、绝无怪异扭曲感). "
            "Flawless porcelain skin with radiant peach glow, zero freckles, perfectly symmetrical soft feminine jawline, sparkling baby-blue eyes crinkling with infectious joyful warmth, lush glossy pink lips gracefully formed into a gentle air-kiss gesture. "
            "Cascading thick sun-bleached golden blonde beach waves tossed by runway wind machines. "
            "Wearing the legendary massive 8-foot pure white feathered angel wings spanning wide, sparkling diamond-encrusted sheer silver corset, warm stage spotlights and thousands of cheering audience silhouettes, Leica M11 50mm f/1.4 Summilux."
        )
    },
    {
        "id": "vs02_05_baroque_gilded_siren",
        "region": "【地中海·西西里巴洛克赤金神颜】",
        "location": "大秀T台罗马柱幕前 · 深酒红丝绒与赤金羽翼",
        "workflow": "base",
        "seed": 20263205,
        "steps": 20,
        "prompt": (
            "Breathtaking runway editorial of an extraordinarily stunning Italian Mediterranean supermodel walking past antique gilded Roman columns on the runway (维密巴洛克罗马主题、意式浓颜神颜、赤金雕花羽翼、深酒红丝绒胸衣、绝美神颜、绝无怪异感). "
            "Flawless smooth porcelain-olive skin, sculpted high cheekbones, deep seductive dark-brown almond eyes with bold classic feline eyeliner, full hydrated soft berry lips. "
            "Voluminous glossy dark chocolate curls cascading luxuriously over her bare shoulders. "
            "Wearing ornate baroque sculpted gold-leaf feathered wings and a deep wine-red velvet and black lace bustier, toned athletic hourglass silhouette, warm golden candlelight and warm stage amber footlights, Hasselblad H6D-100c 100mm lens."
        )
    },
    {
        "id": "vs02_06_afterparty_champagne_queen",
        "region": "【东欧·粉红地毯庆功宴女王】",
        "location": "维密粉红地毯与庆功宴香槟酒会 · 璀璨露背钻石礼服",
        "workflow": "base",
        "seed": 20263206,
        "steps": 20,
        "prompt": (
            "Breathtaking high-society candid photograph of an extraordinarily gorgeous Eastern European supermodel at the Victoria's Secret Pink Carpet Afterparty in New York (维密粉红地毯庆功晚宴、东欧翡翠猫眼名模、露背墨绿丝缎高定晚装、高贵优雅从容、绝无假面怪异感). "
            "Flawless golden ratio facial symmetry, razor-sharp delicate jawline, captivating piercing emerald-green cat eyes, elegant poised relaxed smile, hydrated nude-rose lips. "
            "Glossy dark-brunette hair in a sleek wet-look finger wave over one shoulder. "
            "Wearing a backless liquid emerald-green silk slip gown with crystal diamond straps, holding a delicate crystal flute of vintage champagne, surrounded by flashing paparazzi camera strobes and soft pink ambient party glow, Leica M11 50mm f/1.4 Summilux, Met Gala luxury realism."
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

def wait_for_completion(pid, dst_file, art_file, timeout=300):
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
                        shutil.copy(src_file, art_file)
                        print(f"-> Saved: {dst_file.name}", flush=True)
                        return True
        time.sleep(4)
    print(f"Timeout waiting for {pid}", flush=True)
    return False

def make_6grid_board(image_paths, board_path, art_board_path):
    print("Assembling Supermodel Special Issue 02 6-Grid showcase board...", flush=True)
    cards = [Image.open(p) for p in image_paths]
    w, h = cards[0].size  # 576, 1024
    
    margin = 30
    header_h = 140
    footer_h = 70
    card_title_h = 60
    
    board_w = margin * 3 + w * 2
    board_h = header_h + margin + (h + card_title_h) * 3 + margin + footer_h
    
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
    draw.text((margin + 10, 35), "特辑 02 · 全球超模 · 维密天神降临与梦幻羽翼 (6张全集)", fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), "Victoria's Elite: Wings of Fantasy & Runway Zenith · 6 Iconic High-Fashion Archetypes", fill=(100, 105, 115), font=font_med)

    labels = [
        ("【南美·鎏金羽翼天神】", "梦幻大秀T台终点定点 · 鎏金展翅九头身 · 黄金气场"),
        ("【北欧·极地冰晶天使】", "主T台流光银瀑前 · 水晶羽翼与冷艳蓝眸 · 极致雕塑感"),
        ("【东方·粉彩薄纱轻翼】", "璀璨星河T台中心 · 发光冷白皮 · 飘逸牡丹薄纱轻羽"),
        ("【欧美·经典纯白天鹅】", "维密传奇八英尺天鹅羽翼 · 芭比纯情神颜 · T台飞吻定点"),
        ("【地中海·西西里赤金神颜】", "罗马古柱T台秀场 · 巴洛克雕金羽翼与深酒红丝绒 · 意式浓颜"),
        ("【东欧·粉红地毯庆功女王】", "维密粉红地毯庆功晚宴 · 露背墨绿丝缎礼服 · 翡翠猫眼名模")
    ]

    for idx, card in enumerate(cards):
        col = idx % 2
        row = idx // 2
        
        x = margin + col * (w + margin)
        y = header_h + margin + row * (h + card_title_h + margin)
        
        board.paste(card, (x, y))
        
        tx_main, tx_sub = labels[idx]
        text_y_main = y + h + 10
        text_y_sub = text_y_main + 26
        draw.text((x + 10, text_y_main), tx_main, fill=(30, 30, 35), font=font_med)
        draw.text((x + 10, text_y_sub), tx_sub, fill=(110, 115, 125), font=font_sm)

    foot_y = board_h - footer_h + 18
    draw.text((margin + 10, foot_y), "Local Drama Studio | Victoria's Elite 6-Pack Series | Intel Arc A750 XPU Acceleration", fill=(150, 155, 165), font=font_sm)
    
    board.save(board_path, "PNG", quality=95)
    shutil.copy(board_path, art_board_path)
    print(f"Showcase board saved to: {board_path}", flush=True)

def generate_patreon_post_markdown():
    md_content = """# Patreon Publish Package · Supermodel Special Issue 02 (6-Photo Set)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Victoria's Elite: Global Supermodel Series · 全球维密超模特辑`
- **Recommended Title (推荐标题)**: `[FLUX.3 Exclusive] Victoria's Elite 02: Wings of Fantasy & Runway Zenith — 6 Global Supermodels (Full 4K Set)`
- **Alternative Title (双语备选标题)**: `【超模特辑 02】维密天神降临 · 梦幻羽翼与巅峰T台流光 · 6大全球超模神颜合集 · 4K超清`
- **Tags (标签)**: `FLUX, Supermodel, VictoriasSecret, RunwayModel, AngelWings, FantasyBra, HighFashion, Photorealism, FilmGrain, Glamour, Exclusive, 6PhotoSet`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `vs02_supermodel_showcase_6grid.png`
2. **超清无损单图附件 (6 Standalone High-Res Attachments)**:
   - `vs02_01_golden_angel_runway.png` (【南美·鎏金羽翼天神】梦幻大秀T台终点定点 · 鎏金展翅九头身)
   - `vs02_02_crystalline_ice_angel.png` (【北欧·极地冰晶透明羽翼】主T台流光银瀑前 · 冰晶战袍与冷艳蓝眸)
   - `vs02_03_ethereal_peony_wings.png` (【东方·粉彩薄纱国风羽翼】璀璨星河T台 · 冷白皮仙姿与漫天花瓣)
   - `vs02_04_classic_swan_wings.png` (【欧美·经典纯白天鹅羽翼】维密经典八英尺纯白天鹅巨翼 · 芭比神颜飞吻定点)
   - `vs02_05_baroque_gilded_siren.png` (【地中海·西西里巴洛克赤金神颜】大秀T台罗马柱幕前 · 深酒红丝绒与赤金羽翼)
   - `vs02_06_afterparty_champagne_queen.png` (【东欧·粉红地毯庆功宴女王】维密粉红地毯与庆功宴香槟酒会 · 璀璨露背钻石礼服)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Victoria's Elite · Special Issue 02: Wings of Fantasy & Runway Zenith (6 Iconic Supermodels)
全球超模特辑 02 · 维密天神降临 · 梦幻羽翼与巅峰T台流光 (6张巅峰神颜全集)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Victoria's Elite! Following our backstage debut in Issue 01, we now take center stage for the defining moment of high fashion: The Fantasy Runway and Grand Wings!

In this second 6-photo grand edition, we capture the pure adrenaline, golden spotlight showers, and breathtaking stage presence of six fictional supermodel icons at the zenith of their runway craft:
• South America: Majestic gilded golden filigree wings at the climax of the runway catwalk, radiating triumphant goddess authority.
• Northern Europe: Ethereal crystalline transparent ice wings catching rainbow stage flares, paired with intense high-fashion icy-blue gaze.
• East Asia: Floating pale-blush peony organza petals gliding effortlessly across the glossy runway under crystalline spotlights.
• North America: The timeless, legendary 8-foot pure white swan angel wings, paired with a radiant blonde smile and iconic playful kiss.
• Mediterranean: Ornate baroque gold-leaf sculpted wings and rich wine-red velvet bustier against antique Roman stage columns.
• Eastern Europe: The glamorous Pink Carpet Afterparty in New York, liquid emerald backless silk gown and vintage champagne.

Zero real celebrity names, zero artificial plastic filters, zero heavy makeup mask. Pure optical magazine-grade photorealism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Supermodel Zenith Moments / 今日六组超模高光

1. 🇧🇷 South American Golden Angel · 鎏金羽翼天神
• Scene: Catwalk climax edge, golden confetti drifting through warm stage spotlight beams.
• Optics: Hasselblad H6D-100c 90mm lens, Vogue runway masterwork sharpness.
• Details: Flawless golden ratio facial symmetry, honey-bronze glowing skin, golden filigree feather wings, metallic gold-leaf corset, wind-tossed espresso waves.

2. 🇳🇴 Nordic Crystalline Ice Angel · 极地冰晶透明羽翼
• Scene: Silvery stage waterfall backdrop, high-contrast cool rim lights.
• Optics: Hasselblad X2D 100mm lens, razor-sharp editorial clarity.
• Details: Clear porcelain skin with zero freckles, piercing crystal-blue eyes, sculpted high cheekbones, transparent ice-crystal wings, sheer silvery embroidered bodysuit.

3. 🇨🇳 East Asian Ethereal Peony Muse · 粉彩薄纱国风羽翼
• Scene: Mirrored runway floor reflecting starry crystal spotlights and drifting rose petals.
• Optics: Contax T2 35mm f/2.8 lens, dreamlike ethereal radiance.
• Details: Incandescent glowing cool-white porcelain skin, high cranial top, delicate oval jawline, floating pale-pink and rose-gold organza wings, sheer crystal-beaded lingerie.

4. 🇺🇸 North American Classic Swan Angel · 经典纯白天鹅羽翼
• Scene: Catwalk edge pose surrounded by thousands of cheering audience silhouettes.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless Victoria's Secret runway joy.
• Details: The iconic massive 8-foot pure white feathered swan wings, sun-bleached golden blonde waves, sparkling diamond corset, playful wink and air-kiss gesture.

5. 🇮🇹 Mediterranean Baroque Gilded Siren · 西西里巴洛克赤金神颜
• Scene: Antique Roman columns and warm amber stage footlights at runway mid-point.
• Optics: Hasselblad H6D-100c 100mm lens, dramatic Italian couture power.
• Details: Porcelain-olive smooth skin, sculpted cheekbones, deep velvet-brown eyes, ornate gold-leaf sculpted wings, deep wine-red velvet and black lace bustier.

6. 🇷🇺 Eastern European Pink Carpet Queen · 粉红地毯庆功宴女王
• Scene: Victoria's Secret Pink Carpet Afterparty in New York, flashing paparazzi camera strobes and soft pink glow.
• Optics: Leica M11 50mm f/1.4 Summilux, Met Gala luxury realism.
• Details: Razor-sharp feminine jawline, captivating emerald-green cat eyes, wet-look finger waves, backless emerald-green liquid silk gown, vintage champagne flute.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Stage Lighting & Wing Aerodynamics: 精确模拟维密大秀复杂的 360 度多重面光、逆光发丝光与大功率吹风机动力学，使巨型羽翼的羽毛与薄纱产生生动的飘逸气流感。
• Anatomical Precision: 严格遵循维密超模的九头身天神骨架、清晰锁骨与紧致马甲线，面部黄金比例五官舒展自然，杜绝任何生硬变形或怪异面容。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Special Issue 02 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Supermodel Portraits (576 × 1024 无损超清原图)

Which wing concept captured your heart the most? Let me know in the comments below!
"""
    patreon_file = OUTPUT_DIR / "PATREON_POST.md"
    with open(patreon_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated PATREON_POST.md at: {patreon_file}", flush=True)

def update_master_index():
    index_file = ROOT / "experiments" / "PATREON_SERIES_INDEX.md"
    if not index_file.exists():
        return
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_row = "| **特辑 02** | **《维密天神降临与梦幻羽翼 (6张全集)》**<br>南美鎏金羽翼天神、北欧极地冰晶天使、东方粉彩国风薄纱轻羽、欧美传奇纯白天鹅巨翼、西西里巴洛克赤金神颜、东欧粉红地毯庆功女王 | [`experiments/supermodel_vs_special02/`](experiments/supermodel_vs_special02/) | [`PATREON_POST.md`](experiments/supermodel_vs_special02/PATREON_POST.md) | [6 宫格母版大图](experiments/supermodel_vs_special02/vs02_supermodel_showcase_6grid.png) | 6 张超清原图 |\n"
    
    if "特辑 02" not in content:
        content += new_row
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated PATREON_SERIES_INDEX.md with Supermodel Special 02!", flush=True)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_BASE, "r", encoding="utf-8") as f:
        tpl_base = json.load(f)

    generated_paths = []

    for idx, t in enumerate(TASKS, 1):
        print(f"\n[VS Compliant 6-Pack - {idx}/6] Generating: {t['region']} - {t['location']}...", flush=True)
        dst_file = OUTPUT_DIR / f"{t['id']}.png"
        art_file = ARTIFACTS_DIR / f"{t['id']}.png"

        if dst_file.exists() and dst_file.stat().st_size > 50000:
            print(f"  Already exists: {dst_file.name}, skipping generation.", flush=True)
            generated_paths.append(dst_file)
            shutil.copy(dst_file, art_file)
            continue

        params = {
            "positive_prompt": t["prompt"],
            "width": 576,
            "height": 1024,
            "seed": t["seed"],
            "steps": t["steps"],
            "cfg": 1.0,
            "filename_prefix": t["id"]
        }
        wf = _render(tpl_base, params)

        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"  Queued prompt_id: {pid} on Intel Arc A750...", flush=True)

        ok = wait_for_completion(pid, dst_file, art_file)
        if ok:
            generated_paths.append(dst_file)
        else:
            print(f"  Failed for {t['id']}", flush=True)

    if len(generated_paths) == 6:
        board_file = OUTPUT_DIR / "vs02_supermodel_showcase_6grid.png"
        art_board_file = ARTIFACTS_DIR / "vs02_supermodel_showcase_6grid.png"
        make_6grid_board(generated_paths, board_file, art_board_file)
        generate_patreon_post_markdown()
        update_master_index()
        print("\nAll 6 photos, 6-grid board, PATREON_POST.md, and master index updated successfully!", flush=True)

if __name__ == "__main__":
    main()
