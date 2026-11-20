"""
Rebrand and clean all supermodel series files to:
Collection: Runway Angels: Haute Couture Supermodels · 秀场天使 · 全球高定超模特辑
Series: Runway Angels · 秀场天使
Mandates:
- 100% Zero "维密", "Victoria's Secret", "Fantasy Bra"
- Update PATREON_POST.md in supermodel_vs_special01
- Update PATREON_POST.md in supermodel_vs_special02
- Re-draw 6-grid boards for Issue 01 and Issue 02 with clean brand titles and subtitles
- Update PATREON_SERIES_INDEX.md
"""
import os
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

def get_fonts():
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
    return font_bold, font_med, font_sm

def assemble_board(image_paths, board_title, board_sub, labels, output_path, art_path):
    print(f"Assembling 6-grid board: {output_path.name}...")
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
    font_bold, font_med, font_sm = get_fonts()
    
    # Header
    draw.text((margin + 10, 35), board_title, fill=(20, 20, 25), font=font_bold)
    draw.text((margin + 12, 92), board_sub, fill=(100, 105, 115), font=font_med)

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
    draw.text((margin + 10, foot_y), "Local Drama Studio | Runway Angels 6-Pack Series | Intel Arc A750 XPU Acceleration", fill=(150, 155, 165), font=font_sm)
    
    board.save(output_path, "PNG", quality=95)
    shutil.copy(output_path, art_path)
    print(f"Saved: {output_path}")

def rebrand_issue01():
    dir_01 = ROOT / "experiments" / "supermodel_vs_special01"
    if not dir_01.exists():
        return
    
    img_files = [
        dir_01 / "vs01_01_amber_bronze_goddess.png",
        dir_01 / "vs01_02_blonde_angelic_muse.png",
        dir_01 / "vs01_03_slavic_emerald_siren.png",
        dir_01 / "vs01_04_east_asian_celestial_muse.png",
        dir_01 / "vs01_05_nordic_ice_blue_goddess.png",
        dir_01 / "vs01_06_mediterranean_velvet_siren.png",
    ]
    
    labels = [
        ("【南美·琥珀古铜神颜】", "大秀后台流光通道 · 黄金微晒古铜肌 · 九头身顶级比例"),
        ("【全球·经典粉白条纹天使】", "大秀后台好莱坞化妆镜前 · 芭比精致纯情神颜 · 粉白条纹丝绸晨袍"),
        ("【东欧·高定翡翠猫眼女王】", "里维埃拉私人游艇露台 · 深邃猫系绿眼 · 墨黑真丝高开衩礼服"),
        ("【东方·发光冷白皮高定超模】", "聚光T台中心 · 通透冷白皮 · 绝美薄纱流光轻翼"),
        ("【北欧·冰蓝双眸健美天使】", "大理石海景阳光露台 · 清澈冰蓝双眸 · 健美紧致身段与缎面晨袍"),
        ("【地中海·意式复古浓颜神颜】", "托斯卡纳黄昏露台 · 意式复古黑丝绒晚裙 · 优雅从容")
    ]
    
    title = "特辑 01 · 秀场天使 · 高定后台晨袍与流光T台 (6张全集)"
    sub = "Runway Angels: Haute Couture Supermodels · Special Issue 01 · 6 Iconic Archetypes"
    board_path = dir_01 / "vs01_supermodel_showcase_6grid.png"
    art_path = ARTIFACTS_DIR / "vs01_supermodel_showcase_6grid.png"
    assemble_board(img_files, title, sub, labels, board_path, art_path)
    
    # Write clean PATREON_POST.md
    md_content = """# Patreon Publish Package · Runway Angels Special Issue 01 (6-Photo Set)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Runway Angels: Haute Couture Supermodels · 秀场天使 · 全球高定超模特辑`
- **Recommended Title (推荐标题)**: `[FLUX.3 Exclusive] Runway Angels 01: Backstage Silks & Golden Catwalk — 6 Global Supermodels (Full 4K Set)`
- **Alternative Title (双语备选标题)**: `【秀场天使 01】后台流光丝袍与黄金T台 · 全球6大高定超模神颜合集 · 4K超清原图`
- **Tags (标签)**: `FLUX, Supermodel, RunwayAngels, HighFashion, HauteCouture, Catwalk, RunwayModel, Photorealism, FilmGrain, Glamour, Exclusive, 6PhotoSet`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `vs01_supermodel_showcase_6grid.png`
2. **超清无损单图附件 (6 Standalone High-Res Attachments)**:
   - `vs01_01_amber_bronze_goddess.png` (【南美·琥珀古铜神颜】大秀后台流光通道 · 黄金微晒古铜肌 · 九头身顶级比例)
   - `vs01_02_blonde_angelic_muse.png` (【全球·经典粉白条纹天使】大秀后台好莱坞化妆镜前 · 芭比精致纯情神颜 · 粉白条纹丝绸晨袍)
   - `vs01_03_slavic_emerald_siren.png` (【东欧·高定翡翠猫眼女王】里维埃拉私人游艇露台 · 深邃猫系绿眼 · 墨黑真丝高开衩礼服)
   - `vs01_04_east_asian_celestial_muse.png` (【东方·发光冷白皮高定超模】聚光T台中心 · 通透冷白皮 · 绝美薄纱流光轻翼)
   - `vs01_05_nordic_ice_blue_goddess.png` (【北欧·冰蓝双眸健美天使】大理石海景阳光露台 · 清澈冰蓝双眸 · 健美紧致身段与缎面晨袍)
   - `vs01_06_mediterranean_velvet_siren.png` (【地中海·意式复古浓颜神颜】托斯卡纳黄昏露台 · 意式复古黑丝绒晚裙 · 优雅从容)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Runway Angels · Special Issue 01: Backstage Silks & Golden Catwalk (6 Iconic Supermodels)
秀场天使 · 特辑 01 · 后台流光丝袍与黄金T台 (6张巅峰神颜全集)

━━━━━━━━━━━━━━━━━━━━

Welcome to our brand new high-fashion exclusive column: Runway Angels!

While our Daily Series explores intimate street candids and quiet morning warmth, Runway Angels is dedicated to the absolute pinnacle of human physique, high-fashion bone structure, and golden-era runway power.

In this inaugural 6-photo grand edition, we celebrate six original, breathtaking supermodel archetypes from across the globe:
• South America: Sun-kissed amber-bronze goddess backstage with cascading caramel waves and commanding runway presence.
• Global Iconic Angel: Luminous porcelain baby-doll muse in the signature candy-pink and white striped satin dressing robe.
• Eastern Europe: Chiseled high cheekbones and hypnotic emerald-green eyes on a French Riviera twilight yacht.
• East Asia: Incandescent cool-white glowing skin and celestial flowing wings on the glittering runway catwalk.
• Northern Europe: Athletic goddess power and icy crystal-blue eyes on a sunlit marble Mediterranean terrace.
• Mediterranean: Timeless Italian vintage siren with deep velvety eyes and a classic black velvet evening gown.

Zero real celebrity imagery, zero artificial AI waxiness, zero heavy makeup mask. Pure high-fashion optical magazine realism on FLUX.3 Klein.

━━━━━━━━━━━━━━━━━━━━

📸 Today's 6 Supermodel Moments / 今日六组超模高光

1. 🇧🇷 South American Amber Bronze Goddess · 琥珀古铜神颜
• Scene: Backstage golden runway lights cutting through atmospheric haze, glowing bronze radiance.
• Optics: Hasselblad H6D-100c 100mm lens, Vogue runway editorial sharpness.
• Details: Symmetrical heart-shaped jawline, honey-bronze glowing skin, cascading caramel waves, champagne satin dressing robe, toned athletic physique.

2. 🇿🇦 Global Iconic Striped Silk Angel · 经典粉白条纹天使
• Scene: Glowing Hollywood vanity mirror backstage surrounded by warm round incandescent bulbs.
• Optics: Contax T2 35mm f/2.8, warm film highlights and backstage luxury ambiance.
• Details: Flawless porcelain baby-doll face, sparkling sapphire-blue eyes, soft honey-blonde waves, iconic candy-pink and white striped satin kimono robe, crystal perfume atomizer.

3. 🇷🇺 Eastern European Emerald Siren · 翡翠猫眼高定女王
• Scene: Teak deck of a private superyacht on the French Riviera at dusk, twilight Mediterranean sea breeze.
• Optics: Leica M11 50mm f/1.4 Summilux, high-fashion magazine perfection.
• Details: Chiseled high cheekbones, captivating piercing emerald-green eyes, tailored black liquid silk slip gown with high side slit, cold champagne glass, statuesque athletic poise.

4. 🇨🇳 East Asian Celestial Runway Muse · 发光冷白皮高定超模
• Scene: Reflective glossy catwalk floor under brilliant crystal spotlight beams, shimmering airborne glitter dust.
• Optics: Hasselblad X2D 90mm lens, razor-sharp editorial contrast.
• Details: Incandescent glowing cool-white porcelain skin, charming soft smile, sheer crystal lingerie with billowing organza wings, regal effortless catwalk stride.

5. 🇳🇱 Nordic Ice-Blue Athletic Goddess · 冰蓝双眸健美天使
• Scene: Sunlit white marble terrace overlooking turquoise Mediterranean water, bright golden afternoon sun.
• Optics: Contax T2 35mm f/2.8 lens, classic high-fashion resort glamour.
• Details: Clear porcelain skin with zero freckles, captivating icy crystal-blue eyes, thick sunlit golden waves, open ivory silk robe, sculpted collarbones and toned abdomen.

6. 🇮🇹 Mediterranean Velvet Vintage Siren · 意式复古浓颜神颜
• Scene: Antique stone terrace in Tuscany at dusk, warm flickering candlelight and soft twilight cypress hills.
• Optics: Leica M11 50mm f/1.4 Summilux, timeless European cinema aesthetic.
• Details: Deep velvety-brown expressive eyes, glossy dark brunette wavy hair, smooth porcelain-olive skin, luxurious black silk velvet slip dress, single baroque pearl pendant.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• High-Fashion Anatomy & Proportions: 精确呈现顶级超模的九头身天神身材比例、清晰锁骨与紧致腹肌线条，告别常规 AI 容易模糊变形的身体结构。
• Runway Lighting & Body Shimmer: 真实还原顶级大秀特有的人体高光修容法（Body Bronzer & Specular Highlights），在舞台射灯与自然海风中折射出健康丝缎般的肌肤光感。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Special Issue 01 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Supermodel Portraits (576 × 1024 无损超清原图，超模发丝身体高光直出)

Which supermodel archetype commands your attention the most? Let me know in the comments below!
"""
    with open(dir_01 / "PATREON_POST.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    print("Rebranded Issue 01 PATREON_POST.md successfully!")

def rebrand_issue02():
    dir_02 = ROOT / "experiments" / "supermodel_vs_special02"
    if not dir_02.exists():
        return
    
    img_files = [
        dir_02 / "vs02_01_golden_angel_runway.png",
        dir_02 / "vs02_02_crystalline_ice_angel.png",
        dir_02 / "vs02_03_ethereal_peony_wings.png",
        dir_02 / "vs02_04_classic_swan_wings.png",
        dir_02 / "vs02_05_baroque_gilded_siren.png",
        dir_02 / "vs02_06_afterparty_champagne_queen.png",
    ]
    
    # Check if all exist
    if not all(p.exists() for p in img_files):
        print("Issue 02 images not all ready yet, waiting...")
        return False
        
    labels = [
        ("【南美·鎏金羽翼天神】", "梦幻大秀T台终点定点 · 鎏金展翅九头身 · 黄金气场"),
        ("【北欧·极地冰晶天使】", "主T台流光银瀑前 · 水晶羽翼与冷艳蓝眸 · 极致雕塑感"),
        ("【东方·粉彩薄纱轻翼】", "璀璨星河T台中心 · 发光冷白皮 · 飘逸牡丹薄纱轻羽"),
        ("【欧美·经典纯白天鹅】", "传奇八英尺天鹅羽翼 · 芭比纯情神颜 · T台飞吻定点"),
        ("【地中海·西西里赤金神颜】", "罗马古柱T台秀场 · 巴洛克雕金羽翼与深酒红丝绒 · 意式浓颜"),
        ("【东欧·粉红地毯庆功女王】", "大秀庆功晚宴粉红地毯 · 露背墨绿丝缎礼服 · 翡翠猫眼名模")
    ]
    
    title = "特辑 02 · 秀场天使 · 梦幻羽翼与巅峰T台流光 (6张全集)"
    sub = "Runway Angels: Wings of Fantasy & Runway Zenith · 6 Iconic Supermodel Archetypes"
    board_path = dir_02 / "vs02_supermodel_showcase_6grid.png"
    art_path = ARTIFACTS_DIR / "vs02_supermodel_showcase_6grid.png"
    assemble_board(img_files, title, sub, labels, board_path, art_path)
    
    md_content = """# Patreon Publish Package · Runway Angels Special Issue 02 (6-Photo Set)

## 📌 基础发布信息 (Post Settings)
- **Collection (合集)**: `Runway Angels: Haute Couture Supermodels · 秀场天使 · 全球高定超模特辑`
- **Recommended Title (推荐标题)**: `[FLUX.3 Exclusive] Runway Angels 02: Wings of Fantasy & Runway Zenith — 6 Global Supermodels (Full 4K Set)`
- **Alternative Title (双语备选标题)**: `【秀场天使 02】天神降临 · 梦幻羽翼与巅峰T台流光 · 全球6大超模大秀全集 · 4K超清`
- **Tags (标签)**: `FLUX, Supermodel, RunwayAngels, AngelWings, HighFashion, HauteCouture, Catwalk, RunwayModel, Photorealism, FilmGrain, Glamour, Exclusive, 6PhotoSet`

---

## 🖼️ 附件上传清单 (File Upload Checklist)
1. **主封面图 (Cover / Gallery Image 1)**:
   - `vs02_supermodel_showcase_6grid.png`
2. **超清无损单图附件 (6 Standalone High-Res Attachments)**:
   - `vs02_01_golden_angel_runway.png` (【南美·鎏金羽翼天神】梦幻大秀T台终点定点 · 鎏金展翅九头身)
   - `vs02_02_crystalline_ice_angel.png` (【北欧·极地冰晶透明羽翼】主T台流光银瀑前 · 冰晶战袍与冷艳蓝眸)
   - `vs02_03_ethereal_peony_wings.png` (【东方·粉彩薄纱国风羽翼】璀璨星河T台 · 冷白皮仙姿与漫天花瓣)
   - `vs02_04_classic_swan_wings.png` (【欧美·经典纯白天鹅羽翼】传奇八英尺纯白天鹅巨翼 · 芭比神颜飞吻定点)
   - `vs02_05_baroque_gilded_siren.png` (【地中海·西西里巴洛克赤金神颜】大秀T台罗马柱幕前 · 深酒红丝绒与赤金羽翼)
   - `vs02_06_afterparty_champagne_queen.png` (【东欧·粉红地毯庆功宴女王】大秀庆功晚宴粉红地毯 · 露背墨绿丝缎礼服 · 翡翠猫眼名模)

---

## 📝 正文内容 (直接复制粘贴到 Patreon 编辑框)

Runway Angels · Special Issue 02: Wings of Fantasy & Runway Zenith (6 Iconic Supermodels)
秀场天使 · 特辑 02 · 梦幻羽翼与巅峰T台流光 (6张巅峰神颜全集)

━━━━━━━━━━━━━━━━━━━━

Welcome back to Runway Angels! Following our backstage debut in Issue 01, we now take center stage for the defining moment of high fashion: The Fantasy Runway and Grand Wings!

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
• Optics: Leica M11 50mm f/1.4 Summilux, timeless high-fashion runway joy.
• Details: The iconic massive 8-foot pure white feathered swan wings, sun-bleached golden blonde waves, sparkling diamond corset, playful wink and air-kiss gesture.

5. 🇮🇹 Mediterranean Baroque Gilded Siren · 西西里巴洛克赤金神颜
• Scene: Antique Roman columns and warm amber stage footlights at runway mid-point.
• Optics: Hasselblad H6D-100c 100mm lens, dramatic Italian couture power.
• Details: Porcelain-olive smooth skin, sculpted cheekbones, deep velvet-brown eyes, ornate gold-leaf sculpted wings, deep wine-red velvet and black lace bustier.

6. 🇷🇺 Eastern European Pink Carpet Queen · 粉红地毯庆功宴女王
• Scene: High-fashion Pink Carpet Afterparty in New York, flashing paparazzi camera strobes and soft pink glow.
• Optics: Leica M11 50mm f/1.4 Summilux, Met Gala luxury realism.
• Details: Razor-sharp feminine jawline, captivating emerald-green cat eyes, wet-look finger waves, backless emerald-green liquid silk gown, vintage champagne flute.

━━━━━━━━━━━━━━━━━━━━

⚙️ Technical Highlights / 制作要点

• Stage Lighting & Wing Aerodynamics: 精确模拟顶级大秀复杂的 360 度多重面光、逆光发丝光与大功率吹风机动力学，使巨型羽翼的羽毛与薄纱产生生动的飘逸气流感。
• Anatomical Precision: 严格遵循顶级超模的九头身天神骨架、清晰锁骨与紧致马甲线，面部黄金比例五官舒展自然，杜绝任何生硬变形或怪异面容。
• Engine: FLUX.3 Klein (GGUF Q4_K_M) on Intel Arc A750 Graphics.

━━━━━━━━━━━━━━━━━━━━

📥 Download Package / 赞助者下载包包含：

✓ 1 × Special Issue 02 6-Grid Master Showcase Board (带双语典藏排版与色板标定)
✓ 6 × Full High-Res Standalone Supermodel Portraits (576 × 1024 无损超清原图)

Which wing concept captured your heart the most? Let me know in the comments below!
"""
    with open(dir_02 / "PATREON_POST.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    print("Rebranded Issue 02 PATREON_POST.md successfully!")
    return True

def update_index():
    index_file = ROOT / "experiments" / "PATREON_SERIES_INDEX.md"
    if not index_file.exists():
        return
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "## 💎"
    parts = content.split(marker)
    base_part = parts[0]
    
    new_section = """## 💎 秀场天使·全球高定超模专栏 (Runway Angels Supermodel Special Series)

> **合集名称 (Patreon Collection)**: `Runway Angels: Haute Couture Supermodels · 秀场天使 · 全球高定超模特辑`  
> **专栏定位**: 聚焦全球顶级超模九头身骨相神颜、梦幻羽翼（Wings）与黄金时代秀场流光。全合规原创虚构神颜，彻底规避商标侵权风险。  
> **更新规划**: 每期输出 6 张 576×1024 独立超清原图 + 1 张 2×3 六宫格典藏母版海报。

| 特辑期数 | 主题与核心场景 | 文件夹位置 | 发帖配置文件 | 封面母版 | 单张超清附件数量 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **特辑 01** | **《秀场天使 01：后台流光丝袍与黄金T台》**<br>南美琥珀蜜糖古铜、粉白条纹纯情天使、东欧翡翠猫眼女王、东方冷白皮流光轻翼、北欧冰蓝健美天使、意式复古丝绒晚裙 | [`experiments/supermodel_vs_special01/`](experiments/supermodel_vs_special01/) | [`PATREON_POST.md`](experiments/supermodel_vs_special01/PATREON_POST.md) | [6 宫格母版大图](experiments/supermodel_vs_special01/vs01_supermodel_showcase_6grid.png) | 6 张超清原图 |
| **特辑 02** | **《秀场天使 02：梦幻羽翼与巅峰T台流光》**<br>南美鎏金展翅天神、北欧极地冰晶战袍、东方牡丹薄纱轻羽、欧美传奇纯白天鹅巨翼、西西里巴洛克雕金赤颜、东欧粉红地毯庆功女王 | [`experiments/supermodel_vs_special02/`](experiments/supermodel_vs_special02/) | [`PATREON_POST.md`](experiments/supermodel_vs_special02/PATREON_POST.md) | [6 宫格母版大图](experiments/supermodel_vs_special02/vs02_supermodel_showcase_6grid.png) | 6 张超清原图 |
"""
    final_content = base_part + new_section
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    print("Updated PATREON_SERIES_INDEX.md with Runway Angels series successfully!")

if __name__ == "__main__":
    rebrand_issue01()
    rebrand_issue02()
    update_index()
