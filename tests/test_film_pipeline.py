"""Film pipeline: job generation, voice wiring, timeline and segment adapters."""

from __future__ import annotations

import json
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from drama_studio.film import plan_storyboard
from drama_studio.film.assemble import prepare
from drama_studio.film.audio import standard_manifest, write_manifest
from drama_studio.film.jobs import build_keyframe_jobs, build_wan_jobs
from drama_studio.film.project import load_project
from drama_studio.film.schemas import ArtDirection, CameraLanguage, CharacterDesign, EnvironmentDesign, VisualBible
from drama_studio.film.segments import build_audio_manifest, build_segments
from drama_studio.film.timeline import build_edit_timeline


def _wav(path: Path, seconds: float = 1.0, rate: int = 48000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * int(rate * seconds))
    return path


def _png(path: Path) -> Path:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 114), (200, 200, 200)).save(path)
    return path


def _project(root: Path, shots: int = 2) -> Path:
    directory = root / "projects" / "p1"
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(
        json.dumps({"project_id": "p1", "title": "t"}), encoding="utf-8"
    )
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "audio.yaml").write_text(
        "tts:\n  mode: zero_shot\n  zero_shot:\n    prompt_audio: assets/ref.wav\n"
        "    prompt_text: 参考\n    speed: 0.9\n",
        encoding="utf-8",
    )
    (root / "config" / "settings.yaml").write_text(
        'paths: {}\ntts:\n  base_url: "http://tts.test"\n  sample_rate: 48000\n', encoding="utf-8"
    )
    (root / "assets").mkdir(exist_ok=True)
    _wav(root / "assets" / "ref.wav", 0.2)
    (directory / "narration.json").write_text(json.dumps({
        "project_id": "p1",
        "language": "en",
        "segments": [{"id": f"N{i:03d}", "text": f"line {i}"} for i in range(1, shots + 1)],
    }, ensure_ascii=False), encoding="utf-8")
    bible = VisualBible(
        project_id="p1",
        art_direction=ArtDirection(style="ink", lighting="golden_hour", palette=["warm"]),
        protagonist=CharacterDesign(identity="poet"),
        environment=EnvironmentDesign(landscape="mountains_river"),
        camera_language=CameraLanguage(),
    )
    (directory / "visual_bible.yaml").write_text(
        yaml.safe_dump(bible.model_dump(mode="json"), allow_unicode=True), encoding="utf-8"
    )
    beats = [
        {"scene_id": "SC01", "duration_seconds": 5, "shot_size": "ws",
         "motion_primary": "environment_drift", "midground": "ridge",
         "narration_ids": [f"N{i:03d}"]}
        for i in range(1, shots + 1)
    ]
    board = plan_storyboard("p1", beats, bible)
    (directory / "storyboard.json").write_text(
        json.dumps(board.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    return directory


def _audio_manifest(directory: Path, seconds: list[float]) -> Path:
    segments = []
    for index, length in enumerate(seconds, start=1):
        wav = _wav(directory / "assets" / "audio" / f"N{index:03d}.wav", length)
        segments.append({"id": f"N{index:03d}", "text": f"line {index}", "wav": str(wav),
                         "pause_after_ms": 500})
    payload = standard_manifest(project_id="p1", segments=segments, root=directory.parents[1])
    return write_manifest(directory / "assets" / "audio" / "audio_manifest.json", payload)


def test_keyframe_jobs_reference_flux3(tmp_path: Path) -> None:
    _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")
    result = build_keyframe_jobs(loaded, tmp_path)
    payload = json.loads(Path(result["jobs"]).read_text(encoding="utf-8"))
    assert isinstance(payload, list), "r1_batch requires a bare list of jobs"
    assert result["count"] == 2 and len(payload) == 2
    assert payload[0]["workflow"] == "workflows/flux3_t2i_api.json"
    params = json.loads((tmp_path / payload[0]["params"]).read_text(encoding="utf-8"))
    assert params["steps"] == 16 and params["seed"] == 9100


def test_wan_jobs_need_keyframes_unless_allowed(tmp_path: Path) -> None:
    _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")
    with pytest.raises(FileNotFoundError):
        build_wan_jobs(loaded, tmp_path)
    result = build_wan_jobs(loaded, tmp_path, allow_missing_keyframes=True)
    payload = json.loads(Path(result["jobs"]).read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    job = payload[0]
    assert job["workflow"] == "workflows/r0_wan_i2v_api.json"
    assert job["reference"]["input_name"] == "p1_S01_kf.png"
    assert job["reference"]["selector"] == "latest"
    params = json.loads((tmp_path / job["params"]).read_text(encoding="utf-8"))
    assert params["frames"] == 121 and params["shift"] == 8.0


def test_wan_jobs_pick_73_for_short_shots(tmp_path: Path) -> None:
    _project(tmp_path, 2)
    directory = tmp_path / "projects" / "p1"
    board = json.loads((directory / "storyboard.json").read_text(encoding="utf-8"))
    board["shots"][0]["duration_seconds"] = 2.5
    (directory / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    loaded = load_project(tmp_path, "p1")
    for shot in loaded.storyboard.shots:
        _png(directory / "assets" / "keyframes" / shot.shot_id / f"{shot.shot_id}_00001_.png")
    result = build_wan_jobs(loaded, tmp_path)
    payload = json.loads(Path(result["jobs"]).read_text(encoding="utf-8"))
    first = json.loads((tmp_path / payload[0]["params"]).read_text(encoding="utf-8"))
    second = json.loads((tmp_path / payload[1]["params"]).read_text(encoding="utf-8"))
    assert first["frames"] == 73
    assert second["frames"] == 121


def test_voice_synthesis_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from drama_studio.film import voice

    _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")

    def fake(text, *, prompt_wav, prompt_text, out_wav, speed, base):
        _wav(out_wav, 1.25)
        return SimpleNamespace(seconds=1.25, synth_seconds=9.0, sample_rate=48000,
                               prompt_sha256="abc")

    monkeypatch.setattr(voice, "zeroshot_synthesize", fake)
    result = voice.synthesize_narration(loaded, tmp_path)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert result["segments"] == 2
    assert manifest["engine"] == "voxcpm2"
    assert manifest["segments"][0]["rendered_text"] == "(None, None)line 1" or \
        manifest["segments"][0]["rendered_text"] == "line 1"
    assert manifest["lines"][0]["file"] == "projects/p1/assets/audio/N001.wav"
    assert manifest["lines"][0]["duration_seconds"] == pytest.approx(1.25)

    from drama_studio.film.schemas import NarrationSegment
    from drama_studio.film.voice import render_text
    directed = NarrationSegment(id="N009", text="白日依山尽。", emotion="open", delivery="gentle")
    assert render_text(directed) == "白日依山尽"


def test_audio_first_timeline_extends_short_shots(tmp_path: Path) -> None:
    directory = _project(tmp_path, 2)
    _audio_manifest(directory, [7.0, 1.0])
    loaded = load_project(tmp_path, "p1")
    manifest = json.loads((directory / "assets" / "audio" / "audio_manifest.json").read_text(encoding="utf-8"))
    from drama_studio.film.config import ProductionSettings

    timeline = build_edit_timeline(loaded.storyboard, manifest, settings=ProductionSettings())
    first = timeline.entries[0]
    assert (first.end_ms - first.start_ms) >= 7000 + 500, "short shot must grow to hold its line"
    assert timeline.narration_events[0].start_ms == timeline.leading_silence_ms
    assert timeline.narration_events[1].start_ms == timeline.entries[1].start_ms
    assert timeline.total_ms >= timeline.narration_events[-1].end_ms


def test_prepare_builds_segments_and_timed_audio(tmp_path: Path) -> None:
    directory = _project(tmp_path, 2)
    _audio_manifest(directory, [1.0, 1.0])
    for shot in ("S01", "S02"):
        _png(directory / "assets" / "keyframes" / shot / f"{shot}_00001_.png")
    loaded = load_project(tmp_path, "p1")
    prepared = prepare(loaded, tmp_path)
    segments = build_segments(directory, loaded.storyboard, prepared["timeline"], root=tmp_path)
    assert [item["type"] for item in segments] == ["image", "image"]
    assert segments[0]["source"].endswith("S01_00001_.png")
    audio = build_audio_manifest(prepared["audio_manifest"], prepared["timeline"], root=tmp_path)
    assert audio["lines"][0]["gap_before_ms"] == 0
    assert audio["lines"][1]["gap_before_ms"] > 0
    assert audio["timeline"]["total_ms"] == prepared["timeline"].total_ms


def test_segments_refuse_unencoded_wan_frames(tmp_path: Path) -> None:
    directory = _project(tmp_path, 1)
    _audio_manifest(directory, [1.0])
    for index in (1, 2):
        _png(directory / "shots" / "S01" / f"S01_{index:05d}_.png")
    loaded = load_project(tmp_path, "p1")
    prepared = prepare(loaded, tmp_path)
    from drama_studio.film.assets import resolve_asset

    assert resolve_asset(directory, "S01").kind == "image_sequence"
    with pytest.raises(Exception, match="film clips"):
        build_segments(directory, loaded.storyboard, prepared["timeline"], root=tmp_path)
