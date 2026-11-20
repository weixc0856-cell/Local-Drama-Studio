#!/usr/bin/env python3
"""
scripts/generator.py
Dual-Engine Production Image Generator for Local-Drama-Studio.
Routes between FLUX.3 Klein and Z-Image Turbo using config/pipelines.yaml.
Designed for 8GB VRAM (Intel Arc A750) + 64GB DDR5 host memory.
"""

import os
import sys
import json
import time
import re
import argparse
import urllib.request
import urllib.error
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "pipelines.yaml"
BASE_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing pipeline config: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def detect_engine(prompt: str, config: dict) -> str:
    """Auto-detect pipeline based on prompt keywords."""
    prompt_lower = prompt.lower()
    rules = config.get("auto_routing_rules", {})
    
    # Check Z-Image Turbo keywords
    z_keywords = rules.get("z_image_turbo_keywords", [])
    for kw in z_keywords:
        if kw.lower() in prompt_lower:
            return "z_image_turbo"
            
    # Check FLUX.3 Klein keywords
    f_keywords = rules.get("flux3_klein_keywords", [])
    for kw in f_keywords:
        if kw.lower() in prompt_lower:
            return "flux3_klein"
            
    # Default fallback
    return "z_image_turbo"


def fill_workflow(template: dict, values: dict) -> dict:
    """Recursively fill {{key}} placeholders in ComfyUI API JSON."""
    result = {}
    for k, v in template.items():
        if isinstance(v, dict):
            result[k] = fill_workflow(v, values)
        elif isinstance(v, list):
            result[k] = [
                fill_workflow(item, values) if isinstance(item, dict) else item
                for item in v
            ]
        elif isinstance(v, str):
            match = PLACEHOLDER.match(v)
            if match:
                key = match.group(1)
                result[k] = values.get(key, v)
            else:
                out = v
                for rk, rv in values.items():
                    out = out.replace(f"{{{{{rk}}}}}", str(rv))
                result[k] = out
        else:
            result[k] = v
    return result


def queue_prompt(prompt_workflow: dict) -> str:
    """Submit prompt to ComfyUI and return prompt_id."""
    payload = json.dumps({"prompt": prompt_workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with OPENER.open(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["prompt_id"]


def wait_for_completion(prompt_id: str, timeout: int = 600) -> list[str]:
    """Poll ComfyUI history until prompt completes, then return output image filenames."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            req = urllib.request.Request(f"{BASE_URL}/history/{prompt_id}")
            with OPENER.open(req) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
                if prompt_id in hist:
                    entry = hist[prompt_id]
                    status = entry.get("status", {})
                    if status.get("completed", False) or status.get("status_str") == "success":
                        filenames = []
                        for node_id, node_output in entry.get("outputs", {}).items():
                            for img in node_output.get("images", []):
                                filenames.append(img["filename"])
                        return filenames
                    if status.get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI execution error: {entry.get('status')}")
        except urllib.error.URLError:
            pass
        time.sleep(1.0)
    raise TimeoutError(f"Generation timed out after {timeout} seconds (prompt {prompt_id}).")


def download_image(filename: str, dest_path: Path):
    """Download generated image from ComfyUI view endpoint."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/view?filename={urllib.request.quote(filename)}&type=output"
    with OPENER.open(url) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())


def run_generation(
    engine: str,
    prompt: str,
    seed: int,
    batch_count: int = 1,
    output_dir: Path = None,
    overrides: dict = None,
) -> list[Path]:
    """Execute generation on the chosen pipeline engine."""
    config = load_config()
    pipelines = config.get("pipelines", {})
    
    if engine == "auto":
        engine = detect_engine(prompt, config)
        print(f"[Generator] Auto-detected pipeline: {engine}")

    if engine not in pipelines:
        raise ValueError(f"Unknown engine '{engine}'. Available: {list(pipelines.keys())}")

    pcfg = pipelines[engine]
    wf_path = ROOT / pcfg["workflow_path"]
    if not wf_path.exists():
        raise FileNotFoundError(f"Workflow file missing: {wf_path}")

    with open(wf_path, "r", encoding="utf-8") as f:
        wf_template = json.load(f)

    # Base parameters from config
    params = {
        "positive_prompt": prompt,
        "width": pcfg.get("default_width", 768),
        "height": pcfg.get("default_height", 1360),
        "steps": pcfg.get("default_steps", 8),
        "cfg": pcfg.get("default_cfg", 1.0),
        "sampler_name": pcfg.get("sampler", "euler"),
        "scheduler": pcfg.get("scheduler", "simple"),
        "lora_name": pcfg.get("default_lora", ""),
        "lora_strength": pcfg.get("lora_strength", 0.0),
    }

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                params[k] = v

    # Dynamic workflow selection for FLUX.3: choose LoRA workflow only when LoRA is active
    if engine == "flux3_klein":
        has_lora = bool(params.get("lora_name")) and float(params.get("lora_strength", 0.0)) > 0.0
        if has_lora:
            wf_path = ROOT / "workflows" / "flux3_klein_lora_api.json"
        else:
            wf_path = ROOT / "workflows" / "flux3_klein_api.json"
        with open(wf_path, "r", encoding="utf-8") as f:
            wf_template = json.load(f)

    if output_dir is None:
        output_dir = ROOT / "outputs" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    print(f"\n==========================================")
    print(f"Engine      : {pcfg['name']}")
    print(f"Steps / CFG : {params['steps']} / {params['cfg']}")
    print(f"Sampler     : {params['sampler_name']} + {params['scheduler']}")
    print(f"Resolution  : {params['width']}x{params['height']}")
    print(f"LoRA        : {params['lora_name']} ({params['lora_strength']})")
    print(f"Output Dir  : {output_dir}")
    print(f"==========================================\n")

    for i in range(batch_count):
        current_seed = seed + i
        params["seed"] = current_seed
        params["filename_prefix"] = f"{engine}_{current_seed}"
        
        filled = fill_workflow(wf_template, params)
        print(f"[{i+1}/{batch_count}] Submitting seed {current_seed}...")
        prompt_id = queue_prompt(filled)
        print(f"     Queued prompt ID: {prompt_id}. Waiting for completion...")
        
        out_filenames = wait_for_completion(prompt_id)
        for fname in out_filenames:
            dest = output_dir / f"{engine}_{current_seed}_{fname}"
            download_image(fname, dest)
            print(f"     Saved: {dest}")
            generated_files.append(dest)

    return generated_files


def main():
    parser = argparse.ArgumentParser(description="Drama Studio Multi-Engine Image Generator")
    parser.add_argument("--engine", choices=["flux3_klein", "z_image_turbo", "auto"], default="auto",
                        help="Engine pipeline to use (default: auto)")
    parser.add_argument("--prompt", type=str, help="Text prompt")
    parser.add_argument("--prompt-file", type=str, help="Path to text file containing prompt")
    parser.add_argument("--seed", type=int, default=int(time.time()), help="Random seed")
    parser.add_argument("--batch", type=int, default=1, help="Number of images to generate")
    parser.add_argument("--steps", type=int, default=None, help="Override steps")
    parser.add_argument("--cfg", type=float, default=None, help="Override CFG")
    parser.add_argument("--width", type=int, default=None, help="Override width")
    parser.add_argument("--height", type=int, default=None, help="Override height")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    prompt_text = ""
    if args.prompt:
        prompt_text = args.prompt
    elif args.prompt_file:
        pf = Path(args.prompt_file)
        if not pf.exists():
            print(f"Error: Prompt file not found: {pf}", file=sys.stderr)
            sys.exit(1)
        prompt_text = pf.read_text(encoding="utf-8").strip()
    else:
        print("Error: Either --prompt or --prompt-file must be provided.", file=sys.stderr)
        sys.exit(1)

    overrides = {
        "steps": args.steps,
        "cfg": args.cfg,
        "width": args.width,
        "height": args.height,
    }

    out_dir = Path(args.outdir) if args.outdir else ROOT / "outputs" / "raw"
    run_generation(
        engine=args.engine,
        prompt=prompt_text,
        seed=args.seed,
        batch_count=args.batch,
        output_dir=out_dir,
        overrides=overrides
    )


if __name__ == "__main__":
    main()
