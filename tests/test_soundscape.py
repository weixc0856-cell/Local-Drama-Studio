from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drama_studio.voice.soundscape import (  # noqa: E402
    EARLY_TAPS_MS,
    SoundscapeSettings,
    load_settings,
    master,
    measure_loudness,
    space_filter,
    voice_filter,
)

SECTION = {
    "enabled": True,
    "reverb": {"method": "early_reflections"},
    "ir": {"path": "assets/audio/ir/synthetic_hall_0.9s.wav", "dry": 0.85, "wet": 0.18},
    "voice_eq": {"highpass_hz": 80, "deess": [{"hz": 6500, "gain": -2}, {"hz": 8000, "gain": -3}]},
    "ambience": {"track": "", "gain_db": -24},
    "bgm": {"track": "", "gain_db": -26},
    "ducking": {"enabled": True, "bgm": {"threshold": 0.05, "ratio": 4}},
    "voice_dynamics": {"enabled": False, "threshold_db": -20, "ratio": 2.5},
}
LOUDNESS = {"dialogue_lufs": -16.0, "bgm_lufs": -26.0, "true_peak_db": -1.5}


def test_settings_parse_the_config_section():
    settings = SoundscapeSettings.from_config(SECTION, LOUDNESS)
    assert settings.enabled is True
    assert settings.method == "early_reflections"
    assert settings.wet == pytest.approx(0.18)
    assert settings.target_lufs == pytest.approx(-16.0)
    assert settings.deess == ((6500.0, -2.0), (8000.0, -3.0))
    assert settings.compressor is False


def test_loudness_comes_from_the_programme_targets():
    """One place defines loudness: config/audio.yaml ``loudness``."""
    settings = SoundscapeSettings.from_config(SECTION, {"dialogue_lufs": -14.0,
                                                        "true_peak_db": -2.0})
    assert settings.target_lufs == pytest.approx(-14.0)
    assert settings.true_peak == pytest.approx(-2.0)


def test_repository_config_enables_the_agreed_chain():
    """06 (broadcast_light) was chosen by listening and is now the baseline."""
    settings = load_settings(ROOT)
    assert settings.enabled is True
    assert settings.voice_style == "broadcast_light"
    filter_string = space_filter(settings)
    assert "acompressor" in filter_string
    assert "aecho" in filter_string


def test_voice_filter_keeps_the_air():
    filter_string = voice_filter(SoundscapeSettings.from_config(SECTION, LOUDNESS))
    assert "highpass=f=80" in filter_string
    assert "entry(8000,-3.0)" in filter_string
    assert "lowpass" not in filter_string, "整条切高频会让诗词失去空气感"


def test_early_reflections_use_several_taps():
    filter_string = space_filter(SoundscapeSettings.from_config(SECTION, LOUDNESS))
    assert "aecho=" in filter_string
    assert filter_string.count("|") == 2 * (len(EARLY_TAPS_MS) - 1)


def test_compressor_is_off_unless_asked():
    settings = SoundscapeSettings.from_config(SECTION, LOUDNESS)
    assert "acompressor" not in space_filter(settings)
    loud = SoundscapeSettings.from_config(
        {**SECTION, "voice_dynamics": {"enabled": True}}, LOUDNESS)
    assert "acompressor" in space_filter(loud)


def test_disabled_master_is_a_no_op(tmp_path):
    source = tmp_path / "in.wav"
    write_tone(source)
    result = master(source, tmp_path / "out.wav", root=ROOT,
                    settings=SoundscapeSettings(enabled=False))
    assert result.status == "NOT_RUN"
    assert result.output is None
    assert not (tmp_path / "out.wav").exists()


def test_ir_is_deterministic(tmp_path):
    from make_ir import make_ir

    first = make_ir(tmp_path / "a.wav", seed=11)
    second = make_ir(tmp_path / "b.wav", seed=11)
    third = make_ir(tmp_path / "c.wav", seed=12)
    assert first["sha256"] == second["sha256"]
    assert first["sha256"] != third["sha256"]


def write_tone(path: Path, seconds: float = 1.0) -> Path:
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
        "-i", f"sine=frequency=220:duration={seconds}", "-ar", "48000",
        "-c:a", "pcm_s16le", str(path),
    ], check=True, capture_output=True)
    return path


@pytest.mark.skipif(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
                    reason="ffmpeg unavailable")
def test_master_runs_end_to_end(tmp_path):
    settings = SoundscapeSettings.from_config(SECTION, LOUDNESS)
    source = write_tone(tmp_path / "voice.wav", seconds=1.5)
    report_path = tmp_path / "out.wav"
    result = master(source, report_path, root=ROOT, settings=settings)
    assert result.status == "PASS", result.note
    assert report_path.is_file()
    measured = measure_loudness(report_path, settings)
    assert float(measured["input_i"]) > -30.0, "输出不能是静音"
    payload = json.dumps(result.report, ensure_ascii=False)
    assert "aecho" in payload


def test_convolution_is_recorded_as_blocked():
    """The build's afir outputs silence; the default must not depend on it."""
    settings = SoundscapeSettings.from_config(SECTION, LOUDNESS)
    assert settings.method == "early_reflections"


# ------------------------------------------------------------------ style
def test_voice_style_defaults_to_natural():
    settings = SoundscapeSettings.from_config({}, {})
    assert settings.voice_style == "natural"
    assert "acompressor" not in space_filter(settings)


def test_broadcast_style_adds_presence_and_compression():
    section = {**SECTION, "voice_style": "broadcast_light"}
    settings = SoundscapeSettings.from_config(section, LOUDNESS)
    filter_string = space_filter(settings)
    assert settings.voice_style == "broadcast_light"
    assert "entry(3000,2.5)" in filter_string
    assert "acompressor=threshold=-18.0dB" in filter_string
    assert "aecho" in filter_string          # the space is still there


def test_repository_uses_the_agreed_style():
    """06 was chosen by listening; the config must say so."""
    settings = load_settings(ROOT)
    assert settings.voice_style == "broadcast_light"


@pytest.mark.skipif(subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
                    reason="ffmpeg unavailable")
def test_master_hits_target_loudness_after_processing(tmp_path):
    """EQ/echo move the level, so the master must correct the processed file."""
    settings = SoundscapeSettings.from_config(SECTION, LOUDNESS)
    source = write_tone(tmp_path / "voice.wav", seconds=3.0)
    out = tmp_path / "out.wav"
    result = master(source, out, root=ROOT, settings=settings)
    assert result.status == "PASS", result.note
    measured = measure_loudness(out, settings)
    target = settings.target_lufs
    assert abs(float(measured["input_i"]) - target) <= 1.0, measured
