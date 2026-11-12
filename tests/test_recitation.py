from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from drama_studio.domain.voice.recitation import RecitationError, mode_spec, plan_line
from drama_studio.application.voice.tts import synthesize_narration


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


def _wav_bytes(seconds: float = 0.2, rate: int = 22050) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def test_recitation_keeps_one_whole_line_and_adds_dash_breaths(tmp_path: Path) -> None:
    root = _root(tmp_path)
    spec = mode_spec(root, "recitation")
    plan = plan_line("春江潮水连海平，海上明月共潮生。", spec)
    breath = "春江潮水——连海平，海上明月——共潮生。"
    assert plan["breath_text"] == breath
    assert [part["text"] for part in plan["parts"]] == [breath]
    assert plan["parts"][0]["pause_after_ms"] == 0
    assert plan["part_count"] == 1


def test_narration_mode_does_not_split(tmp_path: Path) -> None:
    root = _root(tmp_path)
    plan = plan_line("春江潮水连海平，海上明月共潮生。", mode_spec(root, "narration"))
    assert len(plan["parts"]) == 1


def test_chant_is_declared_unsupported(tmp_path: Path) -> None:
    root = _root(tmp_path)
    with pytest.raises(RecitationError, match="不得用普通朗诵冒充"):
        mode_spec(root, "chant")


def test_recitation_synthesizes_parts_and_records_layers(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    narration = root / "episode" / "narration.json"
    narration.parent.mkdir(parents=True)
    narration.write_text(
        json.dumps(
            {
                "speaker": "测试音色",
                "mode": "recitation",
                "lines": [
                    {
                        "text": "春江潮水连海平，海上明月共潮生。",
                        "subtitle_text": "春江潮水連海平，海上明月共潮生。",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bodies: list[str] = []

    def fake_zero_shot(text, *, prompt_wav, prompt_text, out_wav, speed, base, timeout):
        bodies.append(text)
        Path(out_wav).write_bytes(_wav_bytes())
        return SimpleNamespace(synth_seconds=0.1)

    monkeypatch.setattr("drama_studio.application.voice.tts.zeroshot_synthesize", fake_zero_shot)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ready", "model_class": "VoxCPM2", "model_dir": "models/voxcpm2", "speakers": [], "modes": ["zero_shot"]})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://tts.test")
    result = synthesize_narration(
        narration, root / "episode" / "audio", root / "episode" / "audio_manifest.json",
        root=root, http_client=client,
    )
    assert result.mode == "recitation"
    assert bodies == ["春江潮水——连海平，海上明月——共潮生。"]
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert manifest["mode"] == "recitation"
    assert manifest["speed"] == 0.92
    line = manifest["lines"][0]
    assert line["display_text"] == "春江潮水連海平，海上明月共潮生。"
    assert line["subtitle_text"] == line["display_text"]
    assert line["breath_text"] == "春江潮水——连海平，海上明月——共潮生。"
    assert len(line["parts"]) == 1
    assert line["parts"][0]["pause_after_ms"] == 0
    # One whole-line request: 0.2 s response, no digital silence concatenation.
    assert line["duration_seconds"] == pytest.approx(0.2, abs=0.05)
    report = result.pronunciation_report
    assert report is not None and report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["summary"]["display_equals_source"] is True
    assert payload["capabilities"]["api_pinyin_control"] is False
