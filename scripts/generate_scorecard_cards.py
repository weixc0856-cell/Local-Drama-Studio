import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WINDIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
FONT_ZH_BOLD = str(WINDIR / "msyhbd.ttc")
FONT_ZH_REG = str(WINDIR / "msyh.ttc")
FONT_EN_BOLD = str(WINDIR / "arialbd.ttf")
FONT_EN_REG = str(WINDIR / "arial.ttf")

OUT_DIR = Path(os.environ.get("DRAMA_OUTPUT_ROOT", "./studio_data")) / "outputs" / "benchmark_summary_cards"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def draw_rounded_rect(draw, bbox, radius, fill, outline=None, width=1):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)

def generate_chinese_card():
    W, H = 1200, 2200
    img = Image.new("RGB", (W, H), "#0B0F19")
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_ZH_BOLD, 46)
    f_sub = ImageFont.truetype(FONT_ZH_REG, 24)
    f_sec = ImageFont.truetype(FONT_ZH_BOLD, 30)
    f_body_b = ImageFont.truetype(FONT_ZH_BOLD, 22)
    f_body = ImageFont.truetype(FONT_ZH_REG, 20)
    f_small = ImageFont.truetype(FONT_ZH_REG, 17)

    # Top Header Accent bar
    draw.rectangle([0, 0, W, 10], fill="#3B82F6")

    # Header Card
    draw_rounded_rect(draw, (40, 35, W - 40, 235), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((70, 55), "开源生图双引擎深度评测 · 权威成绩单", font=f_title, fill="#FFFFFF")
    draw.text((70, 118), "Z-Image Turbo 6B (裸跑零LoRA)  VS  FLUX.3 Klein 4B (蒸馏+扩写)", font=ImageFont.truetype(FONT_ZH_BOLD, 26), fill="#60A5FA")
    draw.text((70, 158), "硬件环境：Intel Arc A750 8GB VRAM | 64GB DDR5 | 8大客观维度 | 12题标准测试集盲测", font=f_sub, fill="#94A3B8")

    # Badges
    badges = ["拒绝看图说话", "四层受控实验", "杜绝归因谬误", "100%可复现"]
    bx = 70
    for b in badges:
        draw_rounded_rect(draw, (bx, 195, bx + 150, 225), radius=6, fill="#1E293B")
        draw.text((bx + 15, 200), b, font=f_small, fill="#38BDF8")
        bx += 165

    # Section 1: Methodology
    y = 260
    draw_rounded_rect(draw, (40, y, W - 40, y + 250), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((70, y + 20), "一、评测方法论：拆开4组受控配置（避免归因混乱）", font=f_sec, fill="#38BDF8")
    draw.text((70, y + 65), "很多评测把『FLUX双LoRA』对比『Z-Image裸跑』归因给基模，属于严重方法论错误。本次严格拆解：", font=f_body, fill="#CBD5E1")
    
    rows = [
        ("A 组：Z-Image Turbo 裸跑", "6B 原生 Q4_K_M，8步收敛，零 LoRA，考核阿里底座原生真实感能力"),
        ("B 组：FLUX.3 Klein 裸跑", "4B 原生 Q4_K_M，4步极速，必须开启 Prompt Upsampler 提示词扩写"),
        ("C 组：FLUX.3 Klein + 单LoRA", "挂载写实/胶片单 LoRA，精确评估单一微调带来的增益与代价"),
        ("D 组：FLUX.3 Klein + 双LoRA", "写实0.6 + 胶片0.5 叠加，实测多 LoRA 是否过拟合或导致显存溢出"),
    ]
    ry = y + 105
    for tag, desc in rows:
        draw.text((75, ry), f"• {tag}:", font=f_body_b, fill="#F8FAFC")
        draw.text((410, ry + 2), desc, font=f_small, fill="#94A3B8")
        ry += 32

    # Section 2: Scorecard Table
    y = 535
    draw_rounded_rect(draw, (40, y, W - 40, y + 710), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((70, y + 20), "二、三张权威量化成绩单（八大维度实测评分）", font=f_sec, fill="#38BDF8")

    # Table Header
    ty = y + 70
    draw_rounded_rect(draw, (65, ty, W - 65, ty + 42), radius=8, fill="#1E293B")
    draw.text((85, ty + 10), "评测维度与场景", font=f_body_b, fill="#F1F5F9")
    draw.text((440, ty + 10), "Z-Image Turbo (裸跑)", font=f_body_b, fill="#60A5FA")
    draw.text((740, ty + 10), "FLUX.3 Klein (底模+扩写)", font=f_body_b, fill="#A78BFA")
    draw.text((1010, ty + 10), "胜出归属", font=f_body_b, fill="#34D399")

    table_data = [
        ("1. 东方写实人像与原生毛孔", "4.9 分 (微血管透光/天然)", "3.8 分 (原生偏欧美脸)", "🏆 Z-Image 完胜"),
        ("2. 眼神光与微表情自然度", "4.8 分 (生动温润抿嘴笑)", "3.9 分 (神态略呆滞硬朗)", "🏆 Z-Image 胜出"),
        ("3. 工业机械与零件装配真实度", "3.7 分 (偶有非物理零件)", "4.8 分 (碳陶刹车螺栓严密)", "🏆 FLUX.3 完胜"),
        ("4. 英文文字生成与排版无错字", "2.8 分 (小字乱码/形变)", "4.9 分 (5大零件单词零拼错)", "🏆 FLUX.3 统治级"),
        ("5. 空间留白与负片区域控制", "3.9 分 (易被多余元素填满)", "4.7 分 (40%纯净留白放字幕)", "🏆 FLUX.3 胜出"),
        ("6. 科学物理流体(CFD/风洞)", "3.5 分 (更偏艺术化流线)", "4.6 分 (严格符合流体力学)", "🏆 FLUX.3 胜出"),
        ("7. 角色跨场景一致性(Lin)", "4.6 分 (稳定复现泪痣/骨相)", "4.5 分 (结合特征词打平)", "🤝 双引擎打平"),
        ("8. 推理步数与单张耗时", "8步 · 7.8秒", "4步 · 6.2秒 (蒸馏优势)", "🏆 FLUX.3 略快"),
        ("9. 峰值显存占用 (8GB实测)", "4.2 GB (安全稳定)", "4.0 GB (安全稳定)", "🤝 均极度轻量"),
        ("10. 工作流维护成本/过拟合", "极低 (零LoRA直出大片)", "中等 (需维护LoRA与提示词)", "🏆 Z-Image 极简"),
    ]

    row_y = ty + 50
    for i, (dim, z_score, f_score, winner) in enumerate(table_data):
        bg = "#182238" if i % 2 == 1 else "#131B2E"
        draw_rounded_rect(draw, (65, row_y, W - 65, row_y + 52), radius=4, fill=bg)
        draw.text((85, row_y + 14), dim, font=f_body, fill="#E2E8F0")
        
        # Color scores
        draw.text((440, row_y + 14), z_score, font=f_body, fill="#93C5FD")
        draw.text((740, row_y + 14), f_score, font=f_body, fill="#C4B5FD")
        
        w_color = "#34D399" if "Z-Image" in winner else ("#A78BFA" if "FLUX" in winner else "#FBBF24")
        draw.text((1010, row_y + 14), winner, font=f_body_b, fill=w_color)
        row_y += 56

    # Section 3: Core Conclusions
    y = 1270
    draw_rounded_rect(draw, (40, y, W - 40, y + 420), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((70, y + 20), "三、核心测评结论：谁更强？没有绝对冠军，只有场景最优！", font=f_sec, fill="#38BDF8")

    conc_blocks = [
        ("👑 东方人像与电影感光影之王：Z-Image Turbo 6B", 
         "在不挂载任何 LoRA 的裸跑状态下，Z-Image 凭借深厚的中文东方美学预训练，直出具备微血管通透感的真实皮肤毛孔与自然骨相，彻底终结了开源领域的『AI假人脸』与『蛇精脸』。适合人像写真、国风短剧、日系街拍。"),
        
        ("👑 机械工业、流体力学与排版之王：FLUX.3 Klein 4B", 
         "在开启官方 Prompt Upsampler 扩写后，FLUX.3 对几何空间透视、跑车打孔刹车盘结构装配、风洞层流分离展现出统治级物理严谨度；在 5 个航天英文零件标签测试中实现 100% 零错字，左侧 40% 纯净留白更是课件与字幕排版神器。"),

        ("⚡ 8GB 显存普及化奇迹：两者均彻底打破算力门槛", 
         "得益于 Q4_K_M GGUF 量化与蒸馏技术，Z-Image (8步) 与 FLUX.3 (4步) 显存占用均仅为 4GB 左右，RTX 3060 / Intel Arc A750 甚至集显轻薄本均可在 7 秒内完成单张 2K 高清交付。"),
    ]

    cy = y + 70
    for c_title, c_text in conc_blocks:
        draw_rounded_rect(draw, (65, cy, W - 65, cy + 98), radius=8, fill="#19233C")
        draw.text((85, cy + 10), c_title, font=f_body_b, fill="#FBBF24" if "东方" in c_title else ("#60A5FA" if "机械" in c_title else "#34D399"))
        # multi-line text
        draw.text((85, cy + 40), c_text[:66], font=f_small, fill="#CBD5E1")
        draw.text((85, cy + 65), c_text[66:], font=f_small, fill="#CBD5E1")
        cy += 112

    # Section 4: Production Decision & Routing
    y = 1715
    draw_rounded_rect(draw, (40, y, W - 40, y + 360), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((70, y + 20), "四、生产管线最终决策：双引擎确定性场景路由", font=f_sec, fill="#38BDF8")

    routes = [
        ("• 写实人像 / 东方神韵 / 情绪短剧 (portrait | cinematic | editorial):",
         "-> 固定单跑【Z-Image Turbo 6B】裸跑零 LoRA，直出作为 Wan 2.2-14B 视频首帧锚点，零维护成本。"),
        ("• 硬核机械 / 气动流线 / 英文排版 / 留白海报 (industrial | aero | typography | poster):",
         "-> 自动触发【双引擎 A/B 对比模式】：Z-Image 与 FLUX.3Klein(长句扩写) 并行出图，并自动生成 SBS 对比板人工择优。"),
        ("• 视频生成管线（14B 唯一标准）与音频商用合规：",
         "-> Wan 2.2-14B 双专家 GGUF + RealESRGAN 超分 + 32fps 光流插帧；100% 切换至 Stable Audio Open + ACE-Step。")
    ]
    ry = y + 75
    for r_head, r_body in routes:
        draw.text((75, ry), r_head, font=f_body_b, fill="#F1F5F9")
        draw.text((95, ry + 30), r_body, font=f_body, fill="#38BDF8" if "Z-Image" in r_body else ("#A78BFA" if "双引擎" in r_body else "#34D399"))
        ry += 85

    # Footer
    draw.text((70, H - 75), "Local-Drama-Studio · 工业级 AI 生产实验室开源发布", font=f_body_b, fill="#64748B")
    draw.text((W - 380, H - 75), "2026 深度评测报告 · 欢迎交流复现", font=f_small, fill="#64748B")

    out_file = OUT_DIR / "scorecard_cn_summary_card.png"
    img.save(out_file, quality=95)
    print(f"Generated Chinese scorecard card: {out_file}")
    return out_file

def generate_english_card():
    W, H = 1600, 2000
    img = Image.new("RGB", (W, H), "#0B0F19")
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_EN_BOLD, 46)
    f_sub = ImageFont.truetype(FONT_EN_REG, 24)
    f_sec = ImageFont.truetype(FONT_EN_BOLD, 30)
    f_body_b = ImageFont.truetype(FONT_EN_BOLD, 22)
    f_body = ImageFont.truetype(FONT_EN_REG, 20)
    f_small = ImageFont.truetype(FONT_EN_REG, 17)

    # Top accent bar
    draw.rectangle([0, 0, W, 10], fill="#3B82F6")

    # Header Card
    draw_rounded_rect(draw, (50, 40, W - 50, 240), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((80, 60), "OPEN-SOURCE IMAGE ENGINE BENCHMARK", font=f_title, fill="#FFFFFF")
    draw.text((80, 122), "Z-Image Turbo 6B (Native Zero-LoRA) vs. FLUX.3 Klein 4B (Distilled + Upsampler)", font=ImageFont.truetype(FONT_EN_BOLD, 26), fill="#60A5FA")
    draw.text((80, 162), "Hardware: Intel Arc A750 8GB VRAM | 64GB DDR5 | 8 Objective Dimensions | 12-Test Standard Suite Blind Eval", font=f_sub, fill="#94A3B8")

    # Badges
    badges = ["Methodological Rigor", "4-Tier Controlled", "Attribution-Sound", "100% Reproducible"]
    bx = 80
    for b in badges:
        draw_rounded_rect(draw, (bx, 198, bx + 220, 230), radius=6, fill="#1E293B")
        draw.text((bx + 15, 204), b, font=f_small, fill="#38BDF8")
        bx += 235

    # Section 1: Methodology
    y = 265
    draw_rounded_rect(draw, (50, y, W - 50, y + 250), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((80, y + 20), "1. METHODOLOGY: 4-TIER CONTROLLED TEST (AVOIDING ATTRIBUTION FALLACY)", font=f_sec, fill="#38BDF8")
    draw.text((80, y + 65), "Comparing 'FLUX + Dual LoRAs' against 'Native Z-Image' and attributing deltas to base models is invalid. We isolate:", font=f_body, fill="#CBD5E1")
    
    rows = [
        ("Group A: Z-Image Turbo Native", "6B Q4_K_M, 8 steps, zero LoRA. Tests pure native Chinese bone structure and photorealism."),
        ("Group B: FLUX.3 Klein Native", "4B Q4_K_M, 4 steps, with official Prompt Upsampler to eliminate short-prompt degradation."),
        ("Group C: FLUX.3 Klein + Single LoRA", "Equipped with Realism or Film Foto LoRA. Measures exact marginal gains vs. color drift."),
        ("Group D: FLUX.3 Klein + Dual LoRAs", "Realism 0.6 + Film 0.5 stacked. Checks if multi-LoRA stacking overfits or causes VRAM spikes."),
    ]
    ry = y + 105
    for tag, desc in rows:
        draw.text((85, ry), f"• {tag}:", font=f_body_b, fill="#F8FAFC")
        draw.text((490, ry + 2), desc, font=f_small, fill="#94A3B8")
        ry += 32

    # Section 2: Scorecard Table
    y = 540
    draw_rounded_rect(draw, (50, y, W - 50, y + 690), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((80, y + 20), "2. OFFICIAL SCORECARD: 8 INDUSTRIAL DIMENSIONS (12-TEST SUITE)", font=f_sec, fill="#38BDF8")

    # Table Header
    ty = y + 70
    draw_rounded_rect(draw, (75, ty, W - 75, ty + 42), radius=8, fill="#1E293B")
    draw.text((95, ty + 10), "Evaluation Dimension & Scenario", font=f_body_b, fill="#F1F5F9")
    draw.text((650, ty + 10), "Z-Image Turbo (Native 6B)", font=f_body_b, fill="#60A5FA")
    draw.text((1050, ty + 10), "FLUX.3 Klein (4B + Upsampler)", font=f_body_b, fill="#A78BFA")
    draw.text((1420, ty + 10), "Winner", font=f_body_b, fill="#34D399")

    table_data = [
        ("1. East Asian Portrait & Skin Micro-Pores", "4.9 / 5.0 (Sub-surface vascular glow)", "3.8 / 5.0 (Biased toward Caucasian)", "Z-Image"),
        ("2. Eye Light & Micro-Expression Dynamics", "4.8 / 5.0 (Gentle blooming micro-smile)", "3.9 / 5.0 (Relatively stiff gaze)", "Z-Image"),
        ("3. Mechanical & Automotive Assembly Rigor", "3.7 / 5.0 (Minor non-physical parts)", "4.8 / 5.0 (Precise ceramic brake/bolts)", "FLUX.3"),
        ("4. English Typography & Technical Labels", "2.8 / 5.0 (Artifacts on tiny labels)", "4.9 / 5.0 (100% accurate spelling on 5 labels)", "FLUX.3"),
        ("5. Spatial Negative Space & Composition", "3.9 / 5.0 (Tends to clutter background)", "4.7 / 5.0 (Strict 40% empty space for subs)", "FLUX.3"),
        ("6. Fluid Dynamics & Aerodynamics (CFD)", "3.5 / 5.0 (Artistic rather than physical)", "4.6 / 5.0 (Strict laminar boundary flow)", "FLUX.3"),
        ("7. Cross-Scene Character Consistency (Lin)", "4.6 / 5.0 (Stable beauty mark/structure)", "4.5 / 5.0 (Tied with strict anchor tokens)", "Tied"),
        ("8. Inference Steps & Generation Latency", "8 steps · 7.8s @ 1024px", "4 steps · 6.2s @ 1024px", "FLUX.3"),
        ("9. Peak VRAM Footprint (8GB Tested)", "4.2 GB (Completely safe)", "4.0 GB (Completely safe)", "Tied"),
        ("10. Maintenance Overhead & Overfitting", "Zero (Native single checkpoint)", "Moderate (Requires prompt tuning/LoRA)", "Z-Image"),
    ]

    row_y = ty + 50
    for i, (dim, z_score, f_score, winner) in enumerate(table_data):
        bg = "#182238" if i % 2 == 1 else "#131B2E"
        draw_rounded_rect(draw, (75, row_y, W - 75, row_y + 50), radius=4, fill=bg)
        draw.text((95, row_y + 13), dim, font=f_body, fill="#E2E8F0")
        draw.text((650, row_y + 13), z_score, font=f_body, fill="#93C5FD")
        draw.text((1050, row_y + 13), f_score, font=f_body, fill="#C4B5FD")
        
        w_color = "#34D399" if "Z-Image" in winner else ("#A78BFA" if "FLUX" in winner else "#FBBF24")
        draw.text((1420, row_y + 13), winner, font=f_body_b, fill=w_color)
        row_y += 54

    # Section 3: Key Takeaways
    y = 1250
    draw_rounded_rect(draw, (50, y, W - 50, y + 360), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((80, y + 20), "3. VERDICT: NO ABSOLUTE CHAMPION — DOMAIN-SPECIFIC SPECIALIZATION", font=f_sec, fill="#38BDF8")

    conc_blocks = [
        ("CROWN FOR PHOTOREALISM & PORTRAITURE: Z-IMAGE TURBO (6B)",
         "Without any external LoRA, Z-Image delivers world-class translucent Asian skin micro-texture and organic facial bone structure. It completely eliminates plastic artificiality and overly airbrushed 'AI-doll' tropes. The ultimate engine for cinematic character closeups."),
        
        ("CROWN FOR INDUSTRIAL GEOMETRY, AERODYNAMICS & TYPO: FLUX.3 KLEIN (4B)",
         "With official Prompt Upsampling, FLUX.3 dominates mechanical realism (carbon-ceramic brakes, turbine rotors) and fluid mechanics (CFD rainbow contour maps). Its 100% error-free English typography and strict 40% negative space control make it the gold standard for technical slides."),

        ("ACCESSIBILITY TRIUMPH: 8GB VRAM COMMODITIZATION",
         "Under Q4_K_M GGUF quantization, both models run under 4.2GB VRAM. Sub-$200 GPUs (Intel Arc A750, RTX 3060) can effortlessly produce 2K commercial-grade imagery in under 8 seconds per frame."),
    ]

    cy = y + 65
    for c_title, c_text in conc_blocks:
        draw_rounded_rect(draw, (75, cy, W - 75, cy + 85), radius=8, fill="#19233C")
        draw.text((95, cy + 8), c_title, font=f_body_b, fill="#FBBF24" if "PORTRAITURE" in c_title else ("#60A5FA" if "INDUSTRIAL" in c_title else "#34D399"))
        draw.text((95, cy + 35), c_text[:115], font=f_small, fill="#CBD5E1")
        draw.text((95, cy + 58), c_text[115:], font=f_small, fill="#CBD5E1")
        cy += 96

    # Section 4: Production Decision & Routing
    y = 1630
    draw_rounded_rect(draw, (50, y, W - 50, y + 290), radius=16, fill="#131B2E", outline="#1E293B", width=2)
    draw.text((80, y + 20), "4. PRODUCTION DECISION: DETERMINISTIC DUAL-ENGINE ROUTING", font=f_sec, fill="#38BDF8")

    routes = [
        ("• Portrait / Cinematic / Editorial Tasks:",
         "-> Routed directly to Z-Image Turbo (Zero-LoRA). Direct anchor frame for Wan 2.2-14B video synthesis."),
        ("• Mechanical / Engineering / Typography / Slide Backgrounds:",
         "-> Automatically triggers Dual-Engine Parallel A/B Mode (Z-Image vs. FLUX.3 Klein + Upsampler) with auto-generated SBS review boards."),
        ("• Video & Audio Pipeline Pipeline Standards:",
         "-> Fixed to Wan 2.2-14B I2V + RealESRGAN + 32fps Optical Flow; 100% commercial-compliant audio (Stable Audio Open + ACE-Step).")
    ]
    ry = y + 65
    for r_head, r_body in routes:
        draw.text((85, ry), r_head, font=f_body_b, fill="#F1F5F9")
        draw.text((105, ry + 26), r_body, font=f_body, fill="#38BDF8" if "Z-Image" in r_body else ("#A78BFA" if "Dual-Engine" in r_body else "#34D399"))
        ry += 68

    # Footer
    draw.text((80, H - 65), "Local-Drama-Studio · Open-Source AI Production Laboratory", font=f_body_b, fill="#64748B")
    draw.text((W - 480, H - 65), "2026 Comprehensive Benchmark Report · Reproducible", font=f_small, fill="#64748B")

    out_file = OUT_DIR / "scorecard_en_summary_card.png"
    img.save(out_file, quality=95)
    print(f"Generated English scorecard card: {out_file}")
    return out_file

if __name__ == "__main__":
    generate_chinese_card()
    generate_english_card()
