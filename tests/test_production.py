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


def _audio_manifest(path: Path, lines: list[dict]) -> Path:
    path.write_text(json.dumps({"lines": lines}, ensure_ascii=False), encoding="utf-8")
    return path


def test_segments_align_to_audio_and_use_clips(tmp_path: Path) -> None:
    root = tmp_path
    episode = root / "episode"
    episode.mkdir()
    script = _script(root)
    (episode / "production_script.json").write_text(
        json.dumps(script.model_dump(), ensure_ascii=False), encoding="utf-8"
    )
    audio = _audio_manifest(
        episode / "audio_manifest.json",
        [
            {"index": 1, "duration_seconds": 2.0, "pause_after_ms": 500},
            {"index": 2, "duration_seconds": 3.0},
        ],
    )
    clips = episode / "clips"
    clips.mkdir()
    for shot in ("shot_001", "shot_002"):
        (clips / f"{shot}.mp4").write_bytes(b"stub")
    result = build_segments(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "segments.json",
        clips_dir=clips,
        align_audio=True,
        leading_ms=400,
    )
    assert result["count"] == 2
    segments = json.loads((episode / "segments.json").read_text(encoding="utf-8"))
    assert segments[0]["type"] == "video"
    assert segments[0]["source"].endswith("shot_001.mp4")
    # first shot absorbs the 400 ms leading silence: 0.4 + 2.0 + 0.5
    assert segments[0]["duration"] == 2.9
    # second shot uses the default 800 ms gap: 3.0 + 0.8
    assert segments[1]["duration"] == 3.8
    assert segments[0]["planned_duration"] == 3.0


def test_missing_clip_fails_loudly(tmp_path: Path) -> None:
    root = tmp_path
    episode = root / "episode"
    episode.mkdir()
    script = _script(root)
    audio = _audio_manifest(
        episode / "audio_manifest.json",
        [{"index": 1, "duration_seconds": 2.0}, {"index": 2, "duration_seconds": 2.0}],
    )
    clips = episode / "clips"
    clips.mkdir()
    (clips / "shot_001.mp4").write_bytes(b"stub")
    with pytest.raises(ProductionError, match="没有生成动态片段"):
        build_segments(
            script,
            root=root,
            episode_root=episode,
            images_dir=episode / "assets" / "images",
            audio_manifest=audio,
            out_path=episode / "segments.json",
            clips_dir=clips,
            align_audio=True,
        )


def test_production_script_accepts_full_length_poem() -> None:
    data = _script(Path("/nonexistent")).model_dump()
    data["lines"] = [
        {"line_id": f"line_{i:03d}", "text": f"第{i}句", "source_segment_id": f"sub_{i:03d}"}
        for i in range(1, 19)
    ]
    data["shots"] = [
        {
            "shot_id": f"shot_{i:03d}",
            "index": i,
            "type": "image",
            "duration_seconds": 5.0,
            "motion": "scroll pan",
            "scene_prompt": f"画面 {i}",
            "visual_prompt": f"风格；画面 {i}",
            "line_ids": [f"line_{i:03d}"],
        }
        for i in range(1, 19)
    ]
    script = ProductionScript.model_validate(data)
    assert len(script.lines) == 18 and len(script.shots) == 18


def _motion_fixture(tmp_path: Path) -> tuple[Path, Path, ProductionScript, Path]:
    root = tmp_path
    episode = root / "episode"
    episode.mkdir()
    (root / "config").mkdir()
    (root / "config" / "styles.yaml").write_text(
        (Path(__file__).resolve().parents[1] / "config" / "styles.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    script = _script(root)
    (episode / "production_script.json").write_text(
        json.dumps(script.model_dump(), ensure_ascii=False), encoding="utf-8"
    )
    images = episode / "assets" / "images"
    for shot in ("shot_001", "shot_002"):
        path = images / shot / "out.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1024, 1024), (60, 80, 100)).save(path)
    audio = episode / "audio_manifest.json"
    audio.write_text(
        json.dumps(
            {
                "lines": [
                    {"index": 1, "duration_seconds": 1.5, "pause_after_ms": 500},
                    {"index": 2, "duration_seconds": 1.5, "pause_after_ms": 500},
                ]
            }
        ),
        encoding="utf-8",
    )
    return root, episode, script, audio


def test_build_motion_plan_aligns_audio_and_caps_transitions(tmp_path: Path) -> None:
    from drama_studio.motion.spec import load_plan
    from drama_studio.production import build_motion_plan
    from drama_studio.style_presets import load_style_presets

    project_root = Path(__file__).resolve().parents[1]
    preset = load_style_presets(project_root).get("court_green_fine_line")
    root, episode, script, audio = _motion_fixture(tmp_path)
    result = build_motion_plan(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "motion_shots.json",
        preset=preset,
        align_audio=True,
        leading_ms=300,
        tail_seconds=0.5,
        transitions=True,
    )
    assert result["transitions"] == 1
    plan = load_plan(episode / "motion_shots.json")
    assert plan.shots[0].duration_seconds == 2.3  # 0.3 leading + 1.5 speech + 0.5 pause
    assert plan.shots[1].duration_seconds == 2.5  # 2.0 + 0.5 tail
    transition = plan.shots[1].transition_in
    assert transition is not None and transition.type == "crossfade"
    assert 0.3 <= transition.duration_s <= 0.8
    assert plan.total_seconds == 4.8


def test_sequence_segments_replace_the_shot_list(tmp_path: Path) -> None:
    import subprocess

    root, episode, script, audio = _motion_fixture(tmp_path)
    sequence = episode / "sequence.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=4.5",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(sequence)],
        check=True, capture_output=True,
    )
    result = build_segments(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "segments.json",
        sequence=sequence,
        leading_ms=300,
    )
    assert result["count"] == 1
    segments = json.loads((episode / "segments.json").read_text(encoding="utf-8"))
    assert segments[0]["type"] == "video"
    assert segments[0]["duration"] == pytest.approx(4.5, abs=0.05)
    assert len(segments[0]["shots"]) == 2

    too_short = episode / "short.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(too_short)],
        check=True, capture_output=True,
    )
    with pytest.raises(ProductionError, match="短于旁白"):
        build_segments(
            script,
            root=root,
            episode_root=episode,
            images_dir=episode / "assets" / "images",
            audio_manifest=audio,
            out_path=episode / "segments.json",
            sequence=too_short,
            leading_ms=300,
        )
