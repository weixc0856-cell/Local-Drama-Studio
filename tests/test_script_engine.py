from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from drama_studio.content_package import build_content_package
from drama_studio.script_engine import ScriptGenerationError, compose_visual_prompt, generate_script

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "literary_intelligence" / "tests" / "fixtures" / "corpus_short"
STYLE = {
    "id": "style_test",
    "name": "测试风格",
    "positive_prompt": "东方意境，柔和自然光",
    "visual_language": "水墨质感",
    "negative_prompt": "文字，水印",
}


def _package(tmp_path: Path) -> Path:
    path = tmp_path / "content_package.json"
    build_content_package(CORPUS, path)
    return path


def _style(tmp_path: Path) -> Path:
    path = tmp_path / "style.json"
    path.write_text(json.dumps(STYLE, ensure_ascii=False), encoding="utf-8")
    return path


def _draft(shots: int = 3) -> dict:
    return {
        "title": "白日短句",
        "logline": "测试夹具的三段式短视频。",
        "line_order": [1, 2],
        "shots": [
            {
                "scene_prompt": f"画面描述 {index}",
                "duration_seconds": 3.0,
                "motion": "slow push-in",
                "line_indexes": [1] if index == 1 else [2],
            }
            for index in range(1, shots + 1)
        ],
    }


def _transport(responses: list[dict]) -> httpx.MockTransport:
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        payload = queue.pop(0)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]},
        )

    return httpx.MockTransport(handler)


def _client(responses: list[dict]) -> httpx.Client:
    return httpx.Client(transport=_transport(responses), base_url="http://llm.test")


def test_generate_script_writes_script_and_narration(tmp_path: Path) -> None:
    script = generate_script(
        _package(tmp_path),
        _style(tmp_path),
        tmp_path / "production_script.json",
        base_url="http://llm.test",
        model="test-model",
        speaker="测试音色",
        http_client=_client([_draft()]),
    )
    assert len(script.shots) == 3
    assert len(script.lines) == 2
    assert script.style_sha256
    assert script.package_sha256
    assert "水墨质感" in script.shots[0].visual_prompt
    assert "画面描述 1" in script.shots[0].visual_prompt
    narration = json.loads((tmp_path / "narration.json").read_text(encoding="utf-8"))
    assert narration["speaker"] == "测试音色"
    assert narration["lines"] == ["白日依山尽", "长风过野原"]


def test_invalid_first_response_is_repaired(tmp_path: Path) -> None:
    bad = _draft(shots=2)
    script = generate_script(
        _package(tmp_path),
        _style(tmp_path),
        tmp_path / "production_script.json",
        base_url="http://llm.test",
        model="test-model",
        http_client=_client([bad, _draft()]),
    )
    assert len(script.shots) == 3
    assert (tmp_path / "script_raw_attempt1.json").is_file()
    assert (tmp_path / "script_raw_attempt2.json").is_file()


def test_unknown_line_index_fails_after_repairs(tmp_path: Path) -> None:
    bad = _draft()
    bad["shots"][0]["line_indexes"] = [99]
    with pytest.raises(ScriptGenerationError):
        generate_script(
            _package(tmp_path),
            _style(tmp_path),
            tmp_path / "production_script.json",
            base_url="http://llm.test",
            model="test-model",
            http_client=_client([bad, bad, bad]),
        )


def test_style_is_composed_traceably() -> None:
    first = compose_visual_prompt({"positive_prompt": "风格A"}, "同一画面")
    second = compose_visual_prompt({"positive_prompt": "风格B"}, "同一画面")
    assert first != second
    assert first.endswith("同一画面")
    assert second.endswith("同一画面")


def test_generate_script_preserves_video_shot_type(tmp_path: Path) -> None:
    draft = _draft(3)
    draft["shots"][0]["type"] = "video"
    draft["shots"][0]["video_prompt"] = "云雾缓慢横向漂移，山体保持刚性"
    script = generate_script(
        _package(tmp_path), _style(tmp_path), tmp_path / "production_script.json",
        base_url="http://llm.test", model="test", http_client=_client([draft]),
    )
    assert script.shots[0].type == "video"
    assert script.shots[0].video_prompt.startswith("云雾")
    assert script.shots[1].type == "image"
