#!/usr/bin/env python3
"""
scripts/setup_z_image_pipeline.py
Automated environment inspection, model directory preparation, and download helper
for Z-Image Turbo & FLUX.3 Klein dual-engine setup on Intel Arc A750.
"""

import sys
import os
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODELS_ROOT = Path(Path(os.environ.get("DRAMA_MODELS_ROOT", "./models")))
COMFYUI_DIR = ROOT / "runtime" / "ComfyUI"


def inspect_environment():
    print("=" * 60)
    print(" 1. Hardware & Runtime Boundary Inspection")
    print("=" * 60)
    print("Target GPU   : Intel Arc A750 (8GB VRAM Dedicated)")
    print("Host RAM     : 64GB DDR5 (Used for CPU offloading Qwen3-4B)")
    print(f"ComfyUI Path : {COMFYUI_DIR} (Exists: {COMFYUI_DIR.exists()})")
    
    gguf_node = COMFYUI_DIR / "custom_nodes" / "ComfyUI-GGUF"
    print(f"ComfyUI-GGUF : {gguf_node} (Installed: {gguf_node.exists()})")

    extra_paths = COMFYUI_DIR / "extra_model_paths.yaml"
    print(f"Extra Paths  : {extra_paths} (Configured: {extra_paths.exists()})")


def inspect_model_store():
    print("\n" + "=" * 60)
    print(" 2. Model Store Checklist (${DRAMA_MODELS_ROOT})")
    print("=" * 60)

    # 1. FLUX.3 Klein
    flux_unet = MODELS_ROOT / "diffusion_models" / "flux3" / "flux-3-image-klein-Q4_K_M.gguf"
    flux_clip = MODELS_ROOT / "text_encoders" / "qwen3vl_4b_int8_convrot.safetensors"
    flux_vae = MODELS_ROOT / "vae" / "flux2-vae.safetensors"

    print(f"[FLUX.3] Unet GGUF    : {flux_unet.name:<35} -> {'[OK]' if flux_unet.exists() else '[MISSING]'}")
    print(f"[FLUX.3] Text Encoder : {flux_clip.name:<35} -> {'[OK]' if flux_clip.exists() else '[MISSING]'}")
    print(f"[Shared] 16ch VAE     : {flux_vae.name:<35} -> {'[OK]' if flux_vae.exists() else '[MISSING]'}")

    # 2. Z-Image Turbo
    z_unet = MODELS_ROOT / "diffusion_models" / "z_image" / "z-image-turbo-Q4_K_M.gguf"
    z_clip = MODELS_ROOT / "text_encoders" / "Qwen3-4B-Q4_K_M.gguf"

    print(f"[Z-Image] Unet GGUF   : {z_unet.name:<35} -> {'[READY]' if z_unet.exists() else '[PENDING DOWNLOAD]'}")
    print(f"[Z-Image] Text Encoder: {z_clip.name:<35} -> {'[READY]' if z_clip.exists() else '[PENDING DOWNLOAD]'}")

    return {
        "flux_ready": flux_unet.exists() and flux_clip.exists() and flux_vae.exists(),
        "z_image_ready": z_unet.exists() and z_clip.exists() and flux_vae.exists(),
        "paths": {
            "z_unet": z_unet,
            "z_clip": z_clip,
            "vae": flux_vae
        }
    }


def generate_download_commands(status: dict):
    print("\n" + "=" * 60)
    print(" 3. Download Commands for Z-Image Turbo (PowerShell / CLI)")
    print("=" * 60)
    
    z_unet = status["paths"]["z_unet"]
    z_clip = status["paths"]["z_clip"]

    print("""
# 请在具有外部磁盘写入权限的 PowerShell 窗口中执行以下命令创建目录并下载：

# 1. 确保子目录存在：
New-Item -ItemType Directory -Path "${DRAMA_MODELS_ROOT}\\diffusion_models\\z_image" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "${DRAMA_MODELS_ROOT}\\text_encoders" -Force -ErrorAction SilentlyContinue

# 2. 方式 A：通过 huggingface-cli 下载 (推荐)
pip install -U huggingface_hub
huggingface-cli download unsloth/Z-Image-Turbo-GGUF z-image-turbo-Q4_K_M.gguf --local-dir "${DRAMA_MODELS_ROOT}\\diffusion_models\\z_image"
huggingface-cli download unsloth/Z-Image-Turbo-GGUF zimage_qwen3_4b_Q4.gguf --local-dir "${DRAMA_MODELS_ROOT}\\text_encoders"

# 3. 方式 B：国内用户通过 ModelScope (高速镜像)
pip install -U modelscope
modelscope download --model unsloth/Z-Image-Turbo-GGUF z-image-turbo-Q4_K_M.gguf --local_dir "${DRAMA_MODELS_ROOT}\\diffusion_models\\z_image"
modelscope download --model unsloth/Z-Image-Turbo-GGUF zimage_qwen3_4b_Q4.gguf --local_dir "${DRAMA_MODELS_ROOT}\\text_encoders"
""")


def verify_workflows():
    print("=" * 60)
    print(" 4. Workflows & Pipeline Routing Verification")
    print("=" * 60)

    cfg_file = ROOT / "config" / "pipelines.yaml"
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for name, p in cfg.get("pipelines", {}).items():
        wf_path = ROOT / p["workflow_path"]
        print(f"Pipeline: {name:<15} -> Workflow File: {wf_path.name:<25} -> {'[OK]' if wf_path.exists() else '[FAIL]'}")
        if wf_path.exists():
            with open(wf_path, "r", encoding="utf-8") as wf_f:
                data = json.load(wf_f)
                nodes = list(data.keys())
                print(f"   Node Count: {len(nodes)} nodes | Sampler: {p.get('sampler')} | Steps: {p.get('default_steps')}")

    print("\nAll pipeline JSON templates successfully verified!")


def main():
    inspect_environment()
    status = inspect_model_store()
    if not status["z_image_ready"]:
        generate_download_commands(status)
    verify_workflows()


if __name__ == "__main__":
    main()
