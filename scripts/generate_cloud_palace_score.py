#!/usr/bin/env python3
"""scripts/generate_cloud_palace_score.py
Original ambient orchestral score for 「云上天宫」, generated on CPU.

Engine: Stable Audio Open 1.0 (Stability Community License, commercial-free under $1M).
Runs on CPU so it never contends with the A750 while Wan is rendering.

Must be run with the ComfyUI runtime interpreter, which has torch + diffusers:
  runtime\\ComfyUI\\.venv\\Scripts\\python.exe scripts/generate_cloud_palace_score.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402

from drama_studio.paths import output_root, repo_root  # noqa: E402

PROMPT = (
    "Serene cinematic Oriental orchestral ambient, slow sustained guqin plucks and breathy bamboo dizi flute, "
    "wide airy string pads, faint distant bronze bell, vast heavenly spacious atmosphere, "
    "slow gentle swell, no drums, no percussion beat, no vocals, instrumental, 48kHz high fidelity stereo"
)
NEGATIVE = "low quality, noisy, distorted, crackling, loud drums, sudden screaming, vocals, speech"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=18.0)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--out", help="Output WAV path")
    args = ap.parse_args()

    import torch
    import soundfile as sf
    from diffusers import StableAudioPipeline

    cfg_file = repo_root() / "config" / "local-paths.yaml"
    paths = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) if cfg_file.exists() else {}
    models_root = Path((paths.get("models") or {}).get("audio_models") or "models/audio")
    model_path = models_root / "stable-audio-open-1.0"
    if not model_path.exists():
        raise SystemExit(f"Stable Audio model not found at {model_path}")

    out = Path(args.out) if args.out else output_root() / "experiments" / "cloud_palace" / "deliver" / "score.wav"
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Score] Stable Audio Open 1.0 on CPU · {args.seconds}s · {args.steps} steps", flush=True)
    print(f"[Score] prompt: {PROMPT[:100]}...", flush=True)
    t0 = time.time()
    pipe = StableAudioPipeline.from_pretrained(str(model_path), torch_dtype=torch.float32)
    pipe = pipe.to("cpu")
    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    result = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE,
        num_inference_steps=args.steps,
        audio_end_in_s=args.seconds,
        num_waveforms_per_prompt=1,
        generator=generator,
    )
    audio = result.audios[0].T.float().cpu().numpy()
    sf.write(str(out), audio, pipe.vae.sampling_rate)
    elapsed = time.time() - t0
    print(f"[Score] wrote {out} ({elapsed / 60:.1f} min, {pipe.vae.sampling_rate} Hz)", flush=True)


if __name__ == "__main__":
    main()