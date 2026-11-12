from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

import pytest

from drama_studio.voice.audio_assets import AudioAssetError, load_registry
from drama_studio.voice.audio_timeline import (
    AudioEvent,
    AudioTimeline,
    AudioTrack,
    TimelineError,
    from_audio_manifest,
    load_timeline,
)
from drama_studio.voice.mix import MixError, build_filter_graph, mix_timeline
from drama_studio.quality import check_audio_timeline


def _wav(path: Path, seconds: float = 1.0, value: int = 1000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(48000)
        fh.writeframes(b"\x00\x00" * int(48000 * seconds))
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry(root: Path) -> Path:
    bgm = _wav(root / "bgm.wav", 2.0)
    sfx = _wav(root / "sfx.wav", 0.5)
    payload = {
        "schema_version": "1.1",
        "assets": [
            {"asset_id": "bgm_001", "asset_type": "bgm", "path": "bgm.wav",
             "sha256": _sha(bgm), "commercial_allowed": True,
             "status": "VERIFIED"},
            {"asset_id": "sfx_001", "asset_type": "sfx", "path": "sfx.wav",
             "sha256": _sha(sfx), "commercial_allowed": True,
             "status": "VERIFIED"},
        ],
    }
    path = root / "assets.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _timeline(root: Path) -> AudioTimeline:
    voice = _wav(root / "voice.wav", 1.0)
    return AudioTimeline(
        duration_ms=2000,
        tracks=[
            AudioTrack(
                track_id="narration_main",
                type="narration",
                events=[AudioEvent(event_id="nar_001", path="voice.wav",
                                   line_id="line_001", start_ms=0, duration_ms=1000)],
            ),
            AudioTrack(
                track_id="bgm_main", type="bgm", asset_id="bgm_001",
                duration_ms=2000,
                ducking={"enabled": True, "trigger_track_ids": ["narration_main"]},
            ),
            AudioTrack(
                track_id="sfx_main", type="sfx",
                events=[AudioEvent(event_id="sfx_001", asset_id="sfx_001",
                                   start_ms=1200, duration_ms=500)],
            ),
        ],
    )


def test_timeline_validates_bounds_and_duplicates(tmp_path: Path) -> None:
    tl = _timeline(tmp_path)
    assert tl.duration_ms == 2000
    with pytest.raises(ValueError):
        AudioTimeline(
            duration_ms=100,
            tracks=[AudioTrack(track_id="n", type="narration",
                               events=[AudioEvent(event_id="e", path="x.wav",
                                                  start_ms=50, duration_ms=100)])],
        )


def test_from_audio_manifest_uses_ledger(tmp_path: Path) -> None:
    _wav(tmp_path / "line_01.wav")
    manifest = tmp_path / "audio_manifest.json"
    manifest.write_text(json.dumps({
        "sample_rate": 48000,
        "lines": [{"index": 1, "file": "line_01.wav", "duration_seconds": 1.0}],
        "ledger": [{"kind": "line", "index": 1, "start": 0.3, "end": 1.3}],
    }), encoding="utf-8")
    tl = from_audio_manifest(manifest)
    assert tl.tracks[0].events[0].start_ms == 300
    assert tl.duration_ms == 1300


def test_asset_registry_accepts_legacy_fields_and_enforces_status(tmp_path: Path) -> None:
    bgm = _wav(tmp_path / "bgm.wav")
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"assets": [
        {"id": "b", "kind": "bgm", "path": "bgm.wav", "sha256": _sha(bgm),
         "commercial_allowed": True, "status": "VERIFIED"}
    ]}), encoding="utf-8")
    reg = load_registry(legacy)
    assert reg.get("b").asset_type == "bgm"
    assert reg.resolve("b", tmp_path) == bgm

    blocked = tmp_path / "blocked.json"
    blocked.write_text(json.dumps({"assets": [
        {"asset_id": "x", "asset_type": "bgm", "path": "bgm.wav",
         "status": "BLOCKED", "commercial_allowed": False}
    ]}), encoding="utf-8")
    with pytest.raises(AudioAssetError, match="only VERIFIED"):
        load_registry(blocked).resolve("x", tmp_path)


def test_graph_has_ducking_and_track_labels(tmp_path: Path) -> None:
    tl = _timeline(tmp_path)
    reg = load_registry(_registry(tmp_path))
    inputs, graph = build_filter_graph(tl, root=tmp_path, registry=reg)
    assert "-stream_loop" not in inputs  # loop false
    assert "sidechaincompress=" in graph
    assert "[mixed]" in graph
    assert graph.count("adelay=") >= 3


def test_mix_timeline_renders_48k_mono(tmp_path: Path) -> None:
    tl = _timeline(tmp_path)
    plan = tmp_path / "audio_timeline.json"
    plan.write_text(tl.model_dump_json(), encoding="utf-8")
    reg = _registry(tmp_path)
    out = tmp_path / "mixed.wav"
    result = mix_timeline(plan, out, root=tmp_path, asset_registry_path=reg)
    assert result["status"] == "PASS"
    assert out.is_file()
    with wave.open(str(out), "rb") as fh:
        assert fh.getframerate() == 48000
        assert fh.getnchannels() == 1
        assert abs(fh.getnframes() / 48000 - 2.0) < 0.1


def test_missing_asset_is_loud(tmp_path: Path) -> None:
    tl = _timeline(tmp_path)
    reg = _registry(tmp_path)
    plan = tmp_path / "audio_timeline.json"
    plan.write_text(tl.model_dump_json(), encoding="utf-8")
    with pytest.raises(MixError, match="not found"):
        mix_timeline(plan, tmp_path / "mixed.wav", root=tmp_path,
                     asset_registry_path=tmp_path / "missing.json")


def test_timeline_load_rejects_bad_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(TimelineError):
        load_timeline(path)


def test_audio_timeline_quality_passes_ready_assets(tmp_path: Path) -> None:
    tl = _timeline(tmp_path)
    plan = tmp_path / "audio_timeline.json"
    plan.write_text(tl.model_dump_json(), encoding="utf-8")
    reg = _registry(tmp_path)
    result = check_audio_timeline(plan, root=tmp_path, assets_path=reg)
    assert result["status"] == "PASS", result
    assert (tmp_path / "audio_timeline_report.json").is_file()
