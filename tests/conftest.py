from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import os

_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DRAMA_MODELS_ROOT", str(_ROOT / "runtime" / "models"))
os.environ.setdefault("DRAMA_AI_HOME", str(_ROOT / "runtime"))
os.environ.setdefault("VOXCPM_RUNTIME", str(_ROOT / "runtime" / "VoxCPM-Runtime"))

import pytest
from PIL import Image

from drama_studio.workspace.store import WorkspaceStore

SHORT_TEXT = "白日依山尽"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _png(path: Path, size: tuple[int, int] = (64, 64)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (32, 48, 64)).save(path)


def _wav(path: Path, seconds: float = 0.3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(48000)
        fh.writeframes(b"\x00\x00" * int(48000 * seconds))


def _mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.3",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-t", "0.3", str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Isolate discovery/tasks/media from the real repository artifacts."""
    from drama_studio.workspace import api, discovery, media, tasks

    monkeypatch.setattr(discovery, "ROOT", tmp_path)
    monkeypatch.setattr(media, "ROOT", tmp_path)
    monkeypatch.setattr(media, "THUMB_DIR", tmp_path / "logs" / "thumbs")
    monkeypatch.setattr(tasks, "ROOT", tmp_path)
    monkeypatch.setattr(tasks, "LOG_DIR", tmp_path / "logs" / "workspace" / "tasks")
    tasks.LOG_DIR.mkdir(parents=True, exist_ok=True)
    store = WorkspaceStore(root=tmp_path, db_path=tmp_path / "workspace.db")
    return SimpleNamespace(root=tmp_path, store=store, api=api, discovery=discovery, media=media, tasks=tasks)


def make_video_episode(ws: SimpleNamespace) -> dict:
    """Create one synthetic video episode with a real, valid tiny MP4."""
    root: Path = ws.root
    store: WorkspaceStore = ws.store
    project = store.create_project({"name": "测试项目", "aspect_ratio": "9:16"})
    episode = store.create_episode(
        {
            "project_id": project["id"],
            "number": 1,
            "title": "测试期数",
            "track": "video",
            "artifact_root": "artifacts/ep1",
        }
    )
    base = root / "artifacts" / "ep1"
    base.mkdir(parents=True, exist_ok=True)
    _png(base / "scene.png")
    _mp4(base / "clip.mp4")
    _wav(base / "line_01.wav")
    (base / "drama.srt").write_text("1\n00:00:00,000 --> 00:00:00,300\n白日依山尽\n", encoding="utf-8")
    (base / "drama.ass").write_text("[Script Info]\n", encoding="utf-8")
    (root / "artifacts" / "ep1" / "final.mp4").write_bytes((base / "clip.mp4").read_bytes())

    (base / "narration.json").write_text(
        json.dumps({"title": "测试短文本", "lines": [SHORT_TEXT]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (base / "segments.json").write_text(
        json.dumps(
            [
                {"id": "S1", "type": "image", "source": "artifacts/ep1/scene.png", "duration": 0.2},
                {"id": "S2", "type": "video", "source": "artifacts/ep1/clip.mp4", "duration": 0.3},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    wav = base / "line_01.wav"
    (base / "audio_manifest.json").write_text(
        json.dumps(
            {
                "speaker": "测试音色",
                "lines": [
                    {
                        "index": 1,
                        "text": SHORT_TEXT,
                        "file": "artifacts/ep1/line_01.wav",
                        "sha256": sha256(wav),
                        "duration_seconds": 0.3,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    final = base / "final.mp4"
    manifest = {
        "segments": [{"id": "S1", "source": "artifacts/ep1/scene.png"}],
        "content_type": "narration",
        "timeline": {"file": "artifacts/ep1/timeline.json"},
        "total_seconds": 0.3,
        "font": {"postscript_name": "TestFont-Regular"},
        "outputs": {
            "final": "artifacts/ep1/final.mp4",
            "final_sha256": sha256(final),
            "srt": "artifacts/ep1/drama.srt",
            "ass": "artifacts/ep1/drama.ass",
        },
        "decode_returncode": 0,
    }
    build_dir = root / "projects" / project["id"] / "episodes" / episode["id"] / "renders" / "build-test"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"project": project, "episode": store.get_episode(episode["id"])}
