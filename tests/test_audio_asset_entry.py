from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audio_asset_entry.py"


@pytest.mark.skipif(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
                    reason="ffmpeg unavailable")
def test_entry_matches_file(tmp_path):
    tone = tmp_path / "warm_piano.wav"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=1.0", "-ar", "48000",
        "-c:a", "pcm_s16le", str(tone),
    ], check=True, capture_output=True)

    proc = subprocess.run([
        sys.executable, str(SCRIPT), str(tone),
        "--license", "CC0-1.0", "--status", "APPROVED",
        "--source-platform", "wikimedia_commons",
        "--asset-id", "bgm_test_01", "--tag", "piano",
    ], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    entry = json.loads(proc.stdout)
    assert entry["asset_id"] == "bgm_test_01"
    assert entry["sha256"] == hashlib.sha256(tone.read_bytes()).hexdigest()
    assert 900 <= entry["duration_ms"] <= 1100
    assert entry["tags"] == ["shinkai_scenery", "bgm", "piano"]
    assert entry["path"].endswith("warm_piano.wav")


def test_approved_requires_license(tmp_path):
    tone = tmp_path / "x.wav"
    tone.write_bytes(b"not-audio")
    proc = subprocess.run([
        sys.executable, str(SCRIPT), str(tone), "--status", "APPROVED",
    ], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0
    assert "verified --license" in proc.stderr
