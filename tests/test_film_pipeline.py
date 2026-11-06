"""Film pipeline: job generation, voice wiring, assembly command."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from drama_studio.film import build_timeline, plan_storyboard
from drama_studio.film.assemble import build_assemble_command
from drama_studio.film.jobs import build_keyframe_jobs, build_wan_jobs
from drama_studio.film.project import load_project
from drama_studio.film.schemas import ArtDirection, CameraLanguage, CharacterDesign, EnvironmentDesign, VisualBible


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
    (root / "assets" / "ref.wav").write_bytes(b"RIFF")
    (directory / "narration.json").write_text(json.dumps({
        "project_id": "p1",
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
    params = json.loads((tmp_path / job["params"]).read_text(encoding="utf-8"))
    assert params["frames"] == 121 and params["shift"] == 8.0


def test_voice_synthesis_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from drama_studio.film import voice

    _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")

    def fake(text, *, prompt_wav, prompt_text, out_wav, speed, base):
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        out_wav.write_bytes(b"RIFF")
        return SimpleNamespace(seconds=1.25, synth_seconds=9.0, sample_rate=48000,
                               prompt_sha256="abc")

    monkeypatch.setattr(voice, "zeroshot_synthesize", fake)
    result = voice.synthesize_narration(loaded, tmp_path)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert result["segments"] == 2
    assert manifest["engine"] == "voxcpm2"
    assert manifest["segments"][0]["rendered_text"] == "line 1"

    from drama_studio.film.schemas import NarrationSegment
    from drama_studio.film.voice import render_text
    directed = NarrationSegment(id="N009", text="白日依山尽。", emotion="open", delivery="gentle")
    assert render_text(directed) == "(open, gentle)白日依山尽。"


def test_assemble_command_concatenates_and_mixes(tmp_path: Path) -> None:
    directory = _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")
    timeline = build_timeline(loaded.storyboard)
    (directory / "timeline.json").write_text(
        json.dumps(timeline.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    for shot in ("S01", "S02"):
        clip = directory / "shots" / shot / f"{shot}_00001_.mp4"
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(b"")
    (directory / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    segments = []
    for item in ("N001", "N002"):
        (directory / "assets" / "audio" / f"{item}.wav").write_bytes(b"RIFF")
        segments.append({"id": item, "wav": f"assets/audio/{item}.wav"})
    manifest = {"segments": segments}

    cmd = build_assemble_command(directory, timeline, manifest, directory / "out.mp4")
    joined = " ".join(cmd)
    assert "concat=n=2:v=1:a=0" in joined
    assert "amix=inputs=2" in joined
    assert "libx264" in joined and "aac" in joined
    assert cmd[-1].endswith("out.mp4")


def test_contact_sheet_marks_missing_frames(tmp_path: Path) -> None:
    from PIL import Image
    from drama_studio.film.review import build_contact_sheet

    directory = _project(tmp_path, 2)
    loaded = load_project(tmp_path, "p1")
    frame = directory / "assets" / "keyframes" / "S01" / "S01_00001_.png"
    frame.parent.mkdir(parents=True)
    Image.new("RGB", (576, 1024), (200, 180, 140)).save(frame)
    out = build_contact_sheet(directory, loaded.storyboard, directory / "qc" / "sheet.png")
    assert out.is_file() and out.stat().st_size > 0
