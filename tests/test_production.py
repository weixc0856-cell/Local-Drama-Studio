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
        require_static_gate=False,
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


def test_motion_plan_carries_plates_from_the_regions_file(tmp_path: Path) -> None:
    """A shot may describe its planes in the same authored file as its regions.

    The plan is the only thing that changes here: a shot without ``plates``
    keeps the single-plane render path.
    """
    import hashlib

    from drama_studio.motion.spec import load_plan
    from drama_studio.production import build_motion_plan
    from drama_studio.style_presets import load_style_presets

    project_root = Path(__file__).resolve().parents[1]
    preset = load_style_presets(project_root).get("court_green_fine_line")
    root, episode, script, audio = _motion_fixture(tmp_path)

    plates_dir = episode / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)
    background = plates_dir / "bg.png"
    Image.new("RGB", (576, 1024), (230, 230, 230)).save(background)
    hole = plates_dir / "hole.png"
    Image.new("L", (576, 1024), 0).save(hole)
    boat = plates_dir / "boat.png"
    Image.new("RGBA", (576, 1024), (0, 0, 0, 0)).save(boat)

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def rel(path: Path) -> str:
        return path.relative_to(root).as_posix()

    regions = episode / "regions.json"
    regions.write_text(json.dumps({
        "shots": {
            "shot_001": {
                "regions": [
                    {"id": "boat_lock", "role": "rigid_object", "permission": "locked",
                     "box": {"x0": 0.3, "y0": 0.485, "x1": 0.632, "y1": 0.56},
                     "plate_id": "boat"},
                ],
                "layers": [],
                "plates": [
                    {"id": "bg", "source": "original", "path": rel(background),
                     "sha256": digest(background), "z_order": 0, "depth_alpha": 1.0,
                     "coverage": "full_frame"},
                    {"id": "boat", "source": "original", "path": rel(boat),
                     "sha256": digest(boat), "z_order": 1, "depth_alpha": 0.7,
                     "coverage": "partial",
                     "anchor": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0},
                     "hole_mask": rel(hole), "hole_mask_sha256": digest(hole)},
                ],
            }
        }
    }, ensure_ascii=False), encoding="utf-8")

    build_motion_plan(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "motion_shots.json",
        preset=preset,
        regions_path=regions,
        align_audio=True,
        require_static_gate=False,
    )
    plan = load_plan(episode / "motion_shots.json")
    assert [plate.id for plate in plan.shots[0].plates] == ["bg", "boat"]
    assert plan.shots[0].regions[0].plate_id == "boat"
    assert plan.shots[1].plates == []


def test_header_extends_the_first_shot(tmp_path: Path) -> None:
    """The title is audio, so the first shot must cover it rather than trim it."""
    from drama_studio.motion.spec import load_plan
    from drama_studio.production import build_motion_plan
    from drama_studio.style_presets import load_style_presets

    project_root = Path(__file__).resolve().parents[1]
    preset = load_style_presets(project_root).get("court_green_fine_line")
    root, episode, script, audio = _motion_fixture(tmp_path)

    data = json.loads(audio.read_text(encoding="utf-8"))
    data["header"] = {"text": "登鹳雀楼。唐，王之涣。", "file": "episode/audio/header.wav",
                      "duration_seconds": 2.0, "pause_ms": 1100}
    audio.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    build_motion_plan(
        script, root=root, episode_root=episode,
        images_dir=episode / "assets" / "images", audio_manifest=audio,
        out_path=episode / "motion_shots.json", preset=preset,
        align_audio=True, leading_ms=300, transitions=False,
        require_static_gate=False,
    )
    plan = load_plan(episode / "motion_shots.json")
    # 0.3 leading + 2.0 header + 1.1 pause + 1.5 speech + 0.5 pause
    assert plan.shots[0].duration_seconds == 5.4


def test_motion_plan_requires_a_static_report_unless_explicitly_skipped(tmp_path: Path) -> None:
    from drama_studio.production import ProductionError, build_motion_plan
    from drama_studio.style_presets import load_style_presets

    project_root = Path(__file__).resolve().parents[1]
    preset = load_style_presets(project_root).get("court_green_fine_line")
    root, episode, script, audio = _motion_fixture(tmp_path)
    kwargs = dict(
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "motion_shots.json",
        preset=preset,
        align_audio=True,
    )
    try:
        build_motion_plan(script, **kwargs)
    except ProductionError as exc:
        assert "静态质量报告" in str(exc)
    else:
        raise AssertionError("missing static report must fail by default")
    build_motion_plan(script, require_static_gate=False, **kwargs)
    assert (episode / "motion_shots.json").is_file()


def test_build_video_jobs_requires_keyframes_and_writes_wan_jobs(tmp_path: Path) -> None:
    from drama_studio.production import build_video_jobs

    root, episode, script, _ = _motion_fixture(tmp_path)
    (root / "workflows").mkdir(exist_ok=True)
    (root / "workflows" / "r0_wan_i2v_api.json").write_text("{}", encoding="utf-8")
    data = script.model_dump()
    data["shots"][1]["type"] = "video"
    data["shots"][1]["video_prompt"] = "云气缓慢横向漂移，山体保持刚性"
    video_script = ProductionScript.model_validate(data)
    jobs_path = episode / "comfy" / "jobs_video.json"
    result = build_video_jobs(
        video_script,
        root=root,
        episode_root=episode,
        keyframes_dir=episode / "assets" / "images",
        jobs_path=jobs_path,
    )
    assert result["job_count"] == 1
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    assert jobs[0]["id"] == "shot_002"
    assert jobs[0]["type"] == "video"
    assert jobs[0]["reference"]["input_name"] == "shot_002.png"
    params = json.loads((root / jobs[0]["params"]).read_text(encoding="utf-8"))
    assert params["frames"] == 73
    assert params["width"] == 576 and params["height"] == 1024
    assert params["input_image"] == "shot_002.png"
    assert "云气" in params["positive_prompt"]


def test_video_shot_without_keyframe_fails(tmp_path: Path) -> None:
    from drama_studio.production import build_video_jobs

    root, episode, script, _ = _motion_fixture(tmp_path)
    (root / "workflows").mkdir(exist_ok=True)
    (root / "workflows" / "r0_wan_i2v_api.json").write_text("{}", encoding="utf-8")
    data = script.model_dump()
    data["shots"][1]["type"] = "video"
    video_script = ProductionScript.model_validate(data)
    empty = episode / "empty_keyframes"
    empty.mkdir()
    with pytest.raises(ProductionError, match="no keyframe image"):
        build_video_jobs(
            video_script, root=root, episode_root=episode,
            keyframes_dir=empty, jobs_path=episode / "comfy" / "jobs_video.json",
        )


def test_segments_can_mix_video_clip_and_image_when_explicit(tmp_path: Path) -> None:
    import subprocess

    root, episode, script, audio = _motion_fixture(tmp_path)
    clips = episode / "clips"
    clips.mkdir()
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=3",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(clips / "shot_002.mp4")],
        check=True, capture_output=True,
    )
    result = build_segments(
        script,
        root=root,
        episode_root=episode,
        images_dir=episode / "assets" / "images",
        audio_manifest=audio,
        out_path=episode / "segments.json",
        clips_dir=clips,
        allow_partial_clips=True,
        align_audio=False,
    )
    assert result["count"] == 2
    segments = json.loads((episode / "segments.json").read_text(encoding="utf-8"))
    kinds = {seg["id"]: seg["type"] for seg in segments}
    assert kinds == {"shot_001": "image", "shot_002": "video"}
