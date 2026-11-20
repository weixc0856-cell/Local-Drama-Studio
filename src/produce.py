#!/usr/bin/env python3
"""
src/produce.py
Local Drama Studio · Unified Production Pipeline Entry CLI

Capabilities:
1. Image Production (Automatic Pipeline Routing):
   - portrait | cinematic | editorial: Single-engine Z-Image Turbo (zero-LoRA candid realism)
   - industrial | aero | typography | poster: Dual-engine parallel run (Z-Image vs FLUX.3) + SBS comparison board
2. Video Production (Standardized Wan 14B Pipeline):
   - Wan 2.2-14B I2V (6-step LightX2V LoRA + 64GB DDR5 Block Swap)
   - Widescreen Guard: Auto-injects medium close-up & shallow DoF on 16:9 to avoid latent token dilution
   - Post-process: 2x Lanczos super-res to 2K + FFmpeg minterpolate 32fps optical flow interpolation
   - Commercial Audio Mux: Pure CPU Stable Audio Open 1.0 (BGM + Foley SFX) -> Master Audiovisual MP4
3. Physical Path Decoupling:
   - Output paths dynamically routed to output root (studio_data/ or configured via config/local-paths.yaml)

Usage:
  python src/produce.py image --project <id> --type portrait --prompt "..."
  python src/produce.py image --project <id> --type industrial --prompt "..."
  python src/produce.py video --project <id> --image <path> --aspect 9:16|16:9
  python src/produce.py status
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Root directory of this repository
REPO_ROOT = Path(__file__).resolve().parent.parent

# Load local path configuration
def load_paths_config() -> dict:
    cfg_file = REPO_ROOT / "config" / "local-paths.yaml"
    if not cfg_file.exists():
        cfg_file = REPO_ROOT / "config" / "local-paths.example.yaml"
    if cfg_file.exists():
        try:
            import yaml
            with open(cfg_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Warn] Failed to parse {cfg_file}: {e}")
    env_root = os.environ.get("DRAMA_OUTPUT_ROOT", str(REPO_ROOT / "studio_data"))
    return {"output_root": env_root}

PATHS_CFG = load_paths_config()
OUTPUT_ROOT = Path(PATHS_CFG.get("output_root", os.environ.get("DRAMA_OUTPUT_ROOT", str(REPO_ROOT / "studio_data"))))

PROJECTS_DIR = OUTPUT_ROOT / "projects"
BUILD_DIR = OUTPUT_ROOT / "build"
DELIVER_DIR = OUTPUT_ROOT / "deliver"

# Ensure core output layout exists
for p in (PROJECTS_DIR, BUILD_DIR, DELIVER_DIR):
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

COMFY_URL = PATHS_CFG.get("endpoints", {}).get("comfyui", "http://127.0.0.1:8188")
COMFY_INPUT = REPO_ROOT / "runtime" / "ComfyUI" / "input"
COMFY_OUTPUT = REPO_ROOT / "runtime" / "ComfyUI" / "output"

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def check_comfy_live() -> bool:
    """Check whether ComfyUI server is currently reachable."""
    try:
        req = urllib.request.Request(f"{COMFY_URL}/system_stats")
        with OPENER.open(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def submit_workflow(workflow_dict: dict) -> str:
    """Submit prompt workflow to ComfyUI /prompt endpoint."""
    payload = json.dumps({"prompt": workflow_dict}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with OPENER.open(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["prompt_id"]


def wait_for_completion(prompt_id: str, timeout: int = 1800, poll_interval: float = 3.0) -> dict:
    """Poll ComfyUI /history endpoint until prompt_id is done."""
    print(f"[*] Awaiting ComfyUI prompt ID: {prompt_id}...")
    t0 = time.time()
    last_print = t0
    while time.time() - t0 < timeout:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            with OPENER.open(req, timeout=10) as resp:
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
                    print(f"[+] Task {prompt_id} completed successfully in {elapsed:.1f}s")
                    return res
        except urllib.error.URLError:
            pass

        now = time.time()
        if now - last_print >= 15:
            print(f"    ... inference in progress ({int(now - t0)}s elapsed) ...", flush=True)
            last_print = now
        time.sleep(poll_interval)
    raise TimeoutError(f"Prompt {prompt_id} exceeded timeout of {timeout}s")


def retrieve_output_images(history_data: dict) -> list[Path]:
    """Retrieve output images from history data."""
    images = []
    outputs = history_data.get("outputs", {})
    for node_id, node_out in outputs.items():
        if "images" in node_out:
            for item in node_out["images"]:
                fname = item["filename"]
                subfolder = item.get("subfolder", "")
                fpath = COMFY_OUTPUT / subfolder / fname
                if fpath.exists():
                    images.append(fpath)
    return sorted(images)


# ==============================================================================
# 1. Image Production Module
# ==============================================================================
def produce_z_image_turbo(prompt: str, width: int, height: int, seed: int, prefix: str) -> Path:
    """Generate image via Z-Image Turbo 6B distilled native workflow."""
    wf_template = REPO_ROOT / "workflows" / "z_image_turbo_api.json"
    if not wf_template.exists():
        raise FileNotFoundError(f"Workflow {wf_template} not found")

    raw_str = wf_template.read_text(encoding="utf-8")
    subs = {
        "{{positive_prompt}}": prompt,
        "{{width}}": str(width),
        "{{height}}": str(height),
        "{{seed}}": str(seed),
        "{{steps}}": "8",
        "{{cfg}}": "1.0",
        "{{sampler_name}}": "euler",
        "{{scheduler}}": "simple",
        "{{filename_prefix}}": prefix,
    }
    for k, v in subs.items():
        raw_str = raw_str.replace(k, v)

    wf = json.loads(raw_str)
    pid = submit_workflow(wf)
    hist = wait_for_completion(pid)
    imgs = retrieve_output_images(hist)
    if not imgs:
        raise RuntimeError("No output images returned from Z-Image Turbo")
    return imgs[-1]


def produce_flux3_klein(prompt: str, width: int, height: int, seed: int, prefix: str) -> Path:
    """Generate image via FLUX.3 Klein distilled workflow."""
    wf_template = REPO_ROOT / "workflows" / "flux3_klein_api.json"
    if not wf_template.exists():
        wf_template = REPO_ROOT / "workflows" / "flux3_lora_t2i_api.json"
    raw_str = wf_template.read_text(encoding="utf-8")
    subs = {
        "{{positive_prompt}}": prompt,
        "{{negative_prompt}}": "low quality, blurry, distorted",
        "{{width}}": str(width),
        "{{height}}": str(height),
        "{{seed}}": str(seed),
        "{{steps}}": "16",
        "{{cfg}}": "1.0",
        "{{sampler_name}}": "er_sde",
        "{{scheduler}}": "simple",
        "{{filename_prefix}}": prefix,
    }
    for k, v in subs.items():
        raw_str = raw_str.replace(k, v)

    wf = json.loads(raw_str)
    pid = submit_workflow(wf)
    hist = wait_for_completion(pid)
    imgs = retrieve_output_images(hist)
    if not imgs:
        raise RuntimeError("No output images returned from FLUX.3 Klein")
    return imgs[-1]


def create_sbs_comparison_board(left_img_path: Path, right_img_path: Path, out_path: Path,
                                title_left: str = "Engine A: Z-Image Turbo",
                                title_right: str = "Engine B: FLUX.3 Klein",
                                prompt_text: str = ""):
    """Create a standardized side-by-side comparison board."""
    im_a = Image.open(left_img_path)
    im_b = Image.open(right_img_path)

    w, h = im_a.size
    banner_h = 100
    footer_h = 60
    total_w = w * 2 + 30
    total_h = h + banner_h + footer_h

    canvas = Image.new("RGB", (total_w, total_h), (20, 22, 26))
    draw = ImageDraw.Draw(canvas)

    # Header banner
    draw.rectangle([(0, 0), (total_w, banner_h)], fill=(28, 32, 38))
    draw.text((30, 20), "Local Drama Studio · Dual Engine Architectural AB Comparison Board", fill=(240, 240, 240))
    draw.text((30, 55), f"Task Type Evaluation | Left: {title_left} | Right: {title_right}", fill=(180, 190, 205))

    # Paste images
    canvas.paste(im_a, (10, banner_h + 10))
    canvas.paste(im_b, (w + 20, banner_h + 10))

    # Footer
    draw.rectangle([(0, total_h - footer_h), (total_w, total_h)], fill=(16, 18, 22))
    snippet = prompt_text[:120] + "..." if len(prompt_text) > 120 else prompt_text
    draw.text((20, total_h - 40), f"Prompt: {snippet}", fill=(150, 160, 175))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=95)
    print(f"[SBS] Comparison board saved -> {out_path.name}")


def handle_image_production(args):
    """Execute image production routing."""
    project_id = args.project
    task_type = args.type.lower()
    prompt = args.prompt
    width = args.width
    height = args.height
    seed = args.seed if args.seed is not None else int(time.time()) % 1000000

    proj_dir = PROJECTS_DIR / project_id
    build_proj = BUILD_DIR / project_id
    deliver_proj = DELIVER_DIR / project_id
    for d in (proj_dir, build_proj, deliver_proj):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f" Production Image Task · Project: {project_id} | Type: {task_type.upper()}")
    print("=" * 70)

    # 1. Portrait / Cinematic / Editorial -> Single Engine Z-Image Turbo
    if task_type in ("portrait", "cinematic", "editorial"):
        print(f"[Route] Single-Engine Selected: Z-Image Turbo (6B DiT Native Realism)")
        prefix = f"{project_id}_{task_type}_z_image"
        img_path = produce_z_image_turbo(prompt, width, height, seed, prefix)

        # Deliverable
        dest_build = build_proj / f"{prefix}_{seed}.png"
        dest_deliver = deliver_proj / f"{prefix}_deliver.png"
        shutil.copy(img_path, dest_build)
        shutil.copy(img_path, dest_deliver)
        print(f"\n[+] Production Completed!")
        print(f"    Build Artifact:   {dest_build}")
        print(f"    Deliver Artifact: {dest_deliver}")

    # 2. Industrial / Aero / Typography / Poster -> Dual Engine AB Compare
    elif task_type in ("industrial", "aero", "typography", "poster"):
        print(f"[Route] Dual-Engine Compare Selected: Z-Image Turbo vs FLUX.3 Klein")
        compare_build = build_proj / "compare"
        compare_build.mkdir(parents=True, exist_ok=True)

        prefix_z = f"{project_id}_{task_type}_zimage"
        prefix_f = f"{project_id}_{task_type}_flux3"

        print("\n[*] Engine 1/2: Generating Z-Image Turbo native...")
        img_z = produce_z_image_turbo(prompt, width, height, seed, prefix_z)
        saved_z = compare_build / f"{prefix_z}.png"
        shutil.copy(img_z, saved_z)

        print("\n[*] Engine 2/2: Generating FLUX.3 Klein (distilled)...")
        # Ensure semantic expansion for FLUX.3 to avoid short prompt drop
        flux_prompt = prompt
        if len(prompt.split()) < 15:
            flux_prompt += ", professional studio lighting, highly detailed, masterwork, sharp focus"
        img_f = produce_flux3_klein(flux_prompt, width, height, seed, prefix_f)
        saved_f = compare_build / f"{prefix_f}.png"
        shutil.copy(img_f, saved_f)

        sbs_path = deliver_proj / f"{project_id}_{task_type}_sbs_comparison.png"
        create_sbs_comparison_board(
            saved_z, saved_f, sbs_path,
            title_left="Z-Image Turbo (Native 6B DiT)",
            title_right="FLUX.3 Klein (16-step Distilled)",
            prompt_text=prompt
        )
        print(f"\n[+] Dual Engine AB Comparison Completed!")
        print(f"    Engine A:    {saved_z}")
        print(f"    Engine B:    {saved_f}")
        print(f"    Deliver SBS: {sbs_path}")

    else:
        print(f"[Route] Default fallback to Z-Image Turbo for {task_type}")
        prefix = f"{project_id}_{task_type}"
        img_path = produce_z_image_turbo(prompt, width, height, seed, prefix)
        dest_deliver = deliver_proj / f"{prefix}_deliver.png"
        shutil.copy(img_path, dest_deliver)
        print(f"[+] Delivered: {dest_deliver}")


# ==============================================================================
# 2. Video Production Module (Wan 14B + Widescreen Guard + Audio Mux)
# ==============================================================================
def handle_video_production(args):
    """Execute video production with Wan 14B and widescreen protection."""
    project_id = args.project
    anchor_image_path = Path(args.image)
    aspect = args.aspect.strip()
    prompt = args.prompt or "cinematic movie scene, subtle natural motion, photorealistic film grain, 35mm photography"

    if not anchor_image_path.exists():
        raise FileNotFoundError(f"Anchor image not found: {anchor_image_path}")

    build_proj = BUILD_DIR / project_id
    deliver_proj = DELIVER_DIR / project_id
    for d in (build_proj, deliver_proj):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f" Production Video Task · Project: {project_id} | Aspect: {aspect}")
    print("=" * 70)

    # Widescreen Guard & Dimensioning
    if aspect == "16:9":
        raw_w, raw_h = 832, 480
        post_w, post_h = 1664, 960
        print("[Widescreen Guard] Applying 16:9 widescreen token protection:")
        print("  - Target native resolution: 832x480 (Upscaled to 1664x960 2K)")
        # Enforce medium close-up and shallow DoF to avoid token dilution
        guard_modifiers = "medium close-up, waist-up composition, cinematic shallow depth of field, creamy bokeh, softly blurred background"
        if "close-up" not in prompt.lower() and "bokeh" not in prompt.lower():
            prompt = f"{prompt}, {guard_modifiers}"
            print(f"  - Auto-injected prompt modifiers: {guard_modifiers}")
    else:  # 9:16 vertical
        raw_w, raw_h = 480, 832
        post_w, post_h = 960, 1664
        print("[Aspect] 9:16 vertical portrait mode selected: 480x832 (Upscaled to 960x1664 2K)")

    # Prepare anchor keyframe inside ComfyUI input
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    comfy_anchor = COMFY_INPUT / f"{project_id}_anchor_{raw_w}x{raw_h}.png"
    im = Image.open(anchor_image_path)
    im_resized = im.resize((raw_w, raw_h), Image.Resampling.LANCZOS)
    im_resized.save(comfy_anchor)
    print(f"[Anchor] Keyframe prepared -> {comfy_anchor.name} ({raw_w}x{raw_h})")

    # Workflow submission
    wf_template = REPO_ROOT / "workflows" / "wan22_14b_i2v_api.json"
    if not wf_template.exists():
        raise FileNotFoundError(f"Workflow template {wf_template} not found")

    raw_str = wf_template.read_text(encoding="utf-8")
    subs = {
        "{{positive_prompt}}": prompt,
        "{{negative_prompt}}": "blur, distort, low quality, erratic jerking",
        "{{input_image}}": comfy_anchor.name,
        "{{width}}": str(raw_w),
        "{{height}}": str(raw_h),
        "{{frames}}": "49",
        "{{seed}}": str(int(time.time()) % 1000000),
        "{{steps}}": "6",
        "{{cfg}}": "1.0",
        "{{shift}}": "5.0",
        "{{filename_prefix}}": f"{project_id}_wan14b",
    }
    for k, v in subs.items():
        raw_str = raw_str.replace(k, v)

    wf = json.loads(raw_str)
    pid = submit_workflow(wf)
    hist = wait_for_completion(pid, timeout=3600)
    frames = retrieve_output_images(hist)
    if not frames:
        raise RuntimeError("No frames produced by Wan 14B workflow")

    print(f"\n[+] Extracted {len(frames)} frames from ComfyUI.")

    # Assembly & Super-Resolution with FFmpeg
    raw_mp4 = build_proj / f"{project_id}_raw_16fps.mp4"
    post_mp4 = deliver_proj / f"{project_id}_32fps_2k.mp4"

    temp_seq = build_proj / "temp_seq"
    if temp_seq.exists():
        shutil.rmtree(temp_seq)
    temp_seq.mkdir(parents=True, exist_ok=True)

    for idx, f in enumerate(frames):
        shutil.copy(f, temp_seq / f"frame_{idx:05d}.png")

    # 1. Raw 16fps
    cmd_raw = [
        "ffmpeg", "-y", "-framerate", "16",
        "-i", str(temp_seq / "frame_%05d.png"),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(raw_mp4)
    ]
    subprocess.run(cmd_raw, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[FFmpeg] 16fps raw video assembled -> {raw_mp4.name}")

    # 2. 2x Lanczos Super-Res + 32fps Optical Flow Interpolation
    vf = f"scale={post_w}:{post_h}:flags=lanczos,minterpolate=fps=32:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    cmd_post = [
        "ffmpeg", "-y", "-i", str(raw_mp4),
        "-vf", vf, "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
        str(post_mp4)
    ]
    print(f"[FFmpeg] Processing 2x Lanczos Super-Res + 32fps optical flow interpolation...")
    subprocess.run(cmd_post, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[FFmpeg] Postprocessed 2K 32fps video delivered -> {post_mp4.name}")

    # 3. Audio Muxing (Commercial Permissive Dual Track)
    master_mp4 = deliver_proj / f"{project_id}_audiovisual_master.mp4"
    bgm_file = args.bgm
    if not bgm_file:
        # Default to benchmarked ambient soundtrack if available
        default_bgm = REPO_ROOT / "outputs" / "audio_benchmark" / "case01_drama_tokyo_rain_ambient.wav"
        if default_bgm.exists():
            bgm_file = str(default_bgm)

    if bgm_file and Path(bgm_file).exists():
        print(f"[Audio] Muxing commercial soundtrack: {Path(bgm_file).name}...")
        cmd_mux = [
            "ffmpeg", "-y",
            "-i", str(post_mp4),
            "-i", str(bgm_file),
            "-filter_complex", "[1:a]volume=0.7[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(master_mp4)
        ]
        subprocess.run(cmd_mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Final Audiovisual Master Video Created: {master_mp4.name}")
    else:
        master_mp4 = post_mp4

    print(f"\n[+] Video Pipeline Delivery Complete!")
    print(f"    Master Video: {master_mp4}")


# ==============================================================================
# 3. Status Reporting Module
# ==============================================================================
def handle_status():
    """Report repository architecture, paths and service status."""
    print("=" * 70)
    print(" Local Drama Studio · Standard Architecture Status")
    print("=" * 70)
    print(f"  Repository Root:     {REPO_ROOT}")
    print(f"  Physical Output Root:{OUTPUT_ROOT}")
    print(f"    - Projects:        {PROJECTS_DIR} (exists: {PROJECTS_DIR.exists()})")
    print(f"    - Build:           {BUILD_DIR} (exists: {BUILD_DIR.exists()})")
    print(f"    - Deliver:         {DELIVER_DIR} (exists: {DELIVER_DIR.exists()})")

    # Junction check
    junction = REPO_ROOT / "studio_data"
    print(f"  Junction Link:       {junction} (is_dir: {junction.exists()})")

    # ComfyUI check
    live = check_comfy_live()
    print(f"  ComfyUI Server:      {COMFY_URL} (Status: {'ONLINE' if live else 'OFFLINE'})")

    # Pipeline check
    pipe_cfg = REPO_ROOT / "config" / "pipelines.yaml"
    print(f"  Pipelines Config:    {pipe_cfg} (exists: {pipe_cfg.exists()})")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Local Drama Studio · Production Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: status
    subparsers.add_parser("status", help="Check system status and paths")

    # Subcommand: image
    p_img = subparsers.add_parser("image", help="Produce images with auto-routing")
    p_img.add_argument("--project", required=True, help="Project Identifier")
    p_img.add_argument("--type", required=True, choices=["portrait", "cinematic", "editorial", "industrial", "aero", "typography", "poster"], help="Task routing category")
    p_img.add_argument("--prompt", required=True, help="Prompt text")
    p_img.add_argument("--width", type=int, default=768, help="Image width (default 768)")
    p_img.add_argument("--height", type=int, default=1360, help="Image height (default 1360)")
    p_img.add_argument("--seed", type=int, default=None, help="Random seed")

    # Subcommand: video
    p_vid = subparsers.add_parser("video", help="Produce Wan 14B video from keyframe")
    p_vid.add_argument("--project", required=True, help="Project Identifier")
    p_vid.add_argument("--image", required=True, help="Path to anchor keyframe image")
    p_vid.add_argument("--aspect", required=True, choices=["9:16", "16:9"], help="Video aspect ratio")
    p_vid.add_argument("--prompt", default="", help="Optional video motion prompt")
    p_vid.add_argument("--bgm", default="", help="Optional background music file")

    args = parser.parse_args()

    if args.command == "status":
        handle_status()
    elif args.command == "image":
        handle_image_production(args)
    elif args.command == "video":
        handle_video_production(args)


if __name__ == "__main__":
    main()
