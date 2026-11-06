"""POC: local Qwen as the FLUX.3 prompt upsampler (no 9B, no GPU).

Uses the OFFICIAL Black Forest Labs `t2i` system prompt from
`config/upsampler/system_prompts.json` (downloaded unmodified from
black-forest-labs/flux-3-image-klein-pup), plus a style addendum that turns
our composition contract into concrete spatial instructions.

This script only produces captions and timing. It never calls ComfyUI.

    .venv\\Scripts\\python.exe scripts\\poc_upsampler.py ^
        --shots experiments/flux3_poc/params ^
        --out experiments/flux3_poc/captions

The local llama-server must already be running on 8080 (scripts/llm_server.ps1).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "config" / "styles.yaml"
SYSTEM_PROMPTS = ROOT / "config" / "upsampler" / "system_prompts.json"

MEDIUM = {
    "ink_wash": (
        "raw xuan paper with visible fibre, diluted ink washes, dry-brush edges, "
        "gradations from pale grey to dense black, large unpainted areas"
    ),
    "court_green_fine_line": (
        "silk ground with fine even contour lines (iron-wire and gossamer strokes), "
        "flat mineral pigment washes, restrained crisp detail"
    ),
}
PALETTE = {
    "ink_wash": "ink black and grey with a few pale ochre accents; low saturation",
    "court_green_fine_line": (
        "azurite blue and malachite green as dominant hues, ochre and muted gold accents, "
        "pale silk ground; cool temperature, medium saturation"
    ),
}


def style_of(shot_id: str) -> str:
    return "court_green_fine_line" if shot_id.startswith("court") else "ink_wash"


def addendum(style: str) -> str:
    profile = yaml.safe_load(STYLES.read_text(encoding="utf-8"))["styles"][style]
    comp = profile.get("aesthetic_profile", {}).get("composition", {})
    low, high = comp.get("whitespace_range", [0.1, 0.35])
    position = comp.get("default_subject_position", "center")
    return f"""ADDITIONAL REQUIREMENTS FOR THIS IMAGE (apply every point inside the caption; never name these rules, never mention the canvas or ratio):

- The image is a tall vertical composition. Compose for height.
- Empty space: roughly {low:.0%} to {high:.0%} of the frame must be empty paper or empty sky. Name the empty regions explicitly in frame-relative terms (for example "the upper third is unmarked pale paper") and keep them free of subjects, ornament and texture patches.
- All surfaces are blank and unmarked: no calligraphy, no poetry, no seals, red stamps, signatures, watermarks, labels or frames anywhere in the image.
- Medium: {MEDIUM[style]}.
- Palette: {PALETTE[style]}.
- The main subject sits at {position} in the frame and is described with its size relative to the frame.
- Avoid photographic realism, 3D render, digital vector look, neon colour and heavy contrast."""


def build_messages(prompt: str, style: str) -> tuple[str, str]:
    official = json.loads(SYSTEM_PROMPTS.read_text(encoding="utf-8"))["t2i"]
    return official + "\n\n" + addendum(style), prompt


def upscale(client: httpx.Client, model: str, system: str, user: str,
            temperature: float, max_tokens: int) -> tuple[str, dict]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    started = time.perf_counter()
    response = client.post("/chat/completions", json=payload)
    response.raise_for_status()
    elapsed = time.perf_counter() - started
    data = response.json()
    caption = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    return caption, {
        "elapsed_seconds": round(elapsed, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "words": len(caption.split()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", required=True, help="directory of FLUX.3 params JSON")
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="Qwen3-30B-A3B-Instruct-2507")
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    shots_dir = (ROOT / args.shots).resolve()
    out_dir = (ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    with httpx.Client(base_url=args.base_url, timeout=httpx.Timeout(600.0), trust_env=False) as client:
        for path in sorted(shots_dir.glob("*.json")):
            shot_id = path.stem
            if args.only and shot_id not in args.only:
                continue
            params = json.loads(path.read_text(encoding="utf-8"))
            style = style_of(shot_id)
            system, user = build_messages(params["positive_prompt"], style)
            caption, meta = upscale(
                client, args.model, system, user, args.temperature, args.max_tokens
            )
            (out_dir / f"{shot_id}.txt").write_text(caption + "\n", encoding="utf-8")
            record = {"shot_id": shot_id, "style": style, "caption": caption, **meta}
            records.append(record)
            print(json.dumps({k: record[k] for k in ("shot_id", "style", "words", "elapsed_seconds")},
                             ensure_ascii=False))

    (out_dir / "captions.json").write_text(
        json.dumps({"model": args.model, "temperature": args.temperature, "captions": records},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
