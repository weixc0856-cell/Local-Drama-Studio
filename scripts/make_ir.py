r"""Generate a deterministic synthetic impulse response.

A measured IR for a real hall or water pavilion is a licensed asset. A synthetic
one costs nothing, is reproducible from a seed, and is enough for a first pass:
exponentially decaying noise plus a few early reflections is what a room IR looks
like to a convolver.

    .venv\Scripts\python.exe scripts\make_ir.py --out assets/audio/ir/synthetic_hall_0.9s.wav
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import wave
from pathlib import Path


def make_ir(path: Path, *, seconds: float = 0.9, sample_rate: int = 48000,
            seed: int = 7, rt60: float = 1.6,
            early: tuple[float, ...] = (0.011, 0.023, 0.037, 0.053)) -> dict:
    """Write a mono 16-bit IR: decaying noise with discrete early reflections."""
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    frames = int(round(seconds * sample_rate))
    rng = random.Random(seed)
    decay = math.log(1000.0) / max(1e-3, rt60)      # -60 dB after rt60

    samples = [0.0] * frames
    for index in range(frames):
        t = index / sample_rate
        envelope = math.exp(-decay * t / 6.9) * math.exp(-3.0 * t / seconds)
        # A slight low-pass: roll the noise off so the tail is air, not hiss.
        previous = samples[index - 1] if index else 0.0
        noise = rng.uniform(-1.0, 1.0)
        samples[index] = 0.55 * noise * envelope + 0.45 * previous

    for delay in early:
        position = int(round(delay * sample_rate))
        if position >= frames:
            continue
        gain = 0.45 * math.exp(-delay * 6.0)
        samples[position] += gain

    peak = max(1e-9, max(abs(value) for value in samples))
    scale = 0.89 / peak
    pcm = bytearray()
    for value in samples:
        pcm += int(max(-32768, min(32767, round(value * scale * 32767)))).to_bytes(
            2, "little", signed=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(pcm))

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = {
        "path": str(path), "sha256": digest, "seconds": seconds,
        "sample_rate": sample_rate, "seed": seed, "rt60": rt60,
        "early_reflections_s": list(early), "kind": "synthetic",
        "note": "合成 IR，无版权负担；不是实测空间，不得对外称录制混响",
    }
    path.with_suffix(".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic reverb IR")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seconds", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--rt60", type=float, default=1.6)
    args = parser.parse_args(argv)
    print(json.dumps(make_ir(Path(args.out), seconds=args.seconds, seed=args.seed,
                            rt60=args.rt60), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
