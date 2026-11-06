from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml

from drama_studio.voice.profiles import (
    VoiceProfileError,
    load_library,
    resolve_voice,
    validate_one_backend,
)
from drama_studio.voice.tts import TTSError, synthesize_narration


def _wav_bytes(seconds: float = 0.2, rate: int = 22050) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def _root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text(
        'paths: {}\ntts:\n  base_url: "http://tts.test"\n  sample_rate: 48000\n',
        encoding="utf-8",
    )
    (tmp_path / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_text: "默认参考"\n'
        '    prompt_audio: "assets/default.wav"\n    speed: 0.9\n',
        encoding="utf-8",
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "default.wav").write_bytes(_wav_bytes())
    (tmp_path / "assets" / "a.wav").write_bytes(_wav_bytes())
    (tmp_path / "assets" / "b.wav").write_bytes(_wav_bytes())
    return tmp_path


def _library(root: Path) -> Path:
    payload = {
        "schema_version": "1.0",
        "default_profile": "voice_a",
        "profiles": [
            {
                "profile_id": "voice_a", "display_name": "A", "tts_mode": "zero_shot",
                "prompt_audio": "assets/a.wav", "prompt_text": "参考 A", "speed": 0.9,
                "status": "APPROVED", "commercial_allowed": True,
                "license_evidence": "assets/rights.md",
            },
            {
                "profile_id": "voice_b", "display_name": "B", "tts_mode": "zero_shot",
                "prompt_audio": "assets/b.wav", "prompt_text": "参考 B", "speed": 1.0,
                "status": "APPROVED", "commercial_allowed": True,
                "license_evidence": "assets/rights.md",
            },
            {
                "profile_id": "candidate", "display_name": "C", "tts_mode": "zero_shot",
                "prompt_audio": "assets/b.wav", "prompt_text": "参考 B",
                "status": "TECHNICALLY_VALIDATED", "commercial_allowed": None,
            },
        ],
    }
    path = root / "config" / "voices.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def _narration(root: Path, lines: list[dict | str], **extra) -> Path:
    path = root / "episode" / "narration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"lines": lines, **extra}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _zero_shot_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ready", "model_class": "VoxCPM2",
                "model_dir": "D:/AI/models/voxcpm2",
                "speakers": [], "modes": ["zero_shot"],
            })
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")


def test_library_enforces_approved_and_mode_shape(tmp_path: Path) -> None:
    root = _root(tmp_path)
    library = load_library(_library(root), allow_missing=False)
    assert library is not None
    resolved = resolve_voice(library.get("voice_a"), root)
    assert resolved.label == "zero_shot:a"
    assert resolved.prompt_sha256

    with pytest.raises(VoiceProfileError, match="only APPROVED"):
        resolve_voice(library.get("candidate"), root)
    resolve_voice(library.get("candidate"), root, require_approved=False)

    bad = {
        "schema_version": "1.0",
        "profiles": [{"profile_id": "bad", "display_name": "B", "tts_mode": "sft",
                      "speaker": "中文男", "prompt_audio": "assets/a.wav"}],
    }
    path = root / "config" / "bad.yaml"
    path.write_text(yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8")
    with pytest.raises(VoiceProfileError):
        load_library(path, allow_missing=False)


def test_zero_shot_cast_is_per_line_and_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    _library(root)
    narration = _narration(root, [
        {"text": "第一句", "voice_profile": "voice_a"},
        {"text": "第二句", "voice_profile": "voice_b"},
    ])
    seen: list[tuple[str, str]] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append((Path(prompt_wav).name, prompt_text))
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)
    client = _zero_shot_client()
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client, force=True)
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert seen == [("a.wav", "参考 A"), ("b.wav", "参考 B")]
    assert result.voice_profiles == ("voice_a", "voice_b")
    assert manifest["voice_cast"]["line_profiles"] == ["voice_a", "voice_b"]
    assert manifest["lines"][0]["voice_profile"] == "voice_a"
    assert manifest["lines"][0]["prompt"]["audio"] == "assets/a.wav"
    assert manifest["lines"][1]["speed"] == 1.0
    assert manifest["voice_cast"]["sha256"] == result.voice_cast_sha256

    again = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client)
    assert again.reused is True
    assert len(seen) == 2


def test_one_profile_default_covers_all_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    _library(root)
    narration = _narration(root, ["第一句", "第二句"])
    seen: list[str] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append(Path(prompt_wav).name)
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=_zero_shot_client(), force=True, voice_profile="voice_b")
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert seen == ["b.wav", "b.wav"]
    assert manifest["voice_cast"]["line_profiles"] == ["voice_b", "voice_b"]


def test_unapproved_profile_is_refused(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _library(root)
    narration = _narration(root, [{"text": "第一句", "voice_profile": "candidate"}])
    with pytest.raises(TTSError, match="only APPROVED"):
        synthesize_narration(
            narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
            root=root, http_client=_zero_shot_client())


def test_mixed_backends_are_refused(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payload = {
        "schema_version": "1.0", "default_profile": "sft",
        "profiles": [
            {"profile_id": "sft", "display_name": "S", "tts_mode": "sft",
             "speaker": "中文男", "status": "APPROVED", "commercial_allowed": True,
             "license_evidence": "x"},
            {"profile_id": "clone", "display_name": "C", "tts_mode": "zero_shot",
             "prompt_audio": "assets/a.wav", "prompt_text": "参考 A",
             "status": "APPROVED", "commercial_allowed": True, "license_evidence": "x"},
        ],
    }
    path = root / "config" / "voices.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    narration = _narration(root, [{"text": "第一句", "voice_profile": "clone"}])
    with pytest.raises(TTSError, match="mixed TTS modes"):
        synthesize_narration(
            narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
            root=root, http_client=_zero_shot_client())


def test_sft_is_retired(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payload = {
        "schema_version": "1.0", "default_profile": "male",
        "profiles": [
            {"profile_id": "male", "display_name": "M", "tts_mode": "sft",
             "speaker": "中文男", "status": "APPROVED", "commercial_allowed": True,
             "license_evidence": "x"},
        ],
    }
    (root / "config" / "voices.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    narration = _narration(root, [{"text": "第一句", "voice_profile": "male"}])
    with pytest.raises(TTSError, match="退休"):
        synthesize_narration(
            narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
            root=root, http_client=_zero_shot_client(), force=True)


def test_changing_a_line_profile_invalidates_the_manifest(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    _library(root)
    narration = _narration(root, [{"text": "第一句", "voice_profile": "voice_a"}])
    seen: list[str] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append(Path(prompt_wav).name)
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)
    client = _zero_shot_client()
    synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client, force=True)
    _narration(root, [{"text": "第一句", "voice_profile": "voice_b"}])
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client)
    assert result.reused is False
    assert seen == ["a.wav", "b.wav"]


def test_candidate_cannot_be_forced_into_production(tmp_path: Path) -> None:
    root = _root(tmp_path)
    library = load_library(_library(root), allow_missing=False)
    assert library is not None
    # require_approved=False is the audition path; it must not change the
    # profile's recorded status.
    resolved = resolve_voice(library.get("candidate"), root, require_approved=False)
    assert resolved.status == "TECHNICALLY_VALIDATED"


def test_voice_cast_sidecar_maps_index_and_line_id(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    _library(root)
    cast = {
        "schema_version": "1.0",
        "default_profile": "voice_a",
        "lines": {"1": "voice_b", "line_002": "voice_b"},
    }
    cast_path = root / "episode" / "voice_cast.yaml"
    cast_path.parent.mkdir(parents=True, exist_ok=True)
    cast_path.write_text(yaml.safe_dump(cast, allow_unicode=True), encoding="utf-8")
    narration = _narration(root, [
        {"text": "第一句"},
        {"text": "第二句", "line_id": "line_002"},
    ])
    seen: list[str] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append(Path(prompt_wav).name)
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=_zero_shot_client(), force=True,
        voice_cast_path=cast_path)
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert seen == ["b.wav", "b.wav"]
    assert manifest["voice_cast"]["line_profiles"] == ["voice_b", "voice_b"]
    assert manifest["voice_cast"]["source"] == "episode/voice_cast.yaml"


def test_header_can_use_a_separate_profile(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    _library(root)
    cast = {
        "schema_version": "1.0",
        "default_profile": "voice_a",
        "header_profile": "voice_b",
    }
    cast_path = root / "episode" / "voice_cast.yaml"
    cast_path.parent.mkdir(parents=True, exist_ok=True)
    cast_path.write_text(yaml.safe_dump(cast, allow_unicode=True), encoding="utf-8")
    narration = _narration(
        root, ["第一句"],
        header={"text": "标题", "pause_ms": 300})
    seen: list[str] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        seen.append(Path(prompt_wav).name)
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=_zero_shot_client(), force=True,
        voice_cast_path=cast_path)
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert seen == ["b.wav", "a.wav"]
    assert manifest["voice_cast"]["header_profile"] == "voice_b"
    assert manifest["header"]["voice_profile"] == "voice_b"
    assert manifest["lines"][0]["voice_profile"] == "voice_a"
