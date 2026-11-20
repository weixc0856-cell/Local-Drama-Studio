import shutil
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance

ROOT = Path(r"d:\Local-Drama-Studio")
EXP_DIR = ROOT / "experiments" / "portrait_quality_ab_test"
DAY12_DIR = ROOT / "experiments" / "global_beauties_day12"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

src = EXP_DIR / "case4_ultra_native_864.png"
dst_day12 = DAY12_DIR / "day12_01_china_cinema.png"
dst_art = ARTIFACTS_DIR / "day12_01_china_cinema.png"

# Upscale Case 4 from 864x1536 to 1152x2048
img = Image.open(src).convert("RGB")
up = img.resize((1152, 2048), Image.Resampling.LANCZOS)
sharpened = up.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=3))
enhancer = ImageEnhance.Contrast(sharpened)
final_img = enhancer.enhance(1.02)

final_img.save(dst_day12, "PNG", quality=95)
shutil.copy(dst_day12, dst_art)
print(f"Replaced Day 12 Photo 1 with Case 4 High-Res: {dst_day12}")

# Re-assemble Day 12 6-grid board
import subprocess
import sys
# Run the board assembly part from generate_day12_cinema_beauties_2k.py
sys.path.append(str(ROOT / "scripts"))
from generate_day12_cinema_beauties_2k import make_6grid_board, generate_patreon_post_markdown

image_paths = [DAY12_DIR / f"day12_{i:02d}_{name}.png" for i, name in [
    (1, "china_cinema"),
    (2, "western_cinema"),
    (3, "japan_cinema"),
    (4, "korea_cinema"),
    (5, "mediterranean_cinema"),
    (6, "scifi_cinema")
]]

board_file = DAY12_DIR / "day12_cinema_muses_6grid.png"
art_board_file = ARTIFACTS_DIR / "day12_cinema_muses_6grid.png"
make_6grid_board(image_paths, board_file, art_board_file)
generate_patreon_post_markdown()
print("Successfully updated Day 12 6-Grid board!")
