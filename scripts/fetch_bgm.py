"""Download and clean the four CC0 Keynata Commons BGM tracks.

The previous synthetic sine beds were rejected: they produced a sustained
drone/hum. This script downloads only the explicitly CC0 Keynata tracks, then
applies a mild high-pass, 180/4200 Hz EQ, low-pass and FFT denoise. It never
fabricates music and never uses a third-party track without a recorded license.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path

KEYNATA_FILTER = ("highpass=f=70,equalizer=f=180:t=q:w=1.5:g=-3,"
                  "equalizer=f=4200:t=q:w=2.0:g=-3,lowpass=f=14000,"
                  "afftdn=nf=-40,alimiter=limit=0.95")
WARM_FILTER = "highpass=f=30,alimiter=limit=0.95"

TRACKS = {
    "ink_strings_duo": {
        "track_id": "classical_duo_24036",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_duo_24036/classical_duo_24036.mp3",
    },
    "court_strings_duo": {
        "track_id": "classical_duo_24015",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_duo_24015/classical_duo_24015.mp3",
    },
    "shinkai_piano": {
        "track_id": "classical_piano_6134",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_piano_6134/classical_piano_6134.mp3",
    },
    "ghibli_quartet": {
        "track_id": "classical_quartet_25010",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_quartet_25010/classical_quartet_25010.mp3",
    },
}

WARM_TRACKS = {
    "pop_canon_major": {
        "track_id": "jpop_3piece_11623",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/jpop_3piece_11623/jpop_3piece_11623.mp3",
    },
    "strings_c_major": {
        "track_id": "classical_quartet_25041",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_quartet_25041/classical_quartet_25041.mp3",
    },
    "piano_c_major": {
        "track_id": "classical_piano_4016",
        "url": "https://carf-coder.github.io/keynata-commons/release/tracks/classical_piano_4016/classical_piano_4016.mp3",
    },
}


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ms(path: Path) -> int:
    with wave.open(str(path), "rb") as fh:
        return round(fh.getnframes() / fh.getframerate() * 1000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=("keynata", "warm"), default="keynata",
                        help="keynata = first CC0 set (EQ-cleaned); warm = major-key replacement")
    parser.add_argument("--out-dir", default=None,
                        help="default: assets/audio/bgm/<set>")
    args = parser.parse_args()
    tracks = TRACKS if args.set == "keynata" else WARM_TRACKS
    filters = KEYNATA_FILTER if args.set == "keynata" else WARM_FILTER
    out = Path(args.out_dir or f"assets/audio/bgm/{args.set}")
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for name, spec in tracks.items():
        mp3 = out / f"{name}.mp3"
        wav = out / f"{name}.wav"
        if not mp3.is_file():
            _run(["curl.exe", "-L", "-s", "--max-time", "300", "-o", str(mp3), spec["url"]])
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(mp3),
            "-af", filters,
            "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav),
        ])
        results.append({
            "name": name,
            "track_id": spec["track_id"],
            "source_url": spec["url"],
            "license": "CC0-1.0",
            "wav": str(wav),
            "sha256": _sha(wav),
            "duration_ms": _ms(wav),
        })
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
