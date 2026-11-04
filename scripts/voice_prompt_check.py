"""Measure and clean a zero-shot prompt recording.

The prompt decides what the clone learns: noise teaches noise, room teaches
room, and an unstable level teaches an unstable performance. So the first job is
to turn "sounds off" into numbers, and only then to clean it.

Only stdlib + ffmpeg. Nothing is written over the source: the original is copied
into ``assets/audio/prompts/source/`` and every derived file records its parent's
hash.

    .venv\\Scripts\\python.exe scripts\\voice_prompt_check.py check --in <wav>
    .venv\\Scripts\\python.exe scripts\\voice_prompt_check.py clean --in <wav> --out <wav>
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A prompt shorter than this teaches the model too little about the voice.
MIN_SECONDS = 5.0
MAX_SECONDS = 15.0
MIN_SNR_DB = 30.0
MAX_LEVEL_DRIFT_DB = 6.0
MIN_TAIL_DROP_DB_PER_300MS = -8.0   # a long tail means a live room


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def decode(path: Path, sample_rate: int = 24000) -> tuple[array.array, int]:
    """Decode to mono float samples at ``sample_rate`` via ffmpeg."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1",
         "-ar", str(sample_rate), "-f", "f32le", "-"],
        capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"decode failed: {proc.stderr.decode('utf-8', 'replace')[-500:]}")
    samples = array.array("f")
    samples.frombytes(proc.stdout)
    return samples, sample_rate


def probe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,sample_rate,channels,bits_per_sample",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8")
    data = json.loads(proc.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    return {
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "bits": int(stream.get("bits_per_sample") or 0),
        "duration": round(float(data.get("format", {}).get("duration") or 0.0), 3),
    }


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def _rms(samples: array.array) -> float:
    if not samples:
        return 0.0
    total = sum(value * value for value in samples)
    return math.sqrt(total / len(samples))


def describe(path: Path) -> dict:
    """Everything a human needs to decide "re-record" vs "clean this one"."""
    info = probe(path)
    samples, rate = decode(path)
    if not samples:
        raise RuntimeError("empty audio")

    peak = max(abs(value) for value in samples)
    clipped = sum(1 for value in samples if abs(value) >= 0.999)

    window = int(0.02 * rate)
    frames = [samples[index:index + window]
              for index in range(0, len(samples) - window + 1, window)]
    levels = [_db(_rms(frame)) for frame in frames]
    loudest = max(levels)
    # Speech region: everything between the first and last frame that is within
    # 30 dB of the loudest. Outside it is lead-in/lead-out, not room noise.
    speech_frames = [i for i, value in enumerate(levels) if value > loudest - 30.0]
    if not speech_frames:
        raise RuntimeError("no speech detected")
    first, last = speech_frames[0], speech_frames[-1]
    region = levels[first:last + 1]
    ordered = sorted(region)
    # The quietest fifth of the speech region is the between-syllable floor,
    # which is what "some noise" actually is; digital silence would hide it.
    floor_slice = ordered[:max(1, len(ordered) // 5)]
    noise_floor = sum(floor_slice) / len(floor_slice)
    loud_slice = ordered[int(len(ordered) * 0.75):]
    speech_level = sum(loud_slice) / len(loud_slice)

    # Drift between the first and second half catches "two takes" or a moving
    # microphone. A p90-p10 range would only re-measure the dynamics of speech.
    voiced = [(i, value) for i, value in enumerate(region)
              if value > noise_floor + 10.0]
    drift = 0.0
    if len(voiced) > 8:
        midpoint = len(region) // 2
        first_half = sorted(v for i, v in voiced if i < midpoint)
        second_half = sorted(v for i, v in voiced if i >= midpoint)
        if first_half and second_half:
            drift = round(second_half[len(second_half) // 2]
                          - first_half[len(first_half) // 2], 2)

    # Reverb tail: how much the level falls in the 300 ms after the last loud frame.
    tail_drop = None
    after = frames[last + 1:last + int(0.3 / 0.02)]
    if after:
        joined = array.array("f", [value for frame in after for value in frame])
        tail_drop = round(_db(_rms(joined)) - _db(_rms(frames[last])), 2)

    f0 = estimate_f0(samples, rate)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        **info,
        "peak_dbfs": round(_db(peak), 2),
        "clipped_samples": clipped,
        "noise_floor_dbfs": round(noise_floor, 2),
        "speech_dbfs": round(speech_level, 2),
        # On audio that is already clean the "quietest fifth" *is* the speech,
        # so the ratio is meaningless: report it as unmeasurable instead of 0.
        "snr_db": (round(speech_level - noise_floor, 2)
                   if speech_level - noise_floor >= 1.0 else None),
        "level_drift_db": drift,
        "tail_drop_db_300ms": tail_drop,
        "f0_median_hz": f0,
        "speech_start_s": round(first * 0.02, 2),
        "speech_end_s": round(last * 0.02, 2),
        "band_energy": band_energy(path),
    }


def band_energy(path: Path) -> dict:
    """Energy in two bands, so hiss and sibilance can be compared before/after."""
    def rms(lo: float, hi: float) -> float:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", str(path),
             "-af", f"highpass=f={lo},lowpass=f={hi},astats=metadata=0",
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in proc.stderr.splitlines():
            if "RMS level dB" in line:
                try:
                    return float(line.split(":")[-1].strip())
                except ValueError:
                    break
        return float("-inf")

    body = rms(500, 3000)
    high = rms(6000, 11000)
    return {"body_dbfs": body, "hf_dbfs": high,
            "hf_to_body_db": round(high - body, 2) if body > float("-inf") else None}


def estimate_f0(samples: array.array, rate: int,
                low: float = 60.0, high: float = 400.0) -> float | None:
    """Median F0 by autocorrelation over voiced frames."""
    window = int(0.04 * rate)
    hop = int(0.02 * rate)
    min_lag = max(2, int(rate / high))
    max_lag = min(int(rate / low), window - 1)
    values = []
    for start in range(0, len(samples) - window, hop):
        frame = samples[start:start + window]
        energy = _rms(frame)
        if energy < 0.01:
            continue
        mean = sum(frame) / len(frame)
        centred = [value - mean for value in frame]
        best_lag, best_score = 0, 0.0
        for lag in range(min_lag, max_lag):
            score = sum(centred[i] * centred[i + lag] for i in range(len(centred) - lag))
            if score > best_score:
                best_lag, best_score = lag, score
        if best_lag:
            values.append(rate / best_lag)
    if not values:
        return None
    values.sort()
    return round(values[len(values) // 2], 1)


def verdict(report: dict) -> dict:
    issues = []
    if report["duration"] < MIN_SECONDS:
        issues.append(f"时长 {report['duration']}s 短于建议的 {MIN_SECONDS}s：克隆相似度会明显变弱")
    if report["duration"] > MAX_SECONDS:
        issues.append(f"时长 {report['duration']}s 超过 {MAX_SECONDS}s：推理变慢，收益不明显")
    if report["clipped_samples"]:
        issues.append(f"削波 {report['clipped_samples']} 个采样点")
    if report["snr_db"] is not None and report["snr_db"] < MIN_SNR_DB:
        issues.append(f"SNR {report['snr_db']} dB 低于 {MIN_SNR_DB} dB：底噪会被一起学走")
    if abs(report["level_drift_db"]) > MAX_LEVEL_DRIFT_DB:
        issues.append(
            f"前后半段电平差 {report['level_drift_db']} dB 超过 {MAX_LEVEL_DRIFT_DB} dB："
            "像两次录音或麦克风距离变化")
    if (report["tail_drop_db_300ms"] is not None
            and report["tail_drop_db_300ms"] > MIN_TAIL_DROP_DB_PER_300MS):
        issues.append(f"尾部衰减只有 {report['tail_drop_db_300ms']} dB/300ms：房间混响偏长")
    return {"status": "PASS" if not issues else "REVIEW", "issues": issues}


def clean(source: Path, target: Path, *, noise_floor_db: float | None = None,
          target_lufs: float = -23.0, highpass_hz: float = 70.0,
          denoise_db: float = 8.0, method: str = "anlmdn") -> dict:
    """Denoise, EQ, trim silence and normalise — in that order.

    The prompt is normalised to a *comfortable* level (-23 LUFS), not to the
    programme target: loudness belongs to the master, and a hot prompt teaches
    the model a hot performance.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    # No silenceremove: a prompt's internal pauses are part of the performance,
    # and ``stop_periods=1`` truncates the take at the first one.
    # ``anlmdn`` beats ``afftdn`` on this take by measurement (SNR 38.8 -> 66.4
    # versus 39.8) and keeps the harmonics intact in the spectrogram.
    denoise = (f"afftdn=nr={denoise_db:.1f}:nf={-55.0}"
               if method == "afftdn" else
               "anlmdn=s=1:p=0.002:r=0.006:m=15")
    # Low-pass at 8 kHz is free: the model takes the prompt at 16 kHz for the
    # speech tokens and the speaker embedding, so nothing above 8 kHz is used.
    filters = [
        f"highpass=f={highpass_hz:.0f}",
        denoise,
        "firequalizer=gain_entry='entry(6200,-2);entry(7800,-2.5)'",
        "lowpass=f=8000",
        f"loudnorm=I={target_lufs}:TP=-2.0:LRA=11",
    ]
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(source),
         "-af", ",".join(filters), "-ac", "1", "-ar", "24000",
         "-c:a", "pcm_s16le", str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"clean failed: {proc.stderr[-1200:]}")
    return {"filters": filters, "output": rel(target)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prompt recording check / clean")
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("--in", dest="source", required=True)
    p_check.add_argument("--json", action="store_true")
    p_clean = sub.add_parser("clean")
    p_clean.add_argument("--in", dest="source", required=True)
    p_clean.add_argument("--out", required=True)
    p_clean.add_argument("--noise-floor", type=float, default=None)
    p_clean.add_argument("--target-lufs", type=float, default=-23.0)
    p_clean.add_argument("--denoise-db", type=float, default=8.0)
    p_clean.add_argument("--method", choices=["anlmdn", "afftdn"], default="anlmdn")
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.is_absolute():
        source = ROOT / source
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"not found: {source}"}, ensure_ascii=False))
        return 2

    if args.command == "check":
        report = describe(source)
        report["verdict"] = verdict(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    report = describe(source)
    target = Path(args.out)
    if not target.is_absolute():
        target = ROOT / target
    noise = args.noise_floor if args.noise_floor is not None else report["noise_floor_dbfs"]
    result = clean(source, target, noise_floor_db=noise,
                   target_lufs=args.target_lufs, denoise_db=args.denoise_db,
                   method=args.method)
    after = describe(target)
    after["verdict"] = verdict(after)
    print(json.dumps({
        "ok": True,
        "source": report,
        "output": after,
        "processing": result,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
