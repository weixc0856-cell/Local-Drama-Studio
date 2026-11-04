from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

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
        'tts:\n  mode: sft\n  speakers:\n    narrator: "测试音色"\n', encoding="utf-8"
    )
    return tmp_path


def _transport(calls: dict[str, int]) -> httpx.MockTransport:
    wav = _wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            calls["health"] = calls.get("health", 0) + 1
            return httpx.Response(200, json={"status": "ready", "model_class": "CosyVoice", "model_dir": "D:/AI/CosyVoice-Runtime/pretrained_models/CosyVoice-300M-SFT", "speakers": ["测试音色"], "modes": ["sft", "zero_shot"]})
        if request.url.path == "/tts":
            calls["tts"] = calls.get("tts", 0) + 1
            return httpx.Response(200, content=wav, headers={"X-Synth-Seconds": "0.1"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _narration(root: Path, lines: list[str]) -> Path:
    path = root / "episode" / "narration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"speaker": "测试音色", "speed": 1.0, "lines": lines}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_synthesize_writes_48k_manifest_and_reuses(tmp_path: Path) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽", "长风过野原"])
    calls: dict[str, int] = {}
    client = httpx.Client(transport=_transport(calls), base_url="http://tts.test")

    result = synthesize_narration(
        narration,
        root / "episode" / "audio",
        root / "episode" / "audio_manifest.json",
        root=root,
        http_client=client,
    )
    assert result.line_count == 2
    assert result.reused is False
    assert calls["tts"] == 2
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["speaker"] == "测试音色"
    assert manifest["speaker_id"] == "测试音色"
    assert manifest["tts_mode"] == "sft"
    assert manifest["model_class"] == "CosyVoice"
    assert "CosyVoice-300M-SFT" in manifest["model_dir"]
    assert result.tts_mode == "sft"
    assert manifest["narration_sha256"]
    for line in manifest["lines"]:
        assert line["file"].startswith("episode/audio/")
        with wave.open(str(root / line["file"]), "rb") as fh:
            assert fh.getframerate() == 48000
            assert fh.getnchannels() == 1

    again = synthesize_narration(
        narration,
        root / "episode" / "audio",
        root / "episode" / "audio_manifest.json",
        root=root,
        http_client=client,
    )
    assert again.reused is True
    assert calls["tts"] == 2

    forced = synthesize_narration(
        narration,
        root / "episode" / "audio",
        root / "episode" / "audio_manifest.json",
        root=root,
        http_client=client,
        force=True,
    )
    assert forced.reused is False
    assert calls["tts"] == 4


def test_changed_narration_resynthesizes(tmp_path: Path) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    calls: dict[str, int] = {}
    client = httpx.Client(transport=_transport(calls), base_url="http://tts.test")
    synthesize_narration(narration, root / "audio", root / "audio_manifest.json", root=root, http_client=client)
    _narration(root, ["长风过野原"])
    result = synthesize_narration(narration, root / "audio", root / "audio_manifest.json", root=root, http_client=client)
    assert result.reused is False
    assert calls["tts"] == 2


def test_unready_service_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "loading"})),
        base_url="http://tts.test",
    )
    with pytest.raises(TTSError, match="未就绪"):
        synthesize_narration(narration, root / "audio", root / "audio_manifest.json", root=root, http_client=client)


def test_tts_text_and_subtitle_text_are_separate(tmp_path: Path) -> None:
    """The spoken layer may differ from the displayed subtitle (simplified vs traditional)."""
    root = _root(tmp_path)
    narration = _narration(
        root, [{"text": "艳艳随波千万里", "subtitle_text": "灩灩隨波千萬里"}]
    )
    bodies: list[dict] = []
    wav = _wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ready", "model_class": "CosyVoice", "model_dir": "D:/AI/CosyVoice-Runtime/pretrained_models/CosyVoice-300M-SFT", "speakers": ["测试音色"], "modes": ["sft", "zero_shot"]})
        bodies.append(json.loads(request.content))
        return httpx.Response(200, content=wav, headers={"X-Synth-Seconds": "0.1"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    result = synthesize_narration(
        narration, root / "audio", root / "audio_manifest.json", root=root, http_client=client
    )
    assert bodies[0]["text"] == "艳艳随波——千万里"
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["lines"][0]["text"] == "艳艳随波千万里"
    assert manifest["lines"][0]["breath_text"] == "艳艳随波——千万里"
    assert manifest["lines"][0]["subtitle_text"] == "灩灩隨波千萬里"


def test_zero_shot_needs_a_prompt_text(tmp_path):
    """Explicit cloning without a transcript must fail loudly, not silently."""
    from drama_studio.voice.tts import TTSError, synthesize_narration

    root = _root(tmp_path)
    (root / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_text: ""\n'
        '    prompt_audio: "prompt.wav"\n',
        encoding="utf-8")
    narration = _narration(root, ["白日依山尽"])
    with pytest.raises(TTSError, match="prompt_text"):
        synthesize_narration(narration, root / "episode" / "audio",
                             root / "episode" / "audio_manifest.json",
                             root=root, force=True)


def test_sft_rejects_a_zero_shot_runtime(tmp_path: Path) -> None:
    """The loaded model is verified, not assumed from the configured mode."""
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ready", "model_class": "CosyVoice2",
                "model_dir": "D:/AI/CosyVoice-Runtime/pretrained_models/CosyVoice2-0.5B",
                "speakers": [], "modes": ["zero_shot"],
            })
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    with pytest.raises(TTSError, match="请求 SFT"):
        synthesize_narration(narration, root / "episode" / "audio",
                             root / "episode" / "audio_manifest.json",
                             root=root, force=True, http_client=client)


def test_zero_shot_is_explicit_and_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    prompt = root / "assets" / "prompt.wav"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_bytes(_wav_bytes())
    (root / "config" / "audio.yaml").write_text(
        'tts:\n  mode: sft\n'
        '  zero_shot:\n    prompt_audio: "assets/prompt.wav"\n'
        '    prompt_text: "测试参考文本"\n    speed: 0.9\n',
        encoding="utf-8")
    narration = _narration(root, ["白日依山尽"])

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ready", "model_class": "CosyVoice2",
                "model_dir": "D:/AI/CosyVoice-Runtime/pretrained_models/CosyVoice2-0.5B",
                "speakers": [], "modes": ["zero_shot"],
            })
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, force=True, http_client=client, tts_mode="zero_shot")
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert result.tts_mode == "zero_shot"
    assert manifest["tts_mode"] == "zero_shot"
    assert manifest["model_class"] == "CosyVoice2"
    assert "CosyVoice2-0.5B" in manifest["model_dir"]
    assert manifest["speaker_id"] is None
    assert manifest["prompt"]["sha256"]
    assert manifest["prompt"]["text"] == "测试参考文本"


def test_config_mode_zero_shot_is_the_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No explicit tts_mode: config/audio.yaml drives the default."""
    root = _root(tmp_path)
    prompt = root / "assets" / "prompt.wav"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_bytes(_wav_bytes())
    (root / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_audio: "assets/prompt.wav"\n    prompt_text: "测试参考文本"\n    speed: 0.9\n',
        encoding="utf-8")
    narration = _narration(root, ["白日依山尽"])

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        out_wav.write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.voice.tts.zeroshot_synthesize", fake_zero_shot)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ready", "model_class": "CosyVoice2",
                "model_dir": "D:/AI/CosyVoice-Runtime/pretrained_models/CosyVoice2-0.5B",
                "speakers": [], "modes": ["zero_shot"],
            })
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, force=True, http_client=client)
    assert result.tts_mode == "zero_shot"
    assert json.loads(result.manifest.read_text(encoding="utf-8"))["tts_mode"] == "zero_shot"


def test_header_is_spoken_before_the_body(tmp_path: Path) -> None:
    """The title is its own segment; the body lines must start after it."""
    from drama_studio.voice.tts import header_offset_seconds

    root = _root(tmp_path)
    narration = root / "episode" / "narration.json"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_text(json.dumps({
        "mode": "recitation",
        "header": {"text": "登鹳雀楼。唐，王之涣。", "pause_ms": 1100},
        "lines": ["白日依山尽，黄河入海流。"],
    }, ensure_ascii=False), encoding="utf-8")
    calls: dict[str, int] = {}
    client = httpx.Client(transport=_transport(calls), base_url="http://tts.test")

    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client, force=True)

    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert calls["tts"] == 2, "header + one body line"
    assert manifest["header"]["text"] == "登鹳雀楼。唐，王之涣。"
    assert manifest["header"]["pause_ms"] == 1100
    ledger = manifest["ledger"]
    assert ledger[0]["kind"] == "header"
    assert ledger[0]["start"] == 0.0
    assert ledger[1]["kind"] == "line"
    assert ledger[1]["start"] >= ledger[0]["end"] + 1.1 - 1e-6
    assert header_offset_seconds(manifest) > 1.1
    # Body line indices are untouched, so shot ↔ line bindings still resolve.
    assert [line["index"] for line in manifest["lines"]] == [1]
