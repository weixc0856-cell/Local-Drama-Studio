"""R3-B narration TTS via the existing CosyVoice HTTP service.

No new dependencies: httpx is already in the project venv.
Outputs 48 kHz mono WAVs plus audio_manifest.json with durations/hashes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:50000"
ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "experiments/r3b/narration.json"
OUT = ROOT / "experiments/r3b/audio"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(base_url=BASE, timeout=300.0, trust_env=False)
    ready = client.get("/health").json()
    print("health:", ready.get("status"), "speakers:", ready.get("speakers"))
    if ready.get("status") != "ready":
        raise SystemExit("CosyVoice is not ready")

    manifest = []
    for idx, text in enumerate(spec["lines"], start=1):
        raw = OUT / f"line_{idx:02d}_raw.wav"
        wav = OUT / f"line_{idx:02d}.wav"
        resp = client.post("/tts", json={"text": text, "speaker": spec["speaker"], "speed": spec.get("speed", 1.0)})
        resp.raise_for_status()
        raw.write_bytes(resp.content)
        # Resample to 48 kHz mono for the final mix.
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)],
            check=True,
        )
        dur = wav_duration(wav)
        manifest.append({"index": idx, "text": text, "file": str(wav.relative_to(ROOT)),
                         "sha256": sha256(wav), "duration_seconds": round(dur, 3),
                         "synth_seconds": resp.headers.get("X-Synth-Seconds")})
        print(f"line {idx}: {dur:.2f}s -> {wav}")

    (ROOT / "experiments/r3b/audio_manifest.json").write_text(
        json.dumps({"speaker": spec["speaker"], "lines": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("total audio", round(sum(x["duration_seconds"] for x in manifest), 2), "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
