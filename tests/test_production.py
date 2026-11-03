from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from drama_studio.production import ProductionError, build_jobs, build_segments
from drama_studio.script_engine import ProductionScript


def _script(tmp_path: Path) -> ProductionScript:
    data = {
        "schema_version": "1.0",
        "title": "测试标题",
        "logline": "测试夹具。",
        "lines": [
            {"line_id": "line_001", "text": "白日依山尽", "source_segment_id": "sub_001"},
            {"line_id": "line_002", "text": "长风过野原", "source_segment_id": "sub_002"},
        ],
        "shots": [
            {
                "shot_id": "shot_001",
                "index": 1,
                "type": "image",
                "duration_seconds": 3.0,
                "motion": "slow push-in",
                "scene_prompt": "山与落日",
                "visual_prompt": "东方意境；山与落日",
                "negative_prompt": "文字",
                "line_ids": ["line_001"],
            },
            {
                "shot_id": "shot_002",
                "index": 2,
                "type": "image",
                "duration_seconds": 3.0,
                "motion": "static",
                "scene_prompt": "原野与风",
                "visual_prompt": "东方意境；原野与风",
                "negative_prompt": "文字",
                "line_ids": ["line_002"],
            },
        ],
        "style_id": "style_test",
        "style_sha256": "a" * 64,
        "package_sha256": "b" * 64,
        "model": "test",
        "generated_at": "2026-11-03T00:00:00+00:00",
    }
    return ProductionScript.model_validate(data)


def test_build_jobs_and_segments(tmp_path: Path) -> None:
    root = tmp_path
    episode = root / "episode"
    (root / "workflows").mkdir()
    (root / "workflows" / "test.json").write_text("{}", encoding="utf-8")
    script = _script(root)
    (episode).mkdir()
    (episode / "production_script.json").write_text(
        json.dumps(script.model_dump(), ensure_ascii=False), encoding="utf-8"
    )
    jobs = build_jobs(
        script, root=root, episode_root=episode,
        jobs_path=episode / "comfy" / "jobs.json", workflow="workflows/test.json",
    )
    assert jobs["job_count"] == 2
    data = json.loads((episode / "comfy" / "jobs.json").read_text(encoding="utf-8"))
    assert data[0]["id"] == "shot_001"
    params = json.loads((root / data[0]["params"]).read_text(encoding="utf-8"))
    assert params["positive_prompt"] == "东方意境；山与落日"
    assert params["width"] == 576 and params["height"] == 1024

    for shot in ("shot_001", "shot_002"):
        path = episode / "assets" / "images" / shot / "out.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (24, 42), (50, 70, 90)).save(path)
    audio = episode / "audio_manifest.json"
    audio.write_text(json.dumps({"lines": [{"index": 1}]}), encoding="utf-8")
    result = build_segments(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "segments.json",
    )
    assert result["count"] == 2
    segments = json.loads((episode / "segments.json").read_text(encoding="utf-8"))
    assert segments[0]["source"].endswith("out.png")
    assert len(segments[0]["sha256"]) == 64
    assert (episode / "segments.meta.json").is_file()


def test_missing_image_fails_loudly(tmp_path: Path) -> None:
    root = tmp_path
    episode = root / "episode"
    episode.mkdir()
    script = _script(root)
    (episode / "production_script.json").write_text(
        json.dumps(script.model_dump(), ensure_ascii=False), encoding="utf-8"
    )
    audio = episode / "audio_manifest.json"
    audio.write_text(json.dumps({"lines": [{"index": 1}]}), encoding="utf-8")
    with pytest.raises(ProductionError, match="没有生成图片"):
        build_segments(
            script,
            root=root,
            episode_root=episode,
            images_dir=episode / "assets" / "images",
            audio_manifest=audio,
            out_path=episode / "segments.json",
        )


def test_build_jobs_accepts_script_dict(tmp_path: Path) -> None:
    root = tmp_path
    episode = root / "episode"
    episode.mkdir()
    (root / "workflows").mkdir()
    (root / "workflows" / "test.json").write_text("{}", encoding="utf-8")
    script = _script(root)
    jobs = build_jobs(
        script.model_dump(),
        root=root,
        episode_root=episode,
        jobs_path=episode / "comfy" / "jobs.json",
        workflow="workflows/test.json",
    )
    assert jobs["job_count"] == 2
