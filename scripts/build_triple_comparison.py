import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = ROOT / "outputs" / "model_benchmark" / "comparison_boards" / "case01_triple_lora_revelation.jpg"

img1_path = ROOT / "outputs" / "model_benchmark" / "raw" / "flux3_klein_20261101_flux3_klein_20261101_00003_.png"
img2_path = ROOT / "outputs" / "raw" / "flux3_klein_20261101_flux3_klein_20261101_00005_.png"
img3_path = ROOT / "outputs" / "model_benchmark" / "raw" / "z_image_turbo_20261101_z_image_turbo_20261101_00003_.png"

img1 = Image.open(img1_path).convert("RGB")
img2 = Image.open(img2_path).convert("RGB")
img3 = Image.open(img3_path).convert("RGB")

target_w, target_h = 600, 1060
r1 = img1.resize((target_w, target_h), Image.Resampling.LANCZOS)
r2 = img2.resize((target_w, target_h), Image.Resampling.LANCZOS)
r3 = img3.resize((target_w, target_h), Image.Resampling.LANCZOS)

margin = 35
gap = 25
header_h = 160
footer_h = 100

canvas_w = margin * 2 + target_w * 3 + gap * 2
canvas_h = margin * 2 + header_h + target_h + footer_h

canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 20, 24))
draw = ImageDraw.Draw(canvas)

# Title
draw.text((margin, margin + 20), "SHANGHAI CANDID · TRIPLE ARCHITECTURE & LORA REVELATION", fill=(245, 245, 248))
draw.text((margin, margin + 70), "Empirical Proof: FLUX.3 Native vs FLUX.3 + 0.70 East-Asian LoRA vs Z-Image Turbo Native 6B DiT", fill=(160, 165, 175))

# Paste 3 images
pos1 = (margin, margin + header_h)
pos2 = (margin + target_w + gap, margin + header_h)
pos3 = (margin + (target_w + gap) * 2, margin + header_h)

canvas.paste(r1, pos1)
canvas.paste(r2, pos2)
canvas.paste(r3, pos3)

# Sub-titles
draw.text((pos1[0], pos1[1] - 45), "1. FLUX.3 Klein (Zero-LoRA)", fill=(220, 225, 235))
draw.text((pos1[0], pos1[1] - 22), "16 Steps | Native Western Bone Structure", fill=(130, 140, 150))

draw.text((pos2[0], pos2[1] - 45), "2. FLUX.3 + girlslikeflux (0.70)", fill=(255, 200, 120))
draw.text((pos2[0], pos2[1] - 22), "16 Steps | Heavy LoRA Face Retargeting", fill=(200, 160, 100))

draw.text((pos3[0], pos3[1] - 45), "3. Z-Image Turbo (Zero-LoRA)", fill=(130, 225, 255))
draw.text((pos3[0], pos3[1] - 22), "8 Steps (7.0s) | Native East Asian Candid DiT", fill=(100, 180, 220))

foot_y = canvas_h - margin - footer_h + 30
draw.text((margin, foot_y), "Local Drama Studio Architecture Analysis · Intel Arc A750 XPU Acceleration", fill=(120, 125, 135))

BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
canvas.save(BOARD_PATH, format="JPEG", quality=92, optimize=True)
print("Triple board saved:", BOARD_PATH)
