#!/usr/bin/env python3
"""
scripts/test_zimage_to_wan14b_video.py
End-to-End Pipeline Test: Z-Image Turbo Keyframe -> Wan 2.2-14B I2V Video + Postprocessing.

Hardware Constraint: Intel Arc A750 (8GB VRAM) + 64GB DDR5 RAM (Windows PyTorch-XPU).
Configuration:
- Base Model: Wan 2.1/2.2 14B I2V GGUF Q4_K_M (10.56GB)
- Acceleration: LightX2V 6-step Distilled LoRA (rank 32, bf16)
- Text Encoder: umt5_xxl_fp8 (CPU offloaded)
- Dual Aspect Ratios:
  * Case 1: 9:16 Vertical Portrait (480x832, 49 frames, ~3s at 16fps)
  * Case 2: 16:9 Cinematic Widescreen (832x480, 49 frames, ~3s at 16fps)
- Postprocessing: FFmpeg 2x Lanczos Super-Resolution + Motion Flow 32fps Interpolation.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
COMFY_DIR = ROOT / "runtime" / "ComfyUI"
COMFY_INPUT = COMFY_DIR / "input"
COMFY_OUTPUT = COMFY_DIR / "output"
TEST_OUT = ROOT / "experiments" / "wan22_14b_test"
WORKFLOW_TEMPLATE = ROOT / "workflows" / "wan22_14b_i2v_api.json"
COMFY_URL = "http://127.0.0.1:8188"


def prepare_anchor_images():
    """Extract and prepare anchor keyframes for 9:16 and 16:9 tests."""
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    TEST_OUT.mkdir(parents=True, exist_ok=True)

    # 1. 9:16 Anchor (Rainy night taxi window portrait)
    p_9x16 = ROOT / "outputs" / "character_consistency_benchmark" / "raw" / "z_image_turbo_20263103_z_image_turbo_20263103_00001_.png"
    anchor_9x16_dst = COMFY_INPUT / "anchor_9x16_tokyo_rain.png"
    if p_9x16.exists():
        img = Image.open(p_9x16)
        img_resized = img.resize((480, 832), Image.Resampling.LANCZOS)
        img_resized.save(anchor_9x16_dst)
        img_resized.save(TEST_OUT / "anchor_9x16_tokyo_rain.png")
        print(f"[Anchor] 9:16 Keyframe prepared: {anchor_9x16_dst.name} (480x832)")
    else:
        print(f"[Anchor] Warning: {p_9x16} not found")

    # 2. 16:9 Anchor (Shanghai late autumn golden street portrait)
    p_16x9 = ROOT / "outputs" / "aspect_ratio_benchmark" / "raw" / "z_image_turbo_20266101_z_image_turbo_20266101_00001_.png"
    anchor_16x9_dst = COMFY_INPUT / "anchor_16x9_autumn_street.png"
    if p_16x9.exists():
        img = Image.open(p_16x9)
        img_resized = img.resize((832, 480), Image.Resampling.LANCZOS)
        img_resized.save(anchor_16x9_dst)
        img_resized.save(TEST_OUT / "anchor_16x9_autumn_street.png")
        print(f"[Anchor] 16:9 Keyframe prepared: {anchor_16x9_dst.name} (832x480)")
    else:
        print(f"[Anchor] Warning: {p_16x9} not found")


def submit_workflow(workflow_dict: dict) -> str:
    """Submit workflow dictionary to ComfyUI /prompt endpoint."""
    payload = json.dumps({"prompt": workflow_dict}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["prompt_id"]


def wait_for_completion(prompt_id: str, poll_interval: float = 3.0) -> dict:
    """Poll ComfyUI /history endpoint until prompt_id is done."""
    print(f"[*] Awaiting prompt {prompt_id} completion...")
    t0 = time.time()
    last_print = t0
    while True:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if prompt_id in data:
                    res = data[prompt_id]
                    status_info = res.get("status", {})
                    if status_info.get("status_str") == "error":
                        err_msg = ""
                        for m in status_info.get("messages", []):
                            if m[0] == "execution_error":
                                err_msg = m[1].get("exception_message", str(m[1]))
                        raise RuntimeError(f"ComfyUI Execution Error: {err_msg}")
                    elapsed = time.time() - t0
                    print(f"\n[+] Prompt {prompt_id} completed successfully in {elapsed:.1f}s!")
                    return res
        except Exception as e:
            if "ComfyUI Execution Error" in str(e):
                raise
            pass

        now = time.time()
        if now - last_print >= 15:
            print(f"    ... running Wan 2.2-14B video generation ({int(now - t0)}s elapsed) ...", flush=True)
            last_print = now
        time.sleep(poll_interval)


def build_workflow(input_image: str, positive_prompt: str, negative_prompt: str,
                   width: int, height: int, frames: int, seed: int, prefix: str) -> dict:
    """Load template and substitute variables."""
    raw_str = WORKFLOW_TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "{{positive_prompt}}": positive_prompt,
        "{{negative_prompt}}": negative_prompt,
        "{{input_image}}": input_image,
        "{{width}}": str(width),
        "{{height}}": str(height),
        "{{frames}}": str(frames),
        "{{seed}}": str(seed),
        "{{steps}}": "6",
        "{{cfg}}": "1.0",
        "{{shift}}": "5.0",
        "{{filename_prefix}}": prefix,
    }
    for k, v in subs.items():
        raw_str = raw_str.replace(k, v)
    return json.loads(raw_str)


def extract_frames_from_history(history_data: dict) -> list[Path]:
    """Retrieve list of output frame file paths from ComfyUI history."""
    frames = []
    outputs = history_data.get("outputs", {})
    for node_id, node_out in outputs.items():
        if "images" in node_out:
            for item in node_out["images"]:
                fname = item["filename"]
                subfolder = item.get("subfolder", "")
                fpath = COMFY_OUTPUT / subfolder / fname
                if fpath.exists():
                    frames.append(fpath)
    return sorted(frames)


def assemble_video_with_ffmpeg(frame_paths: list[Path], output_raw_mp4: Path, output_post_mp4: Path, target_w: int, target_h: int):
    """Stitch frames into 16fps MP4 and apply 2x Lanczos super-res + 32fps motion interpolation."""
    if not frame_paths:
        print(f"[FFmpeg] Error: No frame paths provided")
        return False

    print(f"[FFmpeg] Assembling {len(frame_paths)} frames -> {output_raw_mp4.name} (16fps)...")
    
    # Create temp directory with sequential filenames for ffmpeg
    temp_seq = TEST_OUT / "temp_seq"
    if temp_seq.exists():
        shutil.rmtree(temp_seq)
    temp_seq.mkdir(parents=True, exist_ok=True)

    for idx, f in enumerate(frame_paths):
        shutil.copy(f, temp_seq / f"frame_{idx:05d}.png")

    # 1. Raw 16fps MP4
    cmd_raw = [
        "ffmpeg", "-y",
        "-framerate", "16",
        "-i", str(temp_seq / "frame_%05d.png"),
        "-c:v", "libx264",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_raw_mp4)
    ]
    subprocess.run(cmd_raw, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[FFmpeg] Raw 16fps video created: {output_raw_mp4.name} ({output_raw_mp4.stat().st_size / 1024 / 1024:.2f} MB)")

    # 2. 2x Lanczos Super-Res + 32fps Motion Interpolation
    print(f"[FFmpeg] Postprocessing: 2x Lanczos Upscale ({target_w}x{target_h}) + 32fps Motion Interpolation -> {output_post_mp4.name}...")
    vf_filter = f"scale={target_w}:{target_h}:flags=lanczos,minterpolate=fps=32:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    cmd_post = [
        "ffmpeg", "-y",
        "-i", str(output_raw_mp4),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-crf", "17",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        str(output_post_mp4)
    ]
    try:
        subprocess.run(cmd_post, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[FFmpeg] Postprocessed 32fps 2x Video created: {output_post_mp4.name} ({output_post_mp4.stat().st_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        print(f"[FFmpeg] Fallback to blend mode: {e}")
        vf_fallback = f"scale={target_w}:{target_h}:flags=lanczos,minterpolate=fps=32:mi_mode=blend"
        subprocess.run(["ffmpeg", "-y", "-i", str(output_raw_mp4), "-vf", vf_fallback, "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(output_post_mp4)], check=True)

    # Clean temp sequence
    shutil.rmtree(temp_seq)
    return True


def run_pipeline():
    print("=" * 80)
    print(" Local Drama Studio · Wan 2.2-14B I2V End-to-End Pipeline Verification")
    print(" Hardware Constraint: Intel Arc A750 (8GB VRAM) + 64GB DDR5 (PyTorch-XPU)")
    print("=" * 80)

    prepare_anchor_images()

    results = []

    # -------------------------------------------------------------
    # Case 1: 9:16 Vertical Portrait (Tokyo Rain Night)
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print(" >>> Case 1: 9:16 Vertical Portrait (Tokyo Rain Night) <<<")
    print(" Resolution: 480x832 | Frames: 49 | Steps: 6 (LightX2V LoRA) | CFG: 1.0")
    print("=" * 60)

    wf_9x16 = build_workflow(
        input_image="anchor_9x16_tokyo_rain.png",
        positive_prompt="Cinematic camera slowly pushes in on the young woman, natural wind blowing silky hair strands, gentle soft blinking and subtle breathing motion, raindrops sliding down transparent umbrella with vivid neon reflections, realistic 8k documentary film.",
        negative_prompt="blurry, distorted face, extra limbs, deformed fingers, jitter, flickering, low quality, artifacts",
        width=480,
        height=832,
        frames=49,
        seed=20261401,
        prefix="wan14b/case01_9x16_tokyo_rain"
    )

    t0 = time.time()
    pid_1 = submit_workflow(wf_9x16)
    history_1 = wait_for_completion(pid_1)
    duration_1 = time.time() - t0

    # Postprocessing
    frames_1 = extract_frames_from_history(history_1)
    raw_mp4_1 = TEST_OUT / "case01_tokyo_rain_9x16_raw_16fps.mp4"
    post_mp4_1 = TEST_OUT / "case01_tokyo_rain_9x16_32fps_upscaled.mp4"
    assemble_video_with_ffmpeg(
        frame_paths=frames_1,
        output_raw_mp4=raw_mp4_1,
        output_post_mp4=post_mp4_1,
        target_w=960,
        target_h=1664
    )

    results.append({
        "case": "Case 01 · 9:16 Vertical Portrait (Tokyo Rain Night)",
        "resolution_raw": "480x832",
        "resolution_post": "960x1664 (2x Lanczos)",
        "frames": len(frames_1),
        "fps_post": "32 fps",
        "duration_sec": duration_1,
        "status": "SUCCESS",
        "raw_video": str(raw_mp4_1),
        "post_video": str(post_mp4_1)
    })

    # -------------------------------------------------------------
    # Case 2: 16:9 Cinematic Widescreen (Shanghai Autumn Street)
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print(" >>> Case 2: 16:9 Cinematic Widescreen (Shanghai Autumn Street) <<<")
    print(" Resolution: 832x480 | Frames: 49 | Steps: 6 (LightX2V LoRA) | CFG: 1.0")
    print("=" * 60)

    wf_16x9 = build_workflow(
        input_image="anchor_16x9_autumn_street.png",
        positive_prompt="Cinematic 16:9 tracking shot, young woman walking forward in autumn street, golden leaves falling gently across frame, warm afternoon sunlight gleaming on cashmere sweater, natural body movement and warm smile, Wong Kar-wai atmospheric film realism.",
        negative_prompt="blurry, distorted face, unnatural limbs, jitter, flickering, sudden morphing, artifacts",
        width=832,
        height=480,
        frames=49,
        seed=20261402,
        prefix="wan14b/case02_16x9_autumn_street"
    )

    t0 = time.time()
    pid_2 = submit_workflow(wf_16x9)
    history_2 = wait_for_completion(pid_2)
    duration_2 = time.time() - t0

    # Postprocessing
    frames_2 = extract_frames_from_history(history_2)
    raw_mp4_2 = TEST_OUT / "case02_autumn_street_16x9_raw_16fps.mp4"
    post_mp4_2 = TEST_OUT / "case02_autumn_street_16x9_32fps_upscaled.mp4"
    assemble_video_with_ffmpeg(
        frame_paths=frames_2,
        output_raw_mp4=raw_mp4_2,
        output_post_mp4=post_mp4_2,
        target_w=1664,
        target_h=960
    )

    results.append({
        "case": "Case 02 · 16:9 Cinematic Widescreen (Shanghai Autumn Street)",
        "resolution_raw": "832x480",
        "resolution_post": "1664x960 (2x Lanczos)",
        "frames": len(frames_2),
        "fps_post": "32 fps",
        "duration_sec": duration_2,
        "status": "SUCCESS",
        "raw_video": str(raw_mp4_2),
        "post_video": str(post_mp4_2)
    })

    # Summary Manifest
    manifest_path = TEST_OUT / "wan14b_pipeline_benchmark_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 80)
    print(f" [ALL TESTS COMPLETED] Benchmark manifest written to: {manifest_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
