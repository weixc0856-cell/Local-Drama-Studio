#!/usr/bin/env python3
"""
scripts/download_audio_models.py
Downloads vetted, commercially-permissive audio foundation models via ModelScope:
1. Stability AI · Stable Audio Open 1.0 (Community License, free <$1M commercial)
2. ACE Studio & StepFun · ACE-Step 1.5 XL Turbo (MIT License, completely unencumbered commercial)

Target Location: D:/AI/models/audio/
"""

import sys
import os
import time
from pathlib import Path

TARGET_BASE = Path("D:/AI/models/audio")

def download_audio_models():
    TARGET_BASE.mkdir(parents=True, exist_ok=True)
    print("=" * 75)
    print(" Commercial Audio Model Downloader (ModelScope CDN)")
    print(f" Target Directory: {TARGET_BASE}")
    print("=" * 75)

    try:
        from modelscope import snapshot_download
    except ImportError:
        print("[Error] 'modelscope' package not installed in current environment.")
        sys.exit(1)

    # 1. Stable Audio Open 1.0 (SFX / Foley / Short Ambient)
    sa_dir = TARGET_BASE / "stable-audio-open-1.0"
    print(f"\n[1/2] Checking: Stable Audio Open 1.0 -> {sa_dir}")
    if sa_dir.exists() and any(sa_dir.glob("*.safetensors")):
        print(f"      Already exists with weights. Skipping.")
    else:
        print(f"      Downloading 'stabilityai/stable-audio-open-1.0' (Diffusers only, skipping .ckpt)...")
        t0 = time.time()
        snapshot_download(
            "stabilityai/stable-audio-open-1.0",
            local_dir=str(sa_dir),
            ignore_file_pattern=["*.ckpt*", "*.incomplete"]
        )
        print(f"      Downloaded in {time.time() - t0:.1f}s!")

    # 2. ACE-Step 1.5 XL Turbo (4B DiT, 8-Step Distilled, Full Instrumental BGM)
    ace_dir = TARGET_BASE / "acestep-v15-xl-turbo-diffusers"
    print(f"\n[2/2] Checking: ACE-Step 1.5 XL Turbo -> {ace_dir}")
    if ace_dir.exists() and any(ace_dir.glob("*.safetensors")):
        print(f"      Already exists with weights. Skipping.")
    else:
        print(f"      Downloading 'ACE-Step/acestep-v15-xl-turbo-diffusers'...")
        t0 = time.time()
        try:
            snapshot_download(
                "ACE-Step/acestep-v15-xl-turbo-diffusers",
                local_dir=str(ace_dir)
            )
            print(f"      Downloaded in {time.time() - t0:.1f}s!")
        except Exception as e:
            print(f"      [Warning] ModelScope ACE-Step alias fallback: {e}")
            snapshot_download(
                "stepfun-ai/ACE-Step",
                local_dir=str(ace_dir)
            )

    print("\n[SUCCESS] Audio foundation models are ready in D:/AI/models/audio/!")

if __name__ == "__main__":
    download_audio_models()
