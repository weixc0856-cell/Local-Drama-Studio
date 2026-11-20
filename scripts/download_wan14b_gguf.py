#!/usr/bin/env python3
"""Download Wan2.1-I2V-14B-480P-GGUF (Q4_K_M) from ModelScope directly into target directory."""
import os
import sys
import shutil
from pathlib import Path
from modelscope.hub.file_download import model_file_download

DEST_DIR = Path(r"D:\AI\models\diffusion_models\wan")
DEST_DIR.mkdir(parents=True, exist_ok=True)
TARGET_FILE = DEST_DIR / "wan2.1-i2v-14b-480p-Q4_K_M.gguf"

if TARGET_FILE.exists() and TARGET_FILE.stat().st_size > 11_000_000_000:
    print(f"File already exists: {TARGET_FILE} ({TARGET_FILE.stat().st_size / (1024**3):.2f} GB)")
    sys.exit(0)

print("Starting download of wan2.1-i2v-14b-480p-Q4_K_M.gguf (11.34 GB) from ModelScope...")
cached_path = model_file_download(
    model_id="city96/Wan2.1-I2V-14B-480P-GGUF",
    file_path="wan2.1-i2v-14b-480p-Q4_K_M.gguf"
)
print("Download finished to cache:", cached_path)
print("Moving to destination:", TARGET_FILE)
shutil.copyfile(cached_path, TARGET_FILE)
print(f"Successfully placed: {TARGET_FILE} ({TARGET_FILE.stat().st_size / (1024**3):.2f} GB)")
