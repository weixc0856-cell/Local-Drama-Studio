from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from voice_prompt_check import describe, estimate_f0, verdict  # noqa: E402


def write_voice(tmp_path: Path, *, seconds: float = 2.0, frequency: int = 220,
                lead_silence: float = 0.3) -> Path:
    """A tone with a quiet lead-in, standing in for a recorded prompt."""
    path = tmp_path / "voice.wav"
    # A tone over a low noise floor: a pure tone has no floor to measure, which
    # the checker reports as "unmeasurable" rather than as a pass.
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i",
        f"sine=frequency={frequency}:duration={seconds}:sample_rate=24000",
        "-f", "lavfi", "-i", f"anoisesrc=color=white:duration={seconds}:amplitude=0.01:seed=3",
        "-filter_complex",
        f"[0:a]volume='if(lt(mod(t\\,0.5)\\,0.25)\\,0.35\\,0.01)':eval=frame[t];"
        f"[1:a]volume=0.05[n];[t][n]amix=inputs=2:normalize=0,"
        f"adelay={int(lead_silence * 1000)}|{int(lead_silence * 1000)}[out]",
        "-map", "[out]", "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(path),
    ], check=True, capture_output=True)
    return path


@pytest.mark.skipif(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
                    reason="ffmpeg unavailable")
def test_describe_reports_levels_and_pitch(tmp_path):
    path = write_voice(tmp_path)
    report = describe(path)
    assert report["duration"] > 2.0
    assert report["f0_median_hz"] == pytest.approx(220, abs=12)
    assert report["snr_db"] is not None and report["snr_db"] > 15
    assert report["clipped_samples"] == 0
    assert report["speech_start_s"] > 0.1  # the lead-in is not counted as speech


@pytest.mark.skipif(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
                    reason="ffmpeg unavailable")
def test_short_prompt_is_flagged(tmp_path):
    report = describe(write_voice(tmp_path, seconds=1.0))
    result = verdict(report)
    assert result["status"] == "REVIEW"
    assert any("短于建议" in issue for issue in result["issues"])


def test_f0_estimate_needs_voiced_frames():
    import array

    silent = array.array("f", [0.0] * 24000)
    assert estimate_f0(silent, 24000) is None


# --------------------------------------------------------------- zero-shot
def test_zeroshot_requires_prompt_text(tmp_path):
    from drama_studio.voice.zeroshot import ZeroShotError, synthesize

    prompt = tmp_path / "p.wav"
    prompt.write_bytes(b"RIFF")
    with pytest.raises(ZeroShotError, match="prompt_text 必填"):
        synthesize("春江潮水连海平", prompt_wav=prompt, prompt_text="  ",
                   out_wav=tmp_path / "o.wav")


def test_zeroshot_requires_the_prompt_to_exist(tmp_path):
    from drama_studio.voice.zeroshot import ZeroShotError, synthesize

    with pytest.raises(ZeroShotError, match="参考音频不存在"):
        synthesize("春江潮水连海平", prompt_wav=tmp_path / "missing.wav",
                   prompt_text="希望你以后能够做的比我还好呦。",
                   out_wav=tmp_path / "o.wav")


def test_zeroshot_health_is_none_when_nothing_is_listening():
    """The caller owns the service lifecycle; a down service must not raise."""
    from drama_studio.voice.zeroshot import healthy

    assert healthy("http://127.0.0.1:59999") is None
