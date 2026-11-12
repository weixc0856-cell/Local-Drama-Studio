from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from drama_studio.application.voice.tts import TTSError, synthesize_narration


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
    prompt = tmp_path / "assets" / "prompt.wav"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_bytes(_wav_bytes(seconds=1.0))
    (tmp_path / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n'
        '    prompt_audio: "assets/prompt.wav"\n    prompt_text: "测试参考文本"\n',
        encoding="utf-8",
    )
    return tmp_path


def _client(health: dict | None = None) -> httpx.Client:
    payload = health or {
        "status": "ready",
        "model_class": "VoxCPM2",
        "model_dir": "models/voxcpm2",
        "speakers": [],
        "modes": ["zero_shot"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")


@pytest.fixture()
def zero_shot_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Record what would be sent to /tts/upload; the HTTP shape is zeroshot's own test."""
    calls: list[dict] = []

    def fake(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        calls.append({"text": text, "prompt_wav": str(prompt_wav),
                      "prompt_text": prompt_text, "speed": speed})
        Path(out_wav).write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.application.voice.tts.zeroshot_synthesize", fake)
    return calls


def _narration(root: Path, lines: list) -> Path:
    path = root / "episode" / "narration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"speaker": "测试音色", "speed": 1.0, "lines": lines}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_synthesize_writes_48k_manifest_and_reuses(
        tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽", "长风过野原"])
    client = _client()

    result = synthesize_narration(
        narration,
        root / "episode" / "audio",
        root / "episode" / "audio_manifest.json",
        root=root,
        http_client=client,
    )
    assert result.line_count == 2
    assert result.reused is False
    assert len(zero_shot_calls) == 2
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["speaker"] == "zero_shot:prompt"
    assert manifest["speaker_id"] is None
    assert manifest["tts_mode"] == "zero_shot"
    assert manifest["model_class"] == "VoxCPM2"
    assert "voxcpm2" in manifest["model_dir"]
    assert manifest["prompt"]["text"] == "测试参考文本"
    assert result.tts_mode == "zero_shot"
    assert manifest["narration_sha256"]
    assert [call["prompt_text"] for call in zero_shot_calls] == ["测试参考文本"] * 2
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
    assert len(zero_shot_calls) == 2

    forced = synthesize_narration(
        narration,
        root / "episode" / "audio",
        root / "episode" / "audio_manifest.json",
        root=root,
        http_client=client,
        force=True,
    )
    assert forced.reused is False
    assert len(zero_shot_calls) == 4


def test_changed_narration_resynthesizes(tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    client = _client()
    synthesize_narration(narration, root / "audio", root / "audio_manifest.json",
                         root=root, http_client=client)
    _narration(root, ["长风过野原"])
    result = synthesize_narration(narration, root / "audio", root / "audio_manifest.json",
                                  root=root, http_client=client)
    assert result.reused is False
    assert len(zero_shot_calls) == 2


def test_unready_service_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    client = _client({"status": "loading"})
    with pytest.raises(TTSError, match="未就绪"):
        synthesize_narration(narration, root / "audio", root / "audio_manifest.json",
                             root=root, http_client=client)


def test_tts_text_and_subtitle_text_are_separate(
        tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    """The spoken layer may differ from the displayed subtitle (simplified vs traditional)."""
    root = _root(tmp_path)
    narration = _narration(
        root, [{"text": "艳艳随波千万里", "subtitle_text": "灩灩隨波千萬里"}]
    )
    result = synthesize_narration(
        narration, root / "audio", root / "audio_manifest.json", root=root, http_client=_client()
    )
    assert zero_shot_calls[0]["text"] == "艳艳随波——千万里"
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["lines"][0]["text"] == "艳艳随波千万里"
    assert manifest["lines"][0]["breath_text"] == "艳艳随波——千万里"
    assert manifest["lines"][0]["subtitle_text"] == "灩灩隨波千萬里"


def test_zero_shot_needs_a_prompt_text(tmp_path):
    """Explicit cloning without a transcript must fail loudly, not silently."""
    root = _root(tmp_path)
    (root / "config" / "audio.yaml").write_text(
        'tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_text: ""\n'
        '    prompt_audio: "assets/prompt.wav"\n',
        encoding="utf-8")
    narration = _narration(root, ["白日依山尽"])
    with pytest.raises(TTSError, match="prompt_text"):
        synthesize_narration(narration, root / "episode" / "audio",
                             root / "episode" / "audio_manifest.json",
                             root=root, force=True)


def test_sft_mode_is_retired(tmp_path: Path) -> None:
    """SFT preset voices are gone; asking for one must say so, not fail vaguely."""
    root = _root(tmp_path)
    (root / "config" / "audio.yaml").write_text(
        'tts:\n  mode: sft\n  speakers:\n    narrator: "测试音色"\n', encoding="utf-8")
    narration = _narration(root, ["白日依山尽"])
    with pytest.raises(TTSError, match="已退休"):
        synthesize_narration(narration, root / "episode" / "audio",
                             root / "episode" / "audio_manifest.json",
                             root=root, force=True, http_client=_client())


def test_zero_shot_rejects_a_foreign_runtime(tmp_path: Path) -> None:
    """The loaded model is verified, not assumed from the configured mode."""
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    client = _client({
        "status": "ready", "model_class": "CosyVoice2",
        "model_dir": "other-runtime/CosyVoice2-0.5B",
        "speakers": [], "modes": ["zero_shot"],
    })
    with pytest.raises(TTSError, match="请求 zero-shot"):
        synthesize_narration(narration, root / "episode" / "audio",
                             root / "episode" / "audio_manifest.json",
                             root=root, force=True, http_client=client)


def test_zero_shot_is_explicit_and_recorded(
        tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, force=True, http_client=_client(), tts_mode="zero_shot")
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert result.tts_mode == "zero_shot"
    assert manifest["tts_mode"] == "zero_shot"
    assert manifest["model_class"] == "VoxCPM2"
    assert "voxcpm2" in manifest["model_dir"]
    assert manifest["speaker_id"] is None
    assert manifest["prompt"]["sha256"]
    assert manifest["prompt"]["text"] == "测试参考文本"


def test_config_mode_zero_shot_is_the_default(
        tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    """No explicit tts_mode: config/audio.yaml drives the default."""
    root = _root(tmp_path)
    narration = _narration(root, ["白日依山尽"])
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, force=True, http_client=_client())
    assert result.tts_mode == "zero_shot"
    assert json.loads(result.manifest.read_text(encoding="utf-8"))["tts_mode"] == "zero_shot"


def test_header_is_spoken_before_the_body(
        tmp_path: Path, zero_shot_calls: list[dict]) -> None:
    """The title is its own segment; the body lines must start after it."""
    from drama_studio.application.voice.tts import header_offset_seconds

    root = _root(tmp_path)
    narration = root / "episode" / "narration.json"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_text(json.dumps({
        "mode": "recitation",
        "header": {"text": "登鹳雀楼。唐，王之涣。", "pause_ms": 1100},
        "lines": ["白日依山尽，黄河入海流。"],
    }, ensure_ascii=False), encoding="utf-8")

    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=_client(), force=True)

    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert len(zero_shot_calls) == 2, "header + one body line"
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
