"""Film stages that sit between generation and the build engine."""

from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest
from PIL import Image

from drama_studio.film.assets import resolve_asset
from drama_studio.film.clips import encode_frames, fit_clip, probe_duration
from drama_studio.film.config import ProductionSettings
from drama_studio.film.status import film_status, record_review, write_state
from drama_studio.film.timeline import build_edit_timeline
from drama_studio.film.motion_plan import build_motion_plan

FFMPEG = shutil.which("ffmpeg")


def _png(path: Path, colour=(200, 200, 200)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 114), colour).save(path)
    return path


def _wav(path: Path, seconds: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(b"\x00\x00" * int(48000 * seconds))
    return path


def _video(path: Path, seconds: float = 2.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"color=c=gray:s=1080x1920:r=24:d={seconds}", "-an",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _manifest(*ids: str) -> dict:
    return {"lines": [
        {"id": item, "duration_seconds": 1.0, "planned_pause_after_ms": 300,
         "text": item, "file": f"{item}.wav"}
        for item in ids
    ]}


def _storyboard():
    from drama_studio.film.schemas import (
        CameraSpec, ContinuitySpec, Layers, MotionSpec, ShotSpec, Storyboard,
    )

    shots = []
    for index, (shot_id, duration) in enumerate((("S01", 3.0), ("S02", 3.0)), start=1):
        shots.append(ShotSpec(
            shot_id=shot_id, scene_id="SC01", narration_ids=[f"N{index:03d}"],
            duration_seconds=duration, shot_size="ws",
            camera=CameraSpec(move="dolly_in"), layers=Layers(midground="ridge"),
            motion=MotionSpec(primary="camera_push_in"),
            continuity=ContinuitySpec(
                lighting="dawn", environment="SC01",
                previous_shot=None if index == 1 else "S01",
                next_shot="S02" if index == 1 else None,
            ),
        ))
    return Storyboard(project_id="p1", shots=shots)


def test_edit_timeline_places_lines_on_shot_boundaries() -> None:
    board = _storyboard()
    timeline = build_edit_timeline(board, _manifest("N001", "N002"), settings=ProductionSettings())
    assert timeline.narration_events[0].start_ms == 300
    assert timeline.narration_events[1].start_ms == timeline.entries[1].start_ms
    assert timeline.total_ms >= timeline.narration_events[-1].end_ms + 1000


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg is required")
def test_encode_frames_keeps_order_and_duration(tmp_path: Path) -> None:
    frames = [
        _png(tmp_path / "frames" / f"S01_{index:05d}_.png", (index * 20, 0, 0))
        for index in range(1, 4)
    ]
    out = encode_frames(frames, tmp_path / "S01_wan.mp4", fps=24)
    assert probe_duration(out) == pytest.approx(3 / 24, abs=0.02)


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg is required")
def test_fit_clip_extends_with_last_frame_hold(tmp_path: Path) -> None:
    source = _video(tmp_path / "source.mp4", 2.0)
    out = tmp_path / "fitted.mp4"
    result = fit_clip(source, out, target_seconds=3.0, policy="hold_last", fps=24)
    assert result["policy"] == "hold_last"
    assert result["source_seconds"] == pytest.approx(2.0, abs=0.05)
    assert result["effective_seconds"] == pytest.approx(3.0, abs=0.1)


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg is required")
def test_fit_clip_trim_never_pretends_to_extend(tmp_path: Path) -> None:
    source = _video(tmp_path / "source.mp4", 1.0)
    with pytest.raises(Exception, match="cannot extend"):
        fit_clip(source, tmp_path / "out.mp4", target_seconds=2.0, policy="trim", fps=24)


def test_motion_plan_maps_camera_vocabulary(tmp_path: Path) -> None:
    board = _storyboard()
    for shot in board.shots:
        _png(tmp_path / "projects" / "p1" / "assets" / "keyframes" / shot.shot_id
             / f"{shot.shot_id}_00001_.png")
    timeline = build_edit_timeline(board, _manifest("N001", "N002"), settings=ProductionSettings())
    plan, info = build_motion_plan(
        tmp_path / "projects" / "p1", board, timeline, root=tmp_path,
        style_id="oriental.ink_wash", settings=ProductionSettings(),
    )
    assert plan is not None and len(plan.shots) == 2
    assert plan.style_id == "ink_wash"
    assert plan.shots[0].camera.move == "slow_push_in"
    assert info["shots"] == 2


def test_motion_plan_reports_unknown_style(tmp_path: Path) -> None:
    board = _storyboard()
    timeline = build_edit_timeline(board, _manifest("N001", "N002"), settings=ProductionSettings())
    plan, info = build_motion_plan(
        tmp_path / "projects" / "p1", board, timeline, root=tmp_path,
        style_id="advertising.acid_pop", settings=ProductionSettings(),
    )
    assert plan is None
    assert "no motion preset" in info["reason"]


def test_status_derives_from_files_and_reviews(tmp_path: Path) -> None:
    from drama_studio.film.project import FilmProject

    board = _storyboard()
    directory = tmp_path / "projects" / "p1"
    for shot in board.shots:
        _png(directory / "assets" / "keyframes" / shot.shot_id / f"{shot.shot_id}_00001_.png")
    project = FilmProject(root=tmp_path, project_id="p1", storyboard=board)
    status = film_status(project, tmp_path)
    assert status["overall"] == "keyframe_generated"
    assert status["counts"]["keyframes"] == 2

    record_review(directory, kind="keyframe", decision="approve", shot_id="S01")
    status = film_status(project, tmp_path)
    assert status["shots"][0]["status"] == "keyframe_approved"
    assert status["shots"][1]["status"] == "keyframe_generated"

    _video(directory / "shots" / "S01" / "S01_motion.mp4", 1.0)
    record_review(directory, kind="video", decision="approve", shot_id="S01")
    status = film_status(project, tmp_path)
    assert status["shots"][0]["status"] == "video_approved"

    build = directory / "renders" / "build-20260101-000000"
    build.mkdir(parents=True)
    (build / "build_manifest.json").write_text(json.dumps({"outputs": {"final": "x.mp4"}}), encoding="utf-8")
    (build / "quality_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    status = film_status(project, tmp_path)
    assert status["overall"] == "assembled"
    record_review(directory, kind="final", decision="approve")
    status = film_status(project, tmp_path)
    assert status["overall"] == "finalized"
    path = write_state(directory, status)
    assert path.is_file()


def test_assemble_dry_run_writes_contracts(tmp_path: Path) -> None:
    from drama_studio.film.assemble import assemble

    board = _storyboard()
    directory = tmp_path / "projects" / "p1"
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(json.dumps({"project_id": "p1"}), encoding="utf-8")
    (directory / "storyboard.json").write_text(
        json.dumps(board.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    _wav(directory / "assets" / "audio" / "N001.wav", 1.0)
    _wav(directory / "assets" / "audio" / "N002.wav", 1.0)
    (directory / "assets" / "audio" / "audio_manifest.json").write_text(json.dumps({
        "project_id": "p1", "content_type": "poetry",
        "lines": [
            {"id": "N001", "file": "projects/p1/assets/audio/N001.wav", "text": "a",
             "duration_seconds": 1.0, "planned_pause_after_ms": 300},
            {"id": "N002", "file": "projects/p1/assets/audio/N002.wav", "text": "b",
             "duration_seconds": 1.0, "planned_pause_after_ms": 300},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    for shot in board.shots:
        _png(directory / "assets" / "keyframes" / shot.shot_id / f"{shot.shot_id}_00001_.png")

    from drama_studio.film.project import load_project

    loaded = load_project(tmp_path, "p1")
    result = assemble(loaded, tmp_path, with_motion=False, dry_run=True,
                      out=tmp_path / "projects" / "p1" / "renders" / "custom", allow_overwrite=True)
    assert result["dry_run"] is True
    build = Path(result["build_dir"])
    assert (build / "segments.json").is_file()
    assert (build / "audio_manifest.json").is_file()
    assert (build / "film_timeline.json").is_file()
    assert result["plan"]["segments"] == 2
    assert result["plan"]["r3_build"][0].endswith("python.exe") or "python" in result["plan"]["r3_build"][0]


def test_audio_timeline_ducking_is_valid() -> None:
    from drama_studio.film.segments import build_audio_timeline
    from drama_studio.voice.audio_timeline import AudioTimeline

    board = _storyboard()
    manifest = {
        "lines": [
            {"id": "N001", "file": "projects/p1/assets/audio/N001.wav", "duration_seconds": 1.0,
             "planned_pause_after_ms": 300, "text": "a"},
            {"id": "N002", "file": "projects/p1/assets/audio/N002.wav", "duration_seconds": 1.0,
             "planned_pause_after_ms": 300, "text": "b"},
        ]
    }
    timeline = build_edit_timeline(board, manifest, settings=ProductionSettings())
    payload = build_audio_timeline(
        manifest, timeline, root=Path("."), bgm_asset_id="bgm_test",
        ambience_asset_id="sfx_test")
    parsed = AudioTimeline.model_validate(payload)
    assert [track.track_id for track in parsed.tracks] == ["narration", "ambience", "bgm"]
    assert parsed.tracks[2].ducking is not None
    assert parsed.tracks[2].ducking.trigger_track_ids == ["narration"]


def test_r3_timeline_matches_film_events() -> None:
    from drama_studio.voice.timeline import build_timeline as build_voice_timeline

    board = _storyboard()
    manifest = {
        "lines": [
            {"id": "N001", "file": "a.wav", "duration_seconds": 1.0,
             "planned_pause_after_ms": 300, "text": "a"},
            {"id": "N002", "file": "b.wav", "duration_seconds": 1.0,
             "planned_pause_after_ms": 300, "text": "b"},
        ]
    }
    timeline = build_edit_timeline(board, manifest, settings=ProductionSettings())
    r3_segments = [
        {
            "segment_id": f"line_{index:02d}",
            "duration": line["duration_seconds"],
            "pause_after_ms": 0,
            "gap_before_ms": 0,
        }
        for index, line in enumerate(manifest["lines"], start=1)
    ]
    # Rebuild the gaps exactly as apply_line_timing would.
    from drama_studio.film.timeline import apply_line_timing

    timed = apply_line_timing(manifest, timeline)["lines"]
    r3_segments = [
        {
            "segment_id": f"line_{index:02d}",
            "duration": line["duration_seconds"],
            "pause_after_ms": 0,
            "gap_before_ms": line["gap_before_ms"],
        }
        for index, line in enumerate(timed, start=1)
    ]
    voice = build_voice_timeline(r3_segments, timeline.leading_silence_ms)
    assert [event["speech_start_ms"] for event in voice["segments"]] == [
        event.start_ms for event in timeline.narration_events
    ]


def test_subtitle_wraps_without_changing_speech() -> None:
    from drama_studio.film.audio import wrap_subtitle

    text = "予观夫巴陵胜状，在洞庭一湖，衔远山，吞长江，浩浩汤汤，横无际涯。"
    wrapped = wrap_subtitle(text, max_chars=12)
    assert "\n" in wrapped
    assert wrapped.replace("\n", "") == text


def test_upscale_backends_report_lanczos_and_missing_ncnn() -> None:
    from drama_studio.film.upscale import available_backends

    backends = available_backends()
    assert backends["lanczos"]["available"] is True
    assert "realesrgan-ncnn" in backends
    assert backends["realesrgan-ncnn"]["kind"] == "external"


def test_wan_qc_cuts_top_band_artifact(tmp_path: Path) -> None:
    from drama_studio.film.wan_qc import select_clean_prefix

    frames = []
    for index in range(12):
        image = Image.new("RGB", (64, 114), (210, 205, 195))
        if index >= 10:
            for x in range(64):
                for y in range(6):
                    image.putpixel((x, y), (10, 10, 10))
        path = tmp_path / f"S01_{index + 1:05d}_.png"
        image.save(path)
        frames.append(path)
    clean, qc = select_clean_prefix(frames)
    assert len(clean) == 10
    assert qc is not None and "top band" in qc["reason"]


def test_wan_qc_cuts_bright_blob(tmp_path: Path) -> None:
    from drama_studio.film.wan_qc import select_clean_prefix

    frames = []
    for index in range(12):
        image = Image.new("RGB", (64, 114), (120, 120, 120))
        if index >= 10:
            for x in range(12, 24):
                for y in range(30, 45):
                    image.putpixel((x, y), (255, 255, 255))
        path = tmp_path / f"S02_{index + 1:05d}_.png"
        image.save(path)
        frames.append(path)
    clean, qc = select_clean_prefix(frames)
    assert len(clean) == 10
    assert qc is not None and "bright blob" in qc["reason"]
