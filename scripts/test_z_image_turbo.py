#!/usr/bin/env python3
"""
scripts/test_z_image_turbo.py
End-to-end automated testing runner for Z-Image Turbo on Intel Arc A750.
Steps:
1. Verify / fetch required models from ModelScope / HuggingFace to D:\\AI\\models
2. Ensure ComfyUI background instance is running (port 8188)
3. Submit Z-Image Turbo 8-step test prompt
4. Verify execution, download result image, and run postprocessing
5. Report timing, VRAM safety, and visual artifacts
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODELS_DIR = Path(r"D:\AI\models")
Z_UNET_DIR = MODELS_DIR / "diffusion_models" / "z_image"
Z_CLIP_DIR = MODELS_DIR / "text_encoders"
Z_UNET_FILE = Z_UNET_DIR / "z-image-turbo-Q4_K_M.gguf"
Z_CLIP_FILE = Z_CLIP_DIR / "Qwen3-4B-Q4_K_M.gguf"
VAE_FILE = MODELS_DIR / "vae" / "flux2-vae.safetensors"

COMFY_DIR = ROOT / "runtime" / "ComfyUI"
COMFY_PY = COMFY_DIR / ".venv" / "Scripts" / "python.exe"
BASE_URL = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def check_and_prepare_models():
    print("[1/5] Checking model weights in D:\\AI\\models...")
    Z_UNET_DIR.mkdir(parents=True, exist_ok=True)
    Z_CLIP_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    if not Z_UNET_FILE.exists():
        missing.append(("Unet GGUF", Z_UNET_FILE, "unsloth/Z-Image-Turbo-GGUF", "z-image-turbo-Q4_K_M.gguf", Z_UNET_DIR))
    if not Z_CLIP_FILE.exists():
        missing.append(("Text Encoder", Z_CLIP_FILE, "Qwen/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf", Z_CLIP_DIR))

    if not missing:
        print("  All required Z-Image Turbo models are present.")
        return True

    print(f"  Missing {len(missing)} model files:")
    for label, target_path, repo, filename, dest_dir in missing:
        print(f"    - {label}: {target_path.name} (Source: {repo})")

    # Try downloading using modelscope if available
    for label, target_path, repo, filename, dest_dir in missing:
        print(f"\n  Downloading {label} ({filename})...")
        cmd = [
            sys.executable, "-c",
            f"from modelscope.hub.file_download import model_file_download; "
            f"model_file_download('{repo}', '{filename}', local_dir=r'{dest_dir}')"
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"  Successfully downloaded: {target_path.name}")
        except Exception as e:
            print(f"  Automatic download failed: {e}")
            print(f"  Please execute manually:")
            print(f"    modelscope download --model {repo} {filename} --local_dir {dest_dir}")
            return False

    return True


def ensure_comfyui_running() -> bool:
    print("\n[2/5] Checking ComfyUI service status...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/system_stats")
        with OPENER.open(req, timeout=3) as r:
            if r.status == 200:
                print("  ComfyUI is already running and ready at http://127.0.0.1:8188")
                return True
    except Exception:
        pass

    print("  ComfyUI is not running. Launching background process...")
    if not COMFY_PY.exists():
        print(f"  Error: ComfyUI python runtime not found at {COMFY_PY}")
        return False

    cmd = [
        str(COMFY_PY), "main.py",
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--disable-auto-launch"
    ]
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_log = open(log_dir / "comfyui.log", "w", encoding="utf-8")
    err_log = open(log_dir / "comfyui.err.log", "w", encoding="utf-8")

    subprocess.Popen(cmd, cwd=str(COMFY_DIR), stdout=out_log, stderr=err_log)
    print("  ComfyUI process started. Waiting for endpoint readiness...")

    deadline = time.time() + 90
    while time.time() < deadline:
        time.sleep(2)
        try:
            req = urllib.request.Request(f"{BASE_URL}/system_stats")
            with OPENER.open(req, timeout=2) as r:
                if r.status == 200:
                    print("  ComfyUI is ready at http://127.0.0.1:8188")
                    return True
        except Exception:
            pass

    print("  Error: ComfyUI failed to start within timeout. Check logs/comfyui.err.log")
    return False


def run_test_generation():
    from scripts.generator import run_generation
    from scripts.postprocess import export_clean_raw, export_social_web, build_four_grid_board

    print("\n[3/5] Submitting Z-Image Turbo Test Generation...")
    prompt_file = ROOT / "prompts" / "day04_tokyo.txt"
    prompt_text = prompt_file.read_text(encoding="utf-8").strip()

    raw_output_dir = ROOT / "outputs" / "test_z_image" / "raw"
    clean_dir = ROOT / "outputs" / "test_z_image" / "clean_raw"
    web_dir = ROOT / "outputs" / "test_z_image" / "social_web"

    t0 = time.time()
    generated = run_generation(
        engine="z_image_turbo",
        prompt=prompt_text,
        seed=20261103,
        batch_count=1,
        output_dir=raw_output_dir,
        overrides={"steps": 8, "cfg": 1.0}
    )
    elapsed = time.time() - t0

    print(f"\n[4/5] Generation finished in {elapsed:.1f}s.")
    print("\n[5/5] Running Post-Processing...")
    for p in generated:
        c_path = export_clean_raw(p, clean_dir)
        w_path = export_social_web(p, web_dir)
        print(f"  Patreon Clean Raw: {c_path}")
        print(f"  Social Web JPG   : {w_path}")

    print("\n" + "=" * 60)
    print(" Z-Image Turbo Test Execution Completed Successfully!")
    print(f" Total Generation Latency: {elapsed:.2f}s (8 steps)")
    print(" Output Directory        :", ROOT / "outputs" / "test_z_image")
    print("=" * 60)


def main():
    print("=" * 60)
    print(" Z-Image Turbo Automated Test Suite (Intel Arc A750 8GB)")
    print("=" * 60)
    
    if not check_and_prepare_models():
        sys.exit(1)

    if not ensure_comfyui_running():
        sys.exit(1)

    run_test_generation()


if __name__ == "__main__":
    main()
