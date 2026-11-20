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

def generate_chinese_light_card():
    W, H = 1200, 2250
    # Clean modern light palette
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_ZH_BOLD, 46)
    f_sub = ImageFont.truetype(FONT_ZH_REG, 24)
    f_sec = ImageFont.truetype(FONT_ZH_BOLD, 30)
    f_body_b = ImageFont.truetype(FONT_ZH_BOLD, 22)
    f_body = ImageFont.truetype(FONT_ZH_REG, 20)
    f_small = ImageFont.truetype(FONT_ZH_REG, 17)

    # Top Royal Blue Accent
    draw.rectangle([0, 0, W, 12], fill="#2563EB")

    # Header Card (Pure White with Crisp Border)
    draw_rounded_rect(draw, (40, 35, W - 40, 240), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((70, 55), "开源生图双引擎深度评测 · 权威成绩单", font=f_title, fill="#0F172A")
    draw.text((70, 118), "Z-Image Turbo 6B (裸跑零LoRA)  VS  FLUX.3 Klein 4B (蒸馏+扩写)", font=ImageFont.truetype(FONT_ZH_BOLD, 26), fill="#2563EB")
    draw.text((70, 160), "测试环境：Intel Arc A750 8GB VRAM | 64GB DDR5 | 8大客观维度 | 12题标准测试集", font=f_sub, fill="#475569")

    # Badges
    badges = [("四层受控实验", "#EFF6FF", "#1D4ED8"), 
              ("拒绝归因谬误", "#F0FDF4", "#15803D"), 
              ("拒绝看图说话", "#FEF3C7", "#B45309"), 
              ("100%本地可复现", "#F3E8FF", "#6B21A8")]
    bx = 70
    for text, bg, fg in badges:
        draw_rounded_rect(draw, (bx, 198, bx + 160, 230), radius=6, fill=bg, outline="#E2E8F0")
        draw.text((bx + 16, 203), text, font=f_small, fill=fg)
        bx += 175

    # Section 1: Methodology
    y = 265
    draw_rounded_rect(draw, (40, y, W - 40, y + 250), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((70, y + 20), "一、评测方法论：拆开4组受控配置（避免归因混乱）", font=f_sec, fill="#1E293B")
    draw.text((70, y + 65), "把『FLUX双LoRA』对比『Z-Image裸跑』归因给基模是严重错误。本次严格拆解4组对照：", font=f_body, fill="#334155")
    
    rows = [
        ("A 组：Z-Image Turbo 裸跑", "6B 原生 Q4_K_M，8步收敛，零 LoRA，考核底座原生东方骨相与真实感"),
        ("B 组：FLUX.3 Klein 裸跑", "4B 原生 Q4_K_M，4步极速，严格开启官方 Prompt Upsampler 提示词扩写"),
        ("C 组：FLUX.3 Klein + 单LoRA", "挂载写实/胶片单 LoRA，精确评估单一微调带来的增益与代价"),
        ("D 组：FLUX.3 Klein + 双LoRA", "写实0.6 + 胶片0.5 叠加，实测多 LoRA 是否过拟合或导致显存溢出"),
    ]
    ry = y + 105
    for tag, desc in rows:
        draw.text((75, ry), f"• {tag}:", font=f_body_b, fill="#0F172A")
        draw.text((410, ry + 2), desc, font=f_small, fill="#64748B")
        ry += 32

    # Section 2: Scorecard Table
    y = 540
    draw_rounded_rect(draw, (40, y, W - 40, y + 715), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((70, y + 20), "二、三张权威量化成绩单（八大客观维度实测评分）", font=f_sec, fill="#1E293B")

    # Table Header
    ty = y + 70
    draw_rounded_rect(draw, (65, ty, W - 65, ty + 42), radius=8, fill="#F1F5F9", outline="#E2E8F0")
    draw.text((85, ty + 10), "评测维度与场景", font=f_body_b, fill="#1E293B")
    draw.text((440, ty + 10), "Z-Image Turbo (裸跑)", font=f_body_b, fill="#2563EB")
    draw.text((740, ty + 10), "FLUX.3 Klein (底模+扩写)", font=f_body_b, fill="#7C3AED")
    draw.text((1010, ty + 10), "胜出归属", font=f_body_b, fill="#059669")

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
        bg = "#F8FAFC" if i % 2 == 1 else "#FFFFFF"
        draw_rounded_rect(draw, (65, row_y, W - 65, row_y + 52), radius=4, fill=bg, outline="#F1F5F9")
        draw.text((85, row_y + 14), dim, font=f_body, fill="#334155")
        draw.text((440, row_y + 14), z_score, font=f_body, fill="#1D4ED8")
        draw.text((740, row_y + 14), f_score, font=f_body, fill="#6D28D9")
        
        w_color = "#059669" if "Z-Image" in winner else ("#7C3AED" if "FLUX" in winner else "#D97706")
        draw.text((1010, row_y + 14), winner, font=f_body_b, fill=w_color)
        row_y += 56

    # Section 3: Core Conclusions
    y = 1280
    draw_rounded_rect(draw, (40, y, W - 40, y + 430), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((70, y + 20), "三、核心测评结论：谁更强？没有绝对冠军，只有场景最优！", font=f_sec, fill="#1E293B")

    conc_blocks = [
        ("👑 东方人像与电影感光影之王：Z-Image Turbo 6B", 
         "在不挂载任何 LoRA 的裸跑状态下，Z-Image 凭借深厚的中文东方美学预训练，直出具备微血管通透感的真实皮肤毛孔与自然骨相，彻底终结了开源领域的『AI假人脸』。适合人像写真、国风短剧、日系街拍。", "#FEF3C7", "#92400E"),
        
        ("👑 机械工业、流体力学与排版之王：FLUX.3 Klein 4B", 
         "在开启官方 Prompt Upsampler 扩写后，FLUX.3 对几何空间透视、跑车打孔刹车盘装配、风洞层流分离展现出统治级物理严谨度；在 5 个航天英文零件测试中 100% 零错字，左侧 40% 纯净留白更是课件与字幕排版神器。", "#EFF6FF", "#1E40AF"),

        ("⚡ 8GB 显存普及化奇迹：两者均彻底打破算力门槛", 
         "得益于 Q4_K_M GGUF 量化与蒸馏技术，Z-Image (8步) 与 FLUX.3 (4步) 显存占用均仅为 4GB 左右，RTX 3060 / Intel Arc A750 甚至轻薄本均可在 7 秒内完成单张 2K 高清交付。", "#ECFDF5", "#065F46"),
    ]

    cy = y + 70
    for c_title, c_text, bg, fg in conc_blocks:
        draw_rounded_rect(draw, (65, cy, W - 65, cy + 102), radius=8, fill=bg, outline="#E2E8F0")
        draw.text((85, cy + 10), c_title, font=f_body_b, fill=fg)
        draw.text((85, cy + 42), c_text[:68], font=f_small, fill="#334155")
        draw.text((85, cy + 68), c_text[68:], font=f_small, fill="#334155")
        cy += 116

    # Section 4: Production Decision & Routing
    y = 1735
    draw_rounded_rect(draw, (40, y, W - 40, y + 365), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((70, y + 20), "四、生产管线最终决策：双引擎确定性场景路由", font=f_sec, fill="#1E293B")

    routes = [
        ("• 写实人像 / 东方神韵 / 情绪短剧 (portrait | cinematic | editorial):",
         "-> 固定单跑【Z-Image Turbo 6B】裸跑零 LoRA，直出作为 Wan 2.2-14B 视频首帧锚点，零维护成本。"),
        ("• 硬核机械 / 气动流线 / 英文排版 / 留白海报 (industrial | aero | typography | poster):",
         "-> 自动触发【双引擎 A/B 对比模式】：Z-Image 与 FLUX.3Klein(长句扩写) 并行出图，自动生成 SBS 对比板人工择优。"),
        ("• 视频生成管线（14B 唯一标准）与音频商用合规：",
         "-> Wan 2.2-14B 双专家 GGUF + RealESRGAN 超分 + 32fps 光流插帧；100% 切换至 Stable Audio Open + ACE-Step。")
    ]
    ry = y + 75
    for r_head, r_body in routes:
        draw.text((75, ry), r_head, font=f_body_b, fill="#0F172A")
        draw.text((95, ry + 30), r_body, font=f_body, fill="#2563EB" if "Z-Image" in r_body else ("#7C3AED" if "双引擎" in r_body else "#059669"))
        ry += 88

    # Footer
    draw.text((70, H - 75), "Local-Drama-Studio · 工业级 AI 生产实验室开源发布", font=f_body_b, fill="#64748B")
    draw.text((W - 380, H - 75), "2026 深度评测报告 · 欢迎交流复现", font=f_small, fill="#64748B")

    out_file = OUT_DIR / "scorecard_cn_summary_card_light.png"
    img.save(out_file, quality=95)
    print(f"Generated Chinese Light scorecard card: {out_file}")
    return out_file

def generate_english_light_card():
    W, H = 1600, 2050
    # Clean modern light palette
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_EN_BOLD, 46)
    f_sub = ImageFont.truetype(FONT_EN_REG, 24)
    f_sec = ImageFont.truetype(FONT_EN_BOLD, 30)
    f_body_b = ImageFont.truetype(FONT_EN_BOLD, 22)
    f_body = ImageFont.truetype(FONT_EN_REG, 20)
    f_small = ImageFont.truetype(FONT_EN_REG, 17)

    # Top Royal Blue Accent
    draw.rectangle([0, 0, W, 12], fill="#2563EB")

    # Header Card
    draw_rounded_rect(draw, (50, 40, W - 50, 245), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((80, 60), "OPEN-SOURCE IMAGE ENGINE BENCHMARK", font=f_title, fill="#0F172A")
    draw.text((80, 122), "Z-Image Turbo 6B (Native Zero-LoRA) vs. FLUX.3 Klein 4B (Distilled + Upsampler)", font=ImageFont.truetype(FONT_EN_BOLD, 26), fill="#2563EB")
    draw.text((80, 162), "Hardware: Intel Arc A750 8GB VRAM | 64GB DDR5 | 8 Objective Dimensions | 12-Test Standard Suite Blind Eval", font=f_sub, fill="#475569")

    # Badges
    badges = [("Methodological Rigor", "#EFF6FF", "#1D4ED8"), 
              ("4-Tier Controlled", "#F0FDF4", "#15803D"), 
              ("Attribution-Sound", "#FEF3C7", "#B45309"), 
              ("100% Reproducible", "#F3E8FF", "#6B21A8")]
    bx = 80
    for text, bg, fg in badges:
        draw_rounded_rect(draw, (bx, 200, bx + 225, 232), radius=6, fill=bg, outline="#E2E8F0")
        draw.text((bx + 18, 206), text, font=f_small, fill=fg)
        bx += 240

    # Section 1: Methodology
    y = 270
    draw_rounded_rect(draw, (50, y, W - 50, y + 250), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((80, y + 20), "1. METHODOLOGY: 4-TIER CONTROLLED TEST (AVOIDING ATTRIBUTION FALLACY)", font=f_sec, fill="#1E293B")
    draw.text((80, y + 65), "Comparing 'FLUX + Dual LoRAs' against 'Native Z-Image' and attributing deltas to base models is invalid. We isolate:", font=f_body, fill="#334155")
    
    rows = [
        ("Group A: Z-Image Turbo Native", "6B Q4_K_M, 8 steps, zero LoRA. Tests pure native Chinese bone structure and photorealism."),
        ("Group B: FLUX.3 Klein Native", "4B Q4_K_M, 4 steps, with official Prompt Upsampler to eliminate short-prompt degradation."),
        ("Group C: FLUX.3 Klein + Single LoRA", "Equipped with Realism or Film Foto LoRA. Measures exact marginal gains vs. color drift."),
        ("Group D: FLUX.3 Klein + Dual LoRAs", "Realism 0.6 + Film 0.5 stacked. Checks if multi-LoRA stacking overfits or causes VRAM spikes."),
    ]
    ry = y + 105
    for tag, desc in rows:
        draw.text((85, ry), f"• {tag}:", font=f_body_b, fill="#0F172A")
        draw.text((490, ry + 2), desc, font=f_small, fill="#64748B")
        ry += 32

    # Section 2: Scorecard Table
    y = 545
    draw_rounded_rect(draw, (50, y, W - 50, y + 700), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((80, y + 20), "2. OFFICIAL SCORECARD: 8 INDUSTRIAL DIMENSIONS (12-TEST SUITE)", font=f_sec, fill="#1E293B")

    # Table Header
    ty = y + 70
    draw_rounded_rect(draw, (75, ty, W - 75, ty + 42), radius=8, fill="#F1F5F9", outline="#E2E8F0")
    draw.text((95, ty + 10), "Evaluation Dimension & Scenario", font=f_body_b, fill="#1E293B")
    draw.text((650, ty + 10), "Z-Image Turbo (Native 6B)", font=f_body_b, fill="#2563EB")
    draw.text((1050, ty + 10), "FLUX.3 Klein (4B + Upsampler)", font=f_body_b, fill="#7C3AED")
    draw.text((1420, ty + 10), "Winner", font=f_body_b, fill="#059669")

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
        bg = "#F8FAFC" if i % 2 == 1 else "#FFFFFF"
        draw_rounded_rect(draw, (75, row_y, W - 75, row_y + 50), radius=4, fill=bg, outline="#F1F5F9")
        draw.text((95, row_y + 13), dim, font=f_body, fill="#334155")
        draw.text((650, row_y + 13), z_score, font=f_body, fill="#1D4ED8")
        draw.text((1050, row_y + 13), f_score, font=f_body, fill="#6D28D9")
        
        w_color = "#059669" if "Z-Image" in winner else ("#7C3AED" if "FLUX" in winner else "#D97706")
        draw.text((1420, row_y + 13), winner, font=f_body_b, fill=w_color)
        row_y += 54

    # Section 3: Key Takeaways
    y = 1270
    draw_rounded_rect(draw, (50, y, W - 50, y + 365), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((80, y + 20), "3. VERDICT: NO ABSOLUTE CHAMPION — DOMAIN-SPECIFIC SPECIALIZATION", font=f_sec, fill="#1E293B")

    conc_blocks = [
        ("CROWN FOR PHOTOREALISM & PORTRAITURE: Z-IMAGE TURBO (6B)",
         "Without any external LoRA, Z-Image delivers world-class translucent Asian skin micro-texture and organic facial bone structure. It completely eliminates plastic artificiality and overly airbrushed 'AI-doll' tropes. The ultimate engine for cinematic character closeups.", "#FEF3C7", "#92400E"),
        
        ("CROWN FOR INDUSTRIAL GEOMETRY, AERODYNAMICS & TYPO: FLUX.3 KLEIN (4B)",
         "With official Prompt Upsampling, FLUX.3 dominates mechanical realism (carbon-ceramic brakes, turbine rotors) and fluid mechanics (CFD rainbow contour maps). Its 100% error-free English typography and strict 40% negative space control make it the gold standard for technical slides.", "#EFF6FF", "#1E40AF"),

        ("ACCESSIBILITY TRIUMPH: 8GB VRAM COMMODITIZATION",
         "Under Q4_K_M GGUF quantization, both models run under 4.2GB VRAM. Sub-$200 GPUs (Intel Arc A750, RTX 3060) can effortlessly produce 2K commercial-grade imagery in under 8 seconds per frame.", "#ECFDF5", "#065F46"),
    ]

    cy = y + 68
    for c_title, c_text, bg, fg in conc_blocks:
        draw_rounded_rect(draw, (75, cy, W - 75, cy + 88), radius=8, fill=bg, outline="#E2E8F0")
        draw.text((95, cy + 9), c_title, font=f_body_b, fill=fg)
        draw.text((95, cy + 36), c_text[:115], font=f_small, fill="#334155")
        draw.text((95, cy + 60), c_text[115:], font=f_small, fill="#334155")
        cy += 98

    # Section 4: Production Decision & Routing
    y = 1660
    draw_rounded_rect(draw, (50, y, W - 50, y + 290), radius=16, fill="#FFFFFF", outline="#E2E8F0", width=2)
    draw.text((80, y + 20), "4. PRODUCTION DECISION: DETERMINISTIC DUAL-ENGINE ROUTING", font=f_sec, fill="#1E293B")

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
        draw.text((85, ry), r_head, font=f_body_b, fill="#0F172A")
        draw.text((105, ry + 26), r_body, font=f_body, fill="#2563EB" if "Z-Image" in r_body else ("#7C3AED" if "Dual-Engine" in r_body else "#059669"))
        ry += 68

    # Footer
    draw.text((80, H - 65), "Local-Drama-Studio · Open-Source AI Production Laboratory", font=f_body_b, fill="#64748B")
    draw.text((W - 480, H - 65), "2026 Comprehensive Benchmark Report · Reproducible", font=f_small, fill="#64748B")

    out_file = OUT_DIR / "scorecard_en_summary_card_light.png"
    img.save(out_file, quality=95)
    print(f"Generated English Light scorecard card: {out_file}")
    return out_file

if __name__ == "__main__":
    generate_chinese_light_card()
    generate_english_light_card()
