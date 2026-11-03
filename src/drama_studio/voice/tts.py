"""Parameterized narration TTS against the local CosyVoice HTTP service.

The module is shared by ``scripts/r3_tts.py`` and the workspace task registry.
It never assumes an episode directory: narration, output directory and manifest
are explicit inputs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import load_audio, load_settings

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as fh:
        return fh.getnframes() / float(fh.getframerate())


def _read_narration(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TTSError(f"无法读取 narration.json: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list) or not data["lines"]:
        raise TTSError("narration.json 必须包含非空 lines 列表")
    lines: list[str] = []
    for index, item in enumerate(data["lines"], start=1):
        text = item.get("text") if isinstance(item, dict) else item
        if not isinstance(text, str) or not text.strip():
            raise TTSError(f"narration.json 第 {index} 行文本为空")
        lines.append(text.strip())
    return {"speaker": data.get("speaker"), "speed": data.get("speed", 1.0), "lines": lines}


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
    lines: list[str],
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
    entries = data.get("lines") or []
    if len(entries) != len(lines):
        return False
    for index, (entry, text) in enumerate(zip(entries, lines), start=1):
        if entry.get("text") != text or entry.get("index") != index:
            return False
        file_value = entry.get("file")
        if not file_value:
            return False
        path = (root / file_value).resolve()
        if not path.is_file() or sha256(path) != entry.get("sha256"):
            return False
    return True


def synthesize_narration(
    narration_path: Path,
    out_dir: Path,
    manifest_path: Path,
    *,
    root: Path | None = None,
    speaker: str | None = None,
    speed: float | None = None,
    base_url: str | None = None,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    http_client: httpx.Client | None = None,
) -> TTSResult:
    root = (root or load_settings().root).resolve()
    narration_path = narration_path if narration_path.is_absolute() else (root / narration_path)
    out_dir = out_dir if out_dir.is_absolute() else (root / out_dir)
    manifest_path = manifest_path if manifest_path.is_absolute() else (root / manifest_path)

    narration = _read_narration(narration_path)
    chosen_speaker = _default_speaker(speaker or narration["speaker"], root)
    chosen_speed = float(speed if speed is not None else narration["speed"])
    settings = load_settings(root)
    endpoint = (base_url or settings.tts.base_url).rstrip("/")
    sample_rate = int(settings.tts.sample_rate)
    narration_sha = sha256(narration_path)

    if not force and _manifest_ok(
        manifest_path, root, narration_sha, chosen_speaker, chosen_speed, narration["lines"], sample_rate
    ):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return TTSResult(
            manifest=manifest_path,
            speaker=chosen_speaker,
            speed=chosen_speed,
            total_seconds=round(sum(float(x.get("duration_seconds") or 0) for x in data["lines"]), 3),
            line_count=len(data["lines"]),
            reused=True,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    client = http_client or httpx.Client(base_url=endpoint, timeout=httpx.Timeout(timeout), trust_env=False)
    owns_client = http_client is None
    try:
        try:
            health = client.get("/health").json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TTSError(f"CosyVoice 不可用: {exc}") from exc
        if health.get("status") != "ready":
            raise TTSError(f"CosyVoice 未就绪: {health}")

        entries: list[dict[str, Any]] = []
        for index, text in enumerate(narration["lines"], start=1):
            raw_path = out_dir / f"line_{index:02d}_raw.wav"
            wav_path = out_dir / f"line_{index:02d}.wav"
            try:
                response = client.post(
                    "/tts",
                    json={"text": text, "speaker": chosen_speaker, "speed": chosen_speed},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise TTSError(f"第 {index} 行合成失败: {exc}") from exc
            raw_path.write_bytes(response.content)
            if raw_path.stat().st_size < 44:
                raise TTSError(f"第 {index} 行返回空音频")
            proc = subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-i", str(raw_path),
                    "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(wav_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                raise TTSError(f"第 {index} 行重采样失败: {proc.stderr[-800:]}")
            duration = wav_duration(wav_path)
            if duration <= 0:
                raise TTSError(f"第 {index} 行音频时长为 0")
            try:
                file_value = wav_path.relative_to(root).as_posix()
            except ValueError:
                file_value = str(wav_path)
            entries.append(
                {
                    "index": index,
                    "text": text,
                    "file": file_value,
                    "sha256": sha256(wav_path),
                    "duration_seconds": round(duration, 3),
                    "synth_seconds": response.headers.get("X-Synth-Seconds"),
                }
            )
    finally:
        if owns_client:
            client.close()

    try:
        narration_value = narration_path.relative_to(root).as_posix()
    except ValueError:
        narration_value = str(narration_path)
    manifest = {
        "speaker": chosen_speaker,
        "speed": chosen_speed,
        "sample_rate": sample_rate,
        "narration": narration_value,
        "narration_sha256": narration_sha,
        "endpoint": endpoint,
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
    )
