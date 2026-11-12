"""Soundscape mastering: one room, one loudness pass, applied to the whole line.

The order is fixed and each step has a reason:

1. **high-pass 80 Hz** — removes rumble the microphone picked up, not voice.
2. **targeted EQ, not a low-pass** — de-essing by cutting everything above
   7.5 kHz makes classical recitation dull; two narrow cuts keep the air.
3. **space** — two modes, and the honest one is the default:

   ``convolution`` uses ``afir`` with an impulse response: a real room.
   **It is blocked on this machine**: FFmpeg 8.1-full_build's ``afir`` outputs
   digital silence for every input form tried (mono/stereo IR, float PCM,
   unit impulse, every option combination). Recorded as a measured blocker.

   ``early_reflections`` (default) is a dense, gently decaying set of taps. It
   is a room-scale early-reflection model, **not** convolution, and must not be
   described as a measured reverb.
4. **sidechain ducking** (only when ambience/BGM exist) — the beds get out of
   the way of the voice.
5. **EBU R128, two passes** — measure, then normalise. One pass guesses.

Everything runs on the *assembled* dialogue track. Per-line reverb would restart
the room at every breath.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_IR = "assets/audio/ir/synthetic_hall_0.9s.wav"
LOUDNORM_JSON = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.S)

PASS = "PASS"
FAIL = "FAIL"
NOT_RUN = "NOT_RUN"


class SoundscapeError(RuntimeError):
    pass


@dataclass(frozen=True)
class SoundscapeSettings:
    enabled: bool = False
    method: str = "early_reflections"   # or "convolution" (blocked on this build)
    ir: str = DEFAULT_IR
    dry: float = 0.85
    wet: float = 0.18
    highpass_hz: float = 80.0
    deess: tuple[tuple[float, float], ...] = ((6500.0, -2.0), (8000.0, -3.0))
    ambience: str | None = None
    ambience_db: float = -24.0
    bgm: str | None = None
    bgm_db: float = -26.0
    ducking: bool = True
    duck_threshold: float = 0.05
    duck_ratio: float = 4.0
    voice_style: str = "natural"       # natural | broadcast_light | broadcast_strong
    compressor: bool = False
    compressor_threshold_db: float = -20.0
    compressor_ratio: float = 2.5
    target_lufs: float = -16.0
    true_peak: float = -1.5
    lra: float = 11.0

    @classmethod
    def from_config(cls, section: dict[str, Any] | None,
                    loudness: dict[str, Any] | None = None) -> "SoundscapeSettings":
        section = section or {}
        loudness = loudness or {}
        eq = section.get("voice_eq") or {}
        deess_raw = eq.get("deess") or []
        deess = tuple((float(item["hz"]), float(item["gain"])) for item in deess_raw)
        ambience = section.get("ambience") or {}
        bgm = section.get("bgm") or {}
        duck = section.get("ducking") or {}
        return cls(
            enabled=bool(section.get("enabled", False)),
            voice_style=str(section.get("voice_style", "natural")),
            method=str((section.get("reverb") or {}).get(
                "method", (section.get("ir") or {}).get("method", "early_reflections"))),
            ir=str((section.get("ir") or {}).get("path") or DEFAULT_IR),
            dry=float((section.get("ir") or {}).get("dry", 0.85)),
            wet=float((section.get("ir") or {}).get("wet", 0.18)),
            highpass_hz=float(eq.get("highpass_hz", 80.0)),
            deess=deess or cls.deess,
            ambience=ambience.get("track") or None,
            ambience_db=float(ambience.get("gain_db", -24.0)),
            bgm=bgm.get("track") or None,
            bgm_db=float(bgm.get("gain_db", loudness.get("bgm_lufs", -26.0))),
            compressor=bool((section.get("voice_dynamics") or {}).get("enabled", False)),
            compressor_threshold_db=float(
                (section.get("voice_dynamics") or {}).get("threshold_db", -20.0)),
            compressor_ratio=float(
                (section.get("voice_dynamics") or {}).get("ratio", 2.5)),
            ducking=bool(duck.get("enabled", True)),
            duck_threshold=float((duck.get("bgm") or {}).get("threshold", 0.05)),
            duck_ratio=float((duck.get("bgm") or {}).get("ratio", 4.0)),
            target_lufs=float(loudness.get("dialogue_lufs", -16.0)),
            true_peak=float(loudness.get("true_peak_db", -1.5)),
            lra=float(loudness.get("lra", 11.0)),
        )


@dataclass(frozen=True)
class SoundscapeResult:
    status: str
    output: Path | None
    settings: SoundscapeSettings
    measured: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    report: dict[str, Any] = field(default_factory=dict)


def load_settings(root: Path) -> SoundscapeSettings:
    path = root / "config" / "audio.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return SoundscapeSettings.from_config(data.get("soundscape"), data.get("loudness"))


def voice_filter(settings: SoundscapeSettings) -> str:
    """EQ chain for the dialogue, before the convolver."""
    entries = ";".join(f"entry({hz:.0f},{gain:.1f})" for hz, gain in settings.deess)
    return (f"highpass=f={settings.highpass_hz:.0f},"
            f"firequalizer=gain_entry='{entries}'")


def reverb_filter(settings: SoundscapeSettings) -> str:
    """Convolution reverb. ``afir`` takes the impulse response as a *second
    input stream*; forgetting that silently produces silence."""
    return f"afir=dry={settings.dry:.2f}:wet={settings.wet:.2f}"


# Dense early reflections with a decaying gain: a small room, not a canyon.
EARLY_TAPS_MS = (11, 23, 37, 53, 71, 97, 131, 173)
EARLY_GAINS = (0.55, 0.42, 0.32, 0.24, 0.18, 0.13, 0.09, 0.06)


BROADCAST_STYLES = {
    # Measured on the pre-2026-11-06 CosyVoice2 clone; VoxCPM2 levels differ: dynamics (p90-p10 of frame levels)
    # 43.8 dB raw -> 39.9 dB light -> 33.2 dB strong.
    "broadcast_light": {
        "eq": "entry(200,1.5);entry(3000,2.5);entry(5500,1.5);entry(7500,-2)",
        "threshold": -18.0, "ratio": 3.0, "release": 180,
    },
    "broadcast_strong": {
        "eq": "entry(250,2);entry(2500,4);entry(4000,3);entry(7500,-3)",
        "threshold": -26.0, "ratio": 4.0, "release": 120,
    },
}


def broadcast_filter(settings: SoundscapeSettings) -> str:
    """Announcer-style presence lift plus compression, or nothing at all.

    This changes the *sound* of the delivery, not the delivery: no amount of
    equalisation teaches the model to project. For that the reference recording
    itself has to be an announcer.
    """
    style = BROADCAST_STYLES.get(settings.voice_style)
    if style is None:
        return ""
    return (f"firequalizer=gain_entry='{style['eq']}',"
            f"acompressor=threshold={style['threshold']}dB:ratio={style['ratio']}:"
            f"attack=8:release={style['release']},")


def dynamics_filter(settings: SoundscapeSettings) -> str:
    """Optional gentle compression.

    Speech with a wide crest factor cannot reach -16 LUFS at -1.5 dBTP without
    taming its peaks; measured on this material the gap is ~4.6 dB. Off by
    default because it changes the voice character, which is a listening
    decision, not an arithmetic one.
    """
    if not settings.compressor:
        return ""
    return (f"acompressor=threshold={settings.compressor_threshold_db}dB:"
            f"ratio={settings.compressor_ratio}:attack=15:release=250,")


def space_filter(settings: SoundscapeSettings) -> str:
    """Combined EQ + space in one chain (single-input filters only)."""
    eq = voice_filter(settings)
    if settings.method == "convolution":
        return eq  # the convolver is appended separately, it needs a second input
    delays = "|".join(str(value) for value in EARLY_TAPS_MS)
    gains = "|".join(f"{value:.2f}" for value in EARLY_GAINS)
    wet = min(0.95, max(0.0, settings.wet + settings.dry - 0.85))
    return (f"{dynamics_filter(settings)}{broadcast_filter(settings)}{eq},"
            f"aecho={settings.dry:.2f}:{0.85 + wet * 0.15:.2f}:{delays}:{gains}")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def measure_loudness(source: Path, settings: SoundscapeSettings) -> dict[str, Any]:
    """First pass: ask loudnorm what the programme actually measures."""
    proc = _run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(source),
        "-af", f"loudnorm=I={settings.target_lufs}:TP={settings.true_peak}:"
               f"LRA={settings.lra}:print_format=json",
        "-f", "null", "-",
    ])
    if proc.returncode != 0:
        raise SoundscapeError(f"loudnorm 测量失败：{proc.stderr[-1200:]}")
    match = LOUDNORM_JSON.search(proc.stderr)
    if not match:
        raise SoundscapeError("loudnorm 未返回测量 JSON")
    return json.loads(match.group(0))


def _measure_file(path: Path, settings: "SoundscapeSettings") -> dict[str, Any]:
    proc = _run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"loudnorm=I={settings.target_lufs}:TP={settings.true_peak}:"
               f"LRA={settings.lra}:print_format=json",
        "-f", "null", "-",
    ])
    match = LOUDNORM_JSON.search(proc.stderr)
    if not match:
        return {}
    return json.loads(match.group(0))


def _apply_loudnorm(source: Path, target: Path, measured: dict[str, Any],
                    settings: "SoundscapeSettings") -> None:
    """Second real pass: normalise the *processed* file to the target loudness.

    The first pass measures the dry input, so EQ/reverb can move the result by
    several LU. This pass uses the measured values of the processed file.
    """
    proc = _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-af", f"loudnorm=I={settings.target_lufs}:TP={settings.true_peak}:"
               f"LRA={settings.lra}:measured_I={measured['input_i']}:"
               f"measured_TP={measured['input_tp']}:"
               f"measured_LRA={measured['input_lra']}:"
               f"measured_thresh={measured['input_thresh']}:"
               f"offset={measured['target_offset']}:linear=false",
        "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(target),
    ])
    if proc.returncode != 0:
        raise SoundscapeError(f"响度校正失败：{proc.stderr[-1200:]}")


def master(vocal_wav: Path, out_wav: Path, *, root: Path | None = None,
           settings: SoundscapeSettings | None = None) -> SoundscapeResult:
    """Apply EQ, reverb and a two-pass loudness normalisation.

    With ``settings.enabled`` false this is a no-op that reports ``NOT_RUN``, so
    a build can call it unconditionally and stay byte-identical to before.
    """
    root = (root or Path.cwd()).resolve()
    settings = settings or load_settings(root)
    if not settings.enabled:
        return SoundscapeResult(NOT_RUN, None, settings,
                                note="soundscape.enabled=false，未做声景处理")

    vocal_wav = Path(vocal_wav)
    if not vocal_wav.is_file():
        raise SoundscapeError(f"干音不存在：{vocal_wav}")
    ir_path = Path(settings.ir)
    if not ir_path.is_absolute():
        ir_path = root / ir_path
    if not ir_path.is_file():
        return SoundscapeResult(
            FAIL, None, settings,
            note=f"缺少脉冲响应 {ir_path}；先运行 scripts/make_ir.py")

    measured = measure_loudness(vocal_wav, settings)

    inputs = ["-i", str(vocal_wav), "-i", str(ir_path)]
    if settings.method == "convolution":
        graph = [f"[0:a]{voice_filter(settings)}[pre]",
                 f"[pre][1:a]{reverb_filter(settings)}[voice]"]
    else:
        graph = [f"[0:a]{space_filter(settings)}[voice]"]
    labels = ["[voice]"]
    index = 2
    if settings.ambience:
        amb = Path(settings.ambience)
        amb = amb if amb.is_absolute() else root / amb
        if amb.is_file():
            inputs += ["-stream_loop", "-1", "-i", str(amb)]
            graph.append(
                f"[{index}:a]volume={settings.ambience_db}dB,highpass=f=120,"
                f"lowpass=f=4000[amb]")
            index += 1
            labels.append("[amb]")
    if settings.bgm:
        track = Path(settings.bgm)
        track = track if track.is_absolute() else root / track
        if track.is_file():
            inputs += ["-stream_loop", "-1", "-i", str(track)]
            graph.append(f"[{index}:a]volume={settings.bgm_db}dB[bgm]")
            index += 1
            labels.append("[bgm]")

    if len(labels) == 1:
        mixed = "[voice]"
    else:
        graph.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:"
            f"normalize=0,alimiter=limit=0.95{mixed_label()}")
        mixed = mixed_label()

    graph.append(
        f"{mixed}loudnorm=I={settings.target_lufs}:TP={settings.true_peak}:"
        f"LRA={settings.lra}:measured_I={measured['input_i']}:"
        f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
        f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:"
        f"linear=false:print_format=summary[out]")

    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = _run([
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", ";".join(graph),
        "-map", "[out]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out_wav),
    ])
    if proc.returncode != 0:
        raise SoundscapeError(f"声景渲染失败：{proc.stderr[-1600:]}")

    final = _measure_file(out_wav, settings)
    correction = None
    try:
        deviation = abs(float(final.get("input_i", settings.target_lufs)) - settings.target_lufs)
    except (TypeError, ValueError):
        deviation = 0.0
    if final and deviation > 0.5:
        correction = final
        corrected = out_wav.with_suffix(".normalise.wav")
        _apply_loudnorm(out_wav, corrected, final, settings)
        corrected.replace(out_wav)
        final = _measure_file(out_wav, settings)

    report = {
        "stage": "soundscape.master",
        "source": str(vocal_wav),
        "output": str(out_wav),
        "ir": str(ir_path),
        "filter": ";".join(graph),
        "measured_before": measured,
        "measured_after": final,
        "correction_pass": correction,
        "targets": {"lufs": settings.target_lufs, "true_peak": settings.true_peak,
                    "lra": settings.lra},
        "beds": {"ambience": settings.ambience, "bgm": settings.bgm},
    }
    label = ("卷积混响" if settings.method == "convolution"
             else "早期反射（非卷积）")
    return SoundscapeResult(PASS, out_wav, settings, measured=measured,
                            note=f"EQ + {label} + 两遍响度", report=report)


def mixed_label() -> str:
    return "[mixed]"


def available() -> bool:
    return shutil.which("ffmpeg") is not None
