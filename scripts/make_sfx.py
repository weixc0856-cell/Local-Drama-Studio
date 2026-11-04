"""Rebuild the self-generated SFX beds used by the reference studies.

All sounds are synthesized locally with FFmpeg; no third-party samples are
included. They are intentionally simple placeholders for wind, water, chime and
transition whoosh, not recordings of a real space.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {proc.stderr[-2000:]}")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ms(path: Path) -> int:
    with wave.open(str(path), "rb") as fh:
        return round(fh.getnframes() / fh.getframerate() * 1000)


def build(out_dir: Path) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = {
        "sfx_wind_soft_30s.wav": (
            'anoisesrc=color=pink:duration=30:amplitude=0.10:seed=20261104',
            'highpass=f=100,lowpass=f=1600,tremolo=f=0.10:d=0.30,'
            'afade=t=in:st=0:d=3,afade=t=out:st=27:d=3,loudnorm=I=-30:TP=-6:LRA=8',
        ),
        "sfx_water_flow_20s.wav": (
            'anoisesrc=color=pink:duration=20:amplitude=0.08:seed=20261104',
            'highpass=f=250,lowpass=f=3000,tremolo=f=0.35:d=0.20,'
            'afade=t=in:st=0:d=2,afade=t=out:st=18:d=2,loudnorm=I=-32:TP=-8:LRA=8',
        ),
        "sfx_chime_single_6s.wav": (
            'sine=frequency=880:duration=6',
            'volume=0.22,afade=t=out:st=0.3:d=5.5,lowpass=f=5000,'
            'afade=t=in:st=0:d=0.05,loudnorm=I=-28:TP=-5:LRA=10',
        ),
        "sfx_whoosh_2s.wav": (
            'anoisesrc=color=pink:duration=2:amplitude=0.16:seed=20261104',
            'highpass=f=350,lowpass=f=6000,tremolo=f=2.0:d=0.5,'
            'afade=t=in:st=0:d=0.6,afade=t=out:st=1.2:d=0.8,loudnorm=I=-26:TP=-4:LRA=8',
        ),
    }
    out: list[dict[str, object]] = []
    for name, (source, af) in jobs.items():
        target = out_dir / name
        _run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", source,
            "-af", af, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(target),
        ])
        out.append({"path": str(target), "sha256": _sha(target), "duration_ms": _ms(target)})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild self-generated SFX beds")
    parser.add_argument("--out-dir", default="assets/audio/sfx")
    args = parser.parse_args()
    print(json.dumps(build(Path(args.out_dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
