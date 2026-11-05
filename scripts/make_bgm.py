"""Rebuild the four self-generated BGM beds.

These are deliberately simple, deterministic FFmpeg graphs: pentatonic sine
layers plus a quiet pink-noise texture, slow tremolo, band limits, fades and
two-pass loudness normalization to about -26 LUFS. They contain no third-party
samples. The WAV files are local-only by repository rule; the manifest keeps
their SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {result.stderr[-2000:]}")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as fh:
        return round(fh.getnframes() / fh.getframerate() * 1000)


def build(out_dir: Path) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = {
        "ink_serene_60s.wav": {
            "freqs": [110, 164.81, 220],
            "noise": 0.015,
            "gains": [0.18, 0.10, 0.05],
            "tremolo": [0.10, 0.11, 0.13],
            "lowpass": 2400,
        },
        "court_elegant_60s.wav": {
            "freqs": [196, 293.66, 392, 587.33],
            "noise": 0.008,
            "gains": [0.14, 0.09, 0.06, 0.028],
            "tremolo": [0.16, 0.20, 0.12, 0.24],
            "lowpass": 4200,
        },
        "shinkai_piano_60s.wav": {
            "freqs": [261.63, 329.63, 392.0, 523.25],
            "noise": 0.006,
            "gains": [0.12, 0.08, 0.06, 0.035],
            "tremolo": [0.12, 0.15, 0.18, 0.22],
            "lowpass": 6000,
        },
        "ghibli_pastoral_60s.wav": {
            "freqs": [196.0, 246.94, 293.66, 392.0],
            "noise": 0.010,
            "gains": [0.12, 0.09, 0.07, 0.03],
            "tremolo": [0.14, 0.18, 0.16, 0.20],
            "lowpass": 5000,
        },
    }
    output = []
    for name, spec in specs.items():
        tmp = out_dir / f".{name}.tmp.wav"
        target = out_dir / name
        inputs: list[str] = []
        filters: list[str] = []
        labels: list[str] = []
        for index, (freq, gain, trem) in enumerate(zip(spec["freqs"], spec["gains"], spec["tremolo"])):
            inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration=60"]
            filters.append(f"[{index}:a]volume={gain},tremolo=f={trem}:d=0.20[a{index}]")
            labels.append(f"[a{index}]")
        noise_index = len(spec["freqs"])
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:duration=60:amplitude={spec['noise']}:seed=20261104"]
        filters.append(f"[{noise_index}:a]highpass=f=120,lowpass=f=900,volume=0.05[anoise]")
        labels.append("[anoise]")
        filters.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
            "highpass=f=70,equalizer=f=180:t=q:w=1.5:g=-3,"
            "equalizer=f=4200:t=q:w=2.0:g=-4,"
            f"lowpass=f={spec['lowpass']},afftdn=nf=-30,"
            "afade=t=in:st=0:d=3,afade=t=out:st=57:d=3,alimiter=limit=0.85[out]"
        )
        _run([
            "ffmpeg", "-y", "-v", "error", *inputs,
            "-filter_complex", ";".join(filters), "-map", "[out]",
            "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(tmp),
        ])
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(tmp),
            "-af", "loudnorm=I=-26:TP=-3:LRA=7", "-ac", "1", "-ar", "48000",
            "-c:a", "pcm_s16le", str(target),
        ])
        tmp.unlink(missing_ok=True)
        output.append({"path": str(target), "sha256": _sha(target), "duration_ms": _duration_ms(target)})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild self-generated BGM beds")
    parser.add_argument("--out-dir", default="assets/audio/bgm")
    args = parser.parse_args()
    print(json.dumps(build(Path(args.out_dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
