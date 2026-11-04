"""Parameterized narration TTS against the local CosyVoice HTTP service.

The module is shared by ``scripts/r3_tts.py`` and the workspace task registry.
It never assumes an episode directory: narration, output directory and manifest
are explicit inputs.

Four text layers are kept apart: source / display / tts / acoustic. The
acoustic layer may use curated homophone aliases; display and source text are
never rewritten. Recitation modes only change speed and pauses.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import load_audio, load_settings
from .pronunciation import Lexicon, build_report, line_layers, load_lexicon
from .recitation import ModeSpec, breath_text, mode_spec, plan_line

DEFAULT_TIMEOUT = 300.0


class TTSError(RuntimeError):
    pass


@dataclass(frozen=True)
class TTSResult:
    manifest: Path
    speaker: str
    speed: float
    total_seconds: float
    line_count: int
    reused: bool
    mode: str = "narration"
    pronunciation_report: Path | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as fh:
        return fh.getnframes() / float(fh.getframerate())


def _read_narration(path: Path, lexicon: Lexicon) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TTSError(f"无法读取 narration.json: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list) or not data["lines"]:
        raise TTSError("narration.json 必须包含非空 lines 列表")
    # A line may be a plain string or an object with text/subtitle_text or the
    # explicit source_text/display_text/tts_text layers. They are kept apart
    # because the SFT voice is trained on simplified Chinese: feeding
    # traditional glyphs degrades pronunciation, while subtitles keep the source.
    lines: list[dict[str, Any]] = []
    for index, item in enumerate(data["lines"], start=1):
        try:
            lines.append(line_layers(item, lexicon, index))
        except ValueError as exc:
            raise TTSError(f"narration.json 第 {index} 行：{exc}") from exc
    return {
        "speaker": data.get("speaker"),
        "speed": data.get("speed"),
        "mode": str(data.get("mode") or "narration"),
        "lines": lines,
    }


def _default_speaker(narration_speaker: str | None, root: Path) -> str:
    if narration_speaker:
        return narration_speaker
    audio = load_audio(root).get("tts") or {}
    speakers = audio.get("speakers") or {}
    narrator = speakers.get("narrator")
    if not narrator:
        raise TTSError("narration.json 未指定 speaker，且 config/audio.yaml 没有 narrator 映射")
    return str(narrator)


def _manifest_ok(
    manifest_path: Path,
    root: Path,
    narration_sha: str,
    speaker: str,
    speed: float,
    mode: str,
    spec: ModeSpec,
    lines: list[dict[str, Any]],
    sample_rate: int,
) -> bool:
    if not manifest_path.is_file():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if data.get("narration_sha256") != narration_sha:
        return False
    if data.get("speaker") != speaker or float(data.get("speed", -1)) != float(speed):
        return False
    if int(data.get("sample_rate", 0)) != sample_rate:
        return False
    if data.get("mode", "narration") != mode:
        return False
    if data.get("mode_spec") != spec.model_dump():
        return False
    entries = data.get("lines") or []
    if len(entries) != len(lines):
        return False
    for index, (entry, line) in enumerate(zip(entries, lines), start=1):
        if entry.get("text") != line["acoustic_text"] or entry.get("index") != index:
            return False
        if entry.get("acoustic_text") not in (None, line["acoustic_text"]):
            return False
        if entry.get("breath_text") not in (None, breath_text(line["acoustic_text"])):
            return False
        if (entry.get("subtitle_text") or entry.get("display_text")) != line["display_text"]:
            return False
        parts = entry.get("parts") or []
        expected = plan_line(line["acoustic_text"], spec)
        if [part["text"] for part in parts] != [part["text"] for part in expected["parts"]]:
            return False
        file_value = entry.get("file")
        if not file_value:
            return False
        path = (root / file_value).resolve()
        if not path.is_file() or sha256(path) != entry.get("sha256"):
            return False
    return True


def _resample(raw: Path, wav: Path, sample_rate: int, label: str) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(raw),
         "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(wav)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise TTSError(f"{label} 重采样失败: {proc.stderr[-800:]}")
    duration = wav_duration(wav)
    if duration <= 0:
        raise TTSError(f"{label} 音频时长为 0")
    return duration


def _silence(path: Path, milliseconds: int, sample_rate: int) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"anullsrc=r={sample_rate}:cl=mono", "-t", f"{milliseconds / 1000.0:.3f}",
         "-c:a", "pcm_s16le", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise TTSError(f"生成停顿失败: {proc.stderr[-800:]}")


def _concat(parts: list[Path], out: Path, sample_rate: int) -> None:
    if len(parts) == 1:
        shutil.copy2(parts[0], out)
        return
    list_path = out.with_suffix(".concat.txt")
    list_path.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(list_path),
         "-ar", str(sample_rate), "-ac", "1", "-c:a", "pcm_s16le", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise TTSError(f"拼接分句失败: {proc.stderr[-800:]}")


def synthesize_narration(
    narration_path: Path,
    out_dir: Path,
    manifest_path: Path,
    *,
    root: Path | None = None,
    speaker: str | None = None,
    speed: float | None = None,
    mode: str | None = None,
    base_url: str | None = None,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    http_client: httpx.Client | None = None,
) -> TTSResult:
    root = (root or load_settings().root).resolve()
    narration_path = narration_path if narration_path.is_absolute() else (root / narration_path)
    out_dir = out_dir if out_dir.is_absolute() else (root / out_dir)
    manifest_path = manifest_path if manifest_path.is_absolute() else (root / manifest_path)

    lexicon = load_lexicon(root, allow_missing=True)
    narration = _read_narration(narration_path, lexicon)
    chosen_mode = mode or narration["mode"]
    spec = mode_spec(root, chosen_mode)
    chosen_speaker = _default_speaker(speaker or narration["speaker"], root)
    chosen_speed = float(
        speed if speed is not None
        else (narration["speed"] if narration["speed"] is not None else spec.speed)
    )
    settings = load_settings(root)
    endpoint = (base_url or settings.tts.base_url).rstrip("/")
    sample_rate = int(settings.tts.sample_rate)
    narration_sha = sha256(narration_path)
    report_path = manifest_path.parent / "pronunciation_report.json"

    if not force and _manifest_ok(
        manifest_path, root, narration_sha, chosen_speaker, chosen_speed, chosen_mode,
        spec, narration["lines"], sample_rate,
    ):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return TTSResult(
            manifest=manifest_path,
            speaker=chosen_speaker,
            speed=chosen_speed,
            total_seconds=round(sum(float(x.get("duration_seconds") or 0) for x in data["lines"]), 3),
            line_count=len(data["lines"]),
            reused=True,
            mode=chosen_mode,
            pronunciation_report=report_path if report_path.is_file() else None,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    client = http_client or httpx.Client(base_url=endpoint, timeout=httpx.Timeout(timeout), trust_env=False)
    owns_client = http_client is None
    silence_cache: dict[int, Path] = {}
    try:
        try:
            health = client.get("/health").json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TTSError(f"CosyVoice 不可用: {exc}") from exc
        if health.get("status") != "ready":
            raise TTSError(f"CosyVoice 未就绪: {health}")

        entries: list[dict[str, Any]] = []
        for index, line in enumerate(narration["lines"], start=1):
            text = line["acoustic_text"]
            breath = breath_text(text)
            raw_path = out_dir / f"line_{index:02d}_raw.wav"
            wav_path = out_dir / f"line_{index:02d}.wav"
            try:
                response = client.post(
                    "/tts",
                    json={
                        "text": breath,
                        "speaker": chosen_speaker,
                        "speed": chosen_speed,
                        # The current SFT API model does not declare a
                        # language field; this is an explicit zh guard and
                        # is ignored by the server. The SFT model is
                        # Chinese-only and text_frontend stays enabled.
                        "language": "zh",
                        "text_frontend": True,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise TTSError(f"第 {index} 行整句合成失败: {exc}") from exc
            raw_path.write_bytes(response.content)
            if raw_path.stat().st_size < 44:
                raise TTSError(f"第 {index} 行返回空音频")
            duration = _resample(raw_path, wav_path, sample_rate, f"第 {index} 行")
            synth_total = float(response.headers.get("X-Synth-Seconds") or 0)
            try:
                file_value = wav_path.relative_to(root).as_posix()
            except ValueError:
                file_value = str(wav_path)
            entries.append(
                {
                    "index": index,
                    "text": text,
                    "breath_text": breath,
                    "tts_text": line["tts_text"],
                    "acoustic_text": text,
                    "source_text": line["source_text"],
                    "display_text": line["display_text"],
                    "subtitle_text": line["display_text"],
                    "overrides": line["overrides"],
                    "replacements": line["replacements"],
                    "file": file_value,
                    "sha256": sha256(wav_path),
                    "duration_seconds": round(duration, 3),
                    # The inter-line pause is mode policy, not an r3 hidden
                    # constant: r3_build and motion alignment both read it.
                    "pause_after_ms": spec.line_pause_ms,
                    "synth_seconds": round(synth_total, 3) if synth_total else None,
                    "parts": [{
                        "index": 1,
                        "text": breath,
                        "file": file_value,
                        "sha256": sha256(wav_path),
                        "duration_seconds": round(duration, 3),
                        "pause_after_ms": 0,
                    }],
                }
            )
    finally:
        if owns_client:
            client.close()

    try:
        narration_value = narration_path.relative_to(root).as_posix()
    except ValueError:
        narration_value = str(narration_path)
    report = build_report(narration["lines"], lexicon)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "speaker": chosen_speaker,
        "speed": chosen_speed,
        "mode": chosen_mode,
        "mode_spec": spec.model_dump(),
        "sample_rate": sample_rate,
        "narration": narration_value,
        "narration_sha256": narration_sha,
        "endpoint": endpoint,
        "request": {
            "language": "zh",
            "text_frontend": True,
            "api_language_field": False,
            "note": "CosyVoice-300M-SFT 是中文 SFT 模型；language 为显式守卫，当前服务模型忽略该字段",
        },
        "pronunciation": {
            "report": report_path.relative_to(root).as_posix() if report_path.is_relative_to(root) else str(report_path),
            "capabilities": report["capabilities"],
            "hit_lines": report["summary"]["hit_lines"],
            "review_status": "PENDING",
        },
        "lines": entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(manifest_path)
    return TTSResult(
        manifest=manifest_path,
        speaker=chosen_speaker,
        speed=chosen_speed,
        total_seconds=round(sum(x["duration_seconds"] for x in entries), 3),
        line_count=len(entries),
        reused=False,
        mode=chosen_mode,
        pronunciation_report=report_path,
    )
