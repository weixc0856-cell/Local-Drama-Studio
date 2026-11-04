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
from .profiles import (
    ResolvedVoice,
    VoiceCastFile,
    VoiceLibrary,
    VoiceProfileError,
    cast_sha256,
    load_library,
    load_voice_cast,
    resolve_voice,
    validate_one_backend,
)
from .pronunciation import Lexicon, build_report, line_layers, load_lexicon
from .recitation import ModeSpec, breath_text, mode_spec, plan_line
from .zeroshot import ZeroShotError
from .zeroshot import synthesize as zeroshot_synthesize

DEFAULT_TIMEOUT = 300.0

TTS_MODES = ("sft", "zero_shot")
SFT_MODEL_CLASS = "CosyVoice"
SFT_MODEL_DIR_MARKER = "CosyVoice-300M-SFT"
ZERO_SHOT_MODEL_CLASS = "CosyVoice2"
ZERO_SHOT_MODEL_DIR_MARKER = "CosyVoice2-0.5B"


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
    tts_mode: str = "sft"
    model_class: str = ""
    model_dir: str = ""
    speaker_id: str | None = None
    voice_profiles: tuple[str, ...] = ()
    voice_cast_sha256: str | None = None


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
            layers = line_layers(item, lexicon, index)
        except ValueError as exc:
            raise TTSError(f"narration.json 第 {index} 行：{exc}") from exc
        if isinstance(item, dict):
            profile = str(item.get("voice_profile") or "").strip() or None
        else:
            profile = None
        layers["voice_profile"] = profile
        layers["line_id"] = (
            str(item.get("line_id") or "").strip() or None
            if isinstance(item, dict) else None)
        lines.append(layers)
    header = data.get("header")
    if header is not None:
        if isinstance(header, str):
            header = {"text": header}
        if not isinstance(header, dict) or not str(header.get("text") or "").strip():
            raise TTSError("narration.json 的 header 必须是字符串或 {text, pause_ms}")
        header = {
            "text": str(header["text"]).strip(),
            "pause_ms": int(header.get("pause_ms", 1100)),
            "voice_profile": str(header.get("voice_profile") or "").strip() or None,
        }
        if header["pause_ms"] < 0:
            raise TTSError("header.pause_ms 不能为负")
    return {
        "header": header,
        "speaker": data.get("speaker"),
        "speed": data.get("speed"),
        # ``mode`` is the recitation mode (narration / recitation / ...).
        # ``tts_mode`` is the synthesis backend (sft / zero_shot); they are
        # deliberately separate so a recitation style cannot silently select
        # a cloning backend.
        "mode": str(data.get("mode") or "narration"),
        "tts_mode": str(data.get("tts_mode") or "").strip() or None,
        "voice_profile": str(data.get("voice_profile") or "").strip() or None,
        "lines": lines,
    }


def _default_speaker(narration_speaker: str | None, root: Path) -> str:
    if narration_speaker:
        return narration_speaker
    audio = load_audio(root).get("tts") or {}
    default = audio.get("default_speaker")
    if default:
        return str(default)
    speakers = audio.get("speakers") or {}
    narrator = speakers.get("narrator")
    if not narrator:
        raise TTSError(
            "narration.json 未指定 speaker，且 config/audio.yaml 没有 "
            "tts.default_speaker / tts.speakers.narrator"
        )
    return str(narrator)


def _cast_entry(cast: ResolvedVoice, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "voice_profile": record["profile_id"],
        "voice_label": record["label"],
        "tts_mode": record["tts_mode"],
        "speaker": record["speaker"],
        "speaker_id": record["speaker_id"],
        "speed": record["speed"],
        "prompt": (
            {"audio": record["prompt_audio"], "sha256": record["prompt_sha256"],
             "text": record["prompt_text"]}
            if record["tts_mode"] == "zero_shot" else None
        ),
    }


def _cast_matches(entry: dict[str, Any], record: dict[str, Any]) -> bool:
    if entry.get("voice_profile") != record["profile_id"]:
        return False
    if entry.get("voice_label") != record["label"]:
        return False
    if entry.get("tts_mode") != record["tts_mode"]:
        return False
    if entry.get("speaker") != record["speaker"]:
        return False
    if entry.get("speaker_id") != record["speaker_id"]:
        return False
    prompt = entry.get("prompt") or {}
    if prompt.get("sha256") != record["prompt_sha256"]:
        return False
    if prompt.get("text") != record["prompt_text"]:
        return False
    if float(entry.get("speed", -1)) != float(record["speed"]):
        return False
    return True


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
    tts_mode: str,
    speaker_id: str | None,
    prompt_sha256: str | None,
    voice_cast_sha256: str | None = None,
    line_cast_records: list[dict[str, Any]] | None = None,
    header_cast_record: dict[str, Any] | None = None,
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
    if data.get("tts_mode") != tts_mode:
        return False
    if data.get("speaker_id") != speaker_id:
        return False
    if (data.get("prompt") or {}).get("sha256") != prompt_sha256:
        return False
    if voice_cast_sha256 is not None:
        if (data.get("voice_cast") or {}).get("sha256") != voice_cast_sha256:
            return False
        header_entry = data.get("header")
        if header_cast_record is not None:
            if not header_entry or not _cast_matches(header_entry, header_cast_record):
                return False
        elif header_entry and header_entry.get("voice_profile"):
            return False
    if data.get("mode_spec") != spec.model_dump():
        return False
    entries = data.get("lines") or []
    if len(entries) != len(lines):
        return False
    for index, (entry, line) in enumerate(zip(entries, lines), start=1):
        if entry.get("text") != line["acoustic_text"] or entry.get("index") != index:
            return False
        if line_cast_records is not None:
            if index - 1 >= len(line_cast_records):
                return False
            if not _cast_matches(entry, line_cast_records[index - 1]):
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


def _render_line(text: str, raw_path: Path, client: httpx.Client, endpoint: str,
                 timeout: float, use_zero_shot: bool, prompt_path: Path | None,
                 prompt_text: str, speed: float, sample_rate: int,
                 label: str, speaker: str = "") -> float:
    """Synthesize one segment to ``raw_path``; returns the server's synth seconds."""
    if use_zero_shot:
        try:
            zs = zeroshot_synthesize(text, prompt_wav=prompt_path, prompt_text=prompt_text,
                                     out_wav=raw_path, speed=speed, base=endpoint,
                                     timeout=timeout)
        except ZeroShotError as exc:
            raise TTSError(f"{label}零样本合成失败: {exc}") from exc
        synth = zs.synth_seconds
    else:
        try:
            response = client.post("/tts", json={
                "text": text, "speaker": speaker, "speed": speed,
                "language": "zh", "text_frontend": True,
            })
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSError(f"{label}合成失败: {exc}") from exc
        raw_path.write_bytes(response.content)
        synth = float(response.headers.get("X-Synth-Seconds") or 0)
    if raw_path.stat().st_size < 44:
        raise TTSError(f"{label}返回空音频")
    return synth


def _ledger(header: dict[str, Any] | None, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Absolute segment times from the start of the audio, for downstream timing."""
    ledger: list[dict[str, Any]] = []
    cursor = 0.0
    if header:
        end = round(header["duration_seconds"], 3)
        ledger.append({"kind": "header", "text": header["text"], "start": 0.0, "end": end})
        cursor = end + header["pause_ms"] / 1000.0
    for entry in entries:
        start = round(cursor, 3)
        end = round(start + float(entry["duration_seconds"]), 3)
        ledger.append({"kind": "line", "index": entry["index"], "start": start, "end": end})
        cursor = end + float(entry.get("pause_after_ms", 0)) / 1000.0
    return ledger


def header_offset_seconds(manifest: dict[str, Any] | Path) -> float:
    """How much audio the title header occupies before the first body line."""
    data = manifest if isinstance(manifest, dict) else json.loads(
        Path(manifest).read_text(encoding="utf-8"))
    header = data.get("header")
    if not header:
        return 0.0
    return round(float(header["duration_seconds"]) + float(header.get("pause_ms", 0)) / 1000.0, 3)


def _normalize_tts_mode(value: str | None) -> str:
    mode = str(value or "sft").strip().lower()
    if mode not in TTS_MODES:
        raise TTSError(f"未知的 TTS 模式 {mode!r}；可选 {list(TTS_MODES)}")
    return mode


def _as_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _validate_runtime(health: dict[str, Any], tts_mode: str, speaker: str) -> tuple[str, str]:
    """Reject a service whose loaded model does not match the requested mode."""
    model_class = str(health.get("model_class") or "").strip()
    model_dir = str(health.get("model_dir") or "").strip()
    if not model_class or not model_dir:
        raise TTSError(
            "CosyVoice /health 未返回 model_class/model_dir，无法确认实际运行时模型；"
            "请使用 scripts/cosyvoice_server.ps1 启动并检查服务版本"
        )
    if tts_mode == "sft":
        if model_class != SFT_MODEL_CLASS or SFT_MODEL_DIR_MARKER not in model_dir:
            raise TTSError(
                f"请求 SFT，但 50000 当前加载的是 {model_class} @ {model_dir}；"
                f"请启动 CosyVoice-300M-SFT（-Model sft）"
            )
        speakers = [str(item) for item in (health.get("speakers") or [])]
        if not speakers:
            raise TTSError("当前 SFT 运行时没有返回预置音色列表，无法确认 speaker")
        if speaker not in speakers:
            raise TTSError(
                f"当前 SFT 运行时没有预置音色 {speaker!r}；可用：{speakers}"
            )
    else:
        if model_class != ZERO_SHOT_MODEL_CLASS or ZERO_SHOT_MODEL_DIR_MARKER not in model_dir:
            raise TTSError(
                f"请求 zero-shot，但 50000 当前加载的是 {model_class} @ {model_dir}；"
                f"请启动 CosyVoice2-0.5B（-Model cosyvoice2）"
            )
    return model_class, model_dir


def _validate_runtime_cast(health: dict[str, Any], tts_mode: str,
                           casts: list[ResolvedVoice]) -> tuple[str, str]:
    speakers = sorted({str(cast.speaker) for cast in casts
                       if cast.tts_mode == "sft" and cast.speaker})
    if tts_mode == "sft":
        if not speakers:
            raise TTSError("SFT 模式没有可用的 speaker")
        for speaker in speakers:
            model_class, model_dir = _validate_runtime(health, tts_mode, speaker)
        return model_class, model_dir
    return _validate_runtime(health, tts_mode, "")


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
    tts_mode: str | None = None,
    speaker_mode: str | None = None,
    voice_profile: str | None = None,
    voices_path: Path | None = None,
    voice_cast_path: Path | None = None,
    require_approved_voices: bool = True,
) -> TTSResult:
    root = (root or load_settings().root).resolve()
    narration_path = narration_path if narration_path.is_absolute() else (root / narration_path)
    out_dir = out_dir if out_dir.is_absolute() else (root / out_dir)
    manifest_path = manifest_path if manifest_path.is_absolute() else (root / manifest_path)

    lexicon = load_lexicon(root, allow_missing=True)
    narration = _read_narration(narration_path, lexicon)
    chosen_mode = mode or narration["mode"]
    spec = mode_spec(root, chosen_mode)

    audio_config = load_audio(root)
    tts_cfg = audio_config.get("tts") or {}
    zero_cfg = tts_cfg.get("zero_shot") or {}

    # Explicit argument > narration.json > config/audio.yaml. There is no
    # "enabled" switch: a zero-shot run must ask for zero_shot by name.
    configured_tts_mode = _normalize_tts_mode(str(tts_cfg.get("mode") or "sft"))
    requested_tts_mode = tts_mode if tts_mode is not None else (
        speaker_mode if speaker_mode is not None else narration.get("tts_mode")
    )

    cast_file: VoiceCastFile | None = None
    if voice_cast_path is not None:
        try:
            cast_file = load_voice_cast(
                voice_cast_path if voice_cast_path.is_absolute()
                else (root / voice_cast_path))
        except VoiceProfileError as exc:
            raise TTSError(str(exc)) from exc
    cast_line_profiles = [
        cast_file.line_profile(index, line.get("line_id"))
        if cast_file is not None else None
        for index, line in enumerate(narration["lines"], start=1)
    ]
    line_profiles = [
        line.get("voice_profile") or cast_profile
        for line, cast_profile in zip(narration["lines"], cast_line_profiles)
    ]
    header_profile = ((narration.get("header") or {}).get("voice_profile")
                      or (cast_file.header_profile if cast_file else None))
    run_profile = str(
        voice_profile or narration.get("voice_profile")
        or (cast_file.default_profile if cast_file else "") or ""
    ).strip() or None
    use_cast = bool(run_profile or header_profile or any(line_profiles))

    prompt_path: Path | None = None
    prompt_text = ""
    prompt_sha256: str | None = None
    speaker_id: str | None = None
    default_cast: ResolvedVoice | None = None
    header_cast: ResolvedVoice | None = None
    line_casts: list[ResolvedVoice] = []
    header_cast_record: dict[str, Any] | None = None
    line_cast_records: list[dict[str, Any]] | None = None
    voice_cast_sha256: str | None = None
    voice_profiles: tuple[str, ...] = ()

    if use_cast:
        library = load_library(voices_path, root=root, allow_missing=False)
        if library is None:
            raise TTSError("voice profile requested but config/voices.yaml is missing")
        default_id = run_profile or library.default_profile
        if not default_id:
            raise TTSError("voice profile requested but the library has no default_profile")
        try:
            default_cast = resolve_voice(
                library.get(default_id), root,
                require_approved=require_approved_voices)
            header_cast = (resolve_voice(library.get(header_profile), root,
                                         require_approved=require_approved_voices)
                           if header_profile else default_cast)
            line_casts = [
                (resolve_voice(library.get(pid), root,
                               require_approved=require_approved_voices)
                 if pid else default_cast)
                for pid in line_profiles
            ]
        except VoiceProfileError as exc:
            raise TTSError(str(exc)) from exc
        try:
            chosen_tts_mode = validate_one_backend([default_cast, header_cast, *line_casts])
        except VoiceProfileError as exc:
            raise TTSError(str(exc)) from exc
        if requested_tts_mode:
            requested = _normalize_tts_mode(requested_tts_mode)
            if requested != chosen_tts_mode:
                raise TTSError(
                    f"narration/config requests {requested}, but selected voice profiles "
                    f"require {chosen_tts_mode}; one run cannot load both models")
        if speaker and chosen_tts_mode == "sft":
            available = sorted({str(c.speaker) for c in line_casts if c.speaker})
            if speaker not in available:
                raise TTSError(
                    f"--speaker {speaker!r} conflicts with the selected voice profiles "
                    f"({available}); change the profile or drop --speaker")
        chosen_speaker = default_cast.label
        speaker_id = default_cast.speaker_id

        def cast_speed(cast: ResolvedVoice) -> float:
            if speed is not None:
                return float(speed)
            if narration["speed"] is not None:
                return float(narration["speed"])
            if cast.speed is not None:
                return float(cast.speed)
            cfg = zero_cfg.get("speed") if cast.tts_mode == "zero_shot" else None
            return float(cfg if cfg is not None else spec.speed)

        chosen_speed = cast_speed(default_cast)
        assert default_cast.prompt_sha256 is not None or default_cast.tts_mode == "sft"
        prompt_sha256 = default_cast.prompt_sha256
        prompt_text = str(default_cast.prompt_text or "")
        if default_cast.prompt_audio:
            prompt_path = root / default_cast.prompt_audio
        voice_profiles = tuple(sorted({c.profile_id for c in [default_cast, header_cast, *line_casts]}))
    else:
        chosen_tts_mode = (_normalize_tts_mode(requested_tts_mode)
                           if requested_tts_mode else configured_tts_mode)
        if chosen_tts_mode == "zero_shot":
            prompt_text = str(zero_cfg.get("prompt_text") or "").strip()
            if not prompt_text:
                raise TTSError("zero-shot 模式需要 tts.zero_shot.prompt_text，且必须与参考音逐字一致")
            prompt_path = Path(str(zero_cfg.get("prompt_audio") or ""))
            prompt_path = prompt_path if prompt_path.is_absolute() else (root / prompt_path)
            if not prompt_path.is_file():
                raise TTSError(f"zero-shot 参考音不存在：{prompt_path}")
            prompt_sha256 = sha256(prompt_path)
            chosen_speaker = f"zero_shot:{prompt_path.stem}"
        else:
            chosen_speaker = _default_speaker(speaker or narration["speaker"], root)
            speaker_id = chosen_speaker
        cfg_speed = zero_cfg.get("speed") if chosen_tts_mode == "zero_shot" else None
        chosen_speed = float(
            speed if speed is not None
            else (narration["speed"] if narration["speed"] is not None
                  else (cfg_speed if cfg_speed is not None else spec.speed))
        )

    use_zero_shot = chosen_tts_mode == "zero_shot"
    header_speed = chosen_speed
    line_speeds: list[float] = []
    if use_cast:
        assert default_cast is not None and header_cast is not None
        header_speed = cast_speed(header_cast)
        line_speeds = [cast_speed(cast) for cast in line_casts]
        if narration.get("header"):
            header_cast_record = {**header_cast.cast_record(), "speed": header_speed}
        line_cast_records = [
            {**cast.cast_record(), "speed": line_speeds[index]}
            for index, cast in enumerate(line_casts)
        ]
        voice_cast_sha256 = cast_sha256(
            ([header_cast_record] if header_cast_record else []) + line_cast_records)
    settings = load_settings(root)
    endpoint = (base_url or settings.tts.base_url).rstrip("/")
    sample_rate = int(settings.tts.sample_rate)
    narration_sha = sha256(narration_path)
    report_path = manifest_path.parent / "pronunciation_report.json"

    if not force and _manifest_ok(
        manifest_path, root, narration_sha, chosen_speaker, chosen_speed, chosen_mode,
        spec, narration["lines"], sample_rate, chosen_tts_mode, speaker_id, prompt_sha256,
        voice_cast_sha256, line_cast_records, header_cast_record,
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
            tts_mode=str(data.get("tts_mode") or chosen_tts_mode),
            model_class=str(data.get("model_class") or ""),
            model_dir=str(data.get("model_dir") or ""),
            speaker_id=data.get("speaker_id"),
            voice_profiles=tuple((data.get("voice_cast") or {}).get("profiles") or ()),
            voice_cast_sha256=(data.get("voice_cast") or {}).get("sha256"),
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
        if use_cast:
            model_class, model_dir = _validate_runtime_cast(
                health, chosen_tts_mode, [default_cast, header_cast, *line_casts])  # type: ignore[list-item]
        else:
            model_class, model_dir = _validate_runtime(health, chosen_tts_mode, chosen_speaker)

        def cast_prompt(cast: ResolvedVoice) -> tuple[Path | None, str]:
            if cast.tts_mode != "zero_shot":
                return None, ""
            assert cast.prompt_audio is not None
            return root / cast.prompt_audio, str(cast.prompt_text or "")

        entries: list[dict[str, Any]] = []
        synth_total = 0.0
        header_entry: dict[str, Any] | None = None
        if narration.get("header"):
            header_text = narration["header"]["text"]
            header_raw = out_dir / "header_raw.wav"
            header_wav = out_dir / "header.wav"
            if use_cast:
                assert header_cast is not None
                header_prompt, header_prompt_text = cast_prompt(header_cast)
                header_speaker = header_cast.speaker or ""
            else:
                header_prompt, header_prompt_text = prompt_path, prompt_text
                header_speaker = chosen_speaker
            synth_total += _render_line(header_text, header_raw, client, endpoint, timeout,
                                        use_zero_shot, header_prompt, header_prompt_text,
                                        header_speed, sample_rate, "标题",
                                        header_speaker)
            header_duration = _resample(header_raw, header_wav, sample_rate, "标题")
            header_entry = {
                "text": header_text,
                "file": _as_rel(header_wav, root),
                "duration_seconds": round(header_duration, 3),
                "pause_ms": int(narration["header"]["pause_ms"]),
            }
            if use_cast:
                assert header_cast_record is not None
                header_entry.update(_cast_entry(header_cast, header_cast_record))

        for index, line in enumerate(narration["lines"], start=1):
            text = line["acoustic_text"]
            breath = breath_text(text)
            raw_path = out_dir / f"line_{index:02d}_raw.wav"
            wav_path = out_dir / f"line_{index:02d}.wav"
            if use_cast:
                line_cast = line_casts[index - 1]
                line_prompt, line_prompt_text = cast_prompt(line_cast)
                line_speed = line_speeds[index - 1]
                line_speaker = line_cast.speaker or ""
            else:
                line_cast = None
                line_prompt, line_prompt_text = prompt_path, prompt_text
                line_speed = chosen_speed
                line_speaker = chosen_speaker
            synth_total += _render_line(breath, raw_path, client, endpoint, timeout,
                                        use_zero_shot, line_prompt, line_prompt_text,
                                        line_speed, sample_rate, f"第 {index} 行",
                                        line_speaker)
            duration = _resample(raw_path, wav_path, sample_rate, f"第 {index} 行")
            file_value = _as_rel(wav_path, root)
            line_entry = {
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
            if use_cast:
                assert line_cast is not None and line_cast_records is not None
                line_entry.update(_cast_entry(line_cast, line_cast_records[index - 1]))
            entries.append(line_entry)
    finally:
        if owns_client:
            client.close()

    narration_value = _as_rel(narration_path, root)
    report = build_report(narration["lines"], lexicon)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "tts_mode": chosen_tts_mode,
        "model_class": model_class,
        "model_dir": model_dir,
        "speaker_id": speaker_id,
        "speaker": chosen_speaker,
        "speed": chosen_speed,
        "mode": chosen_mode,
        "mode_spec": spec.model_dump(),
        "sample_rate": sample_rate,
        "narration": narration_value,
        "narration_sha256": narration_sha,
        "endpoint": endpoint,
        "prompt": (
            {"audio": _as_rel(prompt_path, root), "sha256": prompt_sha256, "text": prompt_text}
            if prompt_path is not None else None
        ),
        "voice_cast": (
            {
                "sha256": voice_cast_sha256,
                "source": (
                    _as_rel(voice_cast_path if voice_cast_path.is_absolute()
                            else (root / voice_cast_path), root)
                    if voice_cast_path is not None else None),
                "profiles": list(voice_profiles),
                "header_profile": (
                    header_cast.profile_id
                    if header_cast is not None and narration.get("header") else None),
                "line_profiles": [cast.profile_id for cast in line_casts],
                "records": [
                    record for record in [header_cast_record, *line_cast_records]
                    if record is not None
                ],
            }
            if use_cast else None
        ),
        "runtime": {
            "model_class": model_class,
            "model_dir": model_dir,
            "speakers": health.get("speakers") or [],
            "modes": health.get("modes") or [],
        },
        "request": {
            "language": "zh",
            "text_frontend": True,
            "api_language_field": False,
            "tts_mode": chosen_tts_mode,
            "voice_profiles": list(voice_profiles),
            "note": "tts_mode 是显式选择；SFT 只接受 CosyVoice-300M-SFT，zero-shot 只接受 CosyVoice2-0.5B；voice_cast 记录逐行音色",
        },
        "pronunciation": {
            "report": _as_rel(report_path, root),
            "capabilities": report["capabilities"],
            "hit_lines": report["summary"]["hit_lines"],
            "review_status": "PENDING",
        },
        "header": header_entry,
        "ledger": _ledger(header_entry, entries),
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
        tts_mode=chosen_tts_mode,
        model_class=model_class,
        model_dir=model_dir,
        speaker_id=speaker_id,
        voice_profiles=voice_profiles,
        voice_cast_sha256=voice_cast_sha256,
    )
