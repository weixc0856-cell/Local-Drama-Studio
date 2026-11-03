from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image


def _png(path: Path, size: tuple[int, int] = (120, 80)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (40, 80, 120)).save(path)


def _mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1.5",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-t", "1.5", str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_safe_path_accepts_repo_media(workspace) -> None:
    _png(workspace.root / "assets" / "sample.png")
    path = workspace.media.safe_path("assets/sample.png")
    assert path.is_file()


@pytest.mark.parametrize(
    "candidate",
    [
        "../etc/passwd",
        "assets/../../etc/passwd",
        "C:/Windows/win.ini",
        "/etc/passwd",
        "config/settings.yaml",
        "logs/workspace-server.log",
    ],
)
def test_safe_path_rejects_escape_or_forbidden_roots(workspace, candidate: str) -> None:
    with pytest.raises(workspace.media.MediaError):
        workspace.media.safe_path(candidate)


def test_parse_range(workspace) -> None:
    assert workspace.media.parse_range("bytes=0-99", 1000) == (0, 99)
    assert workspace.media.parse_range("bytes=900-", 1000) == (900, 999)
    assert workspace.media.parse_range("bytes=-100", 1000) == (900, 999)
    assert workspace.media.parse_range("bytes=0-9999", 1000) == (0, 999)
    with pytest.raises(workspace.media.RangeNotSatisfiable):
        workspace.media.parse_range("bytes=1000-", 1000)
    with pytest.raises(workspace.media.MediaError):
        workspace.media.parse_range("items=0-1", 1000)


def test_thumbnail_is_generated_and_cached(workspace) -> None:
    _png(workspace.root / "assets" / "sample.png")
    first = workspace.media.thumbnail("assets/sample.png", 60)
    second = workspace.media.thumbnail("assets/sample.png", 60)
    assert first.is_file()
    assert first == second
    assert first.stat().st_size > 0


def test_thumbnail_of_video_uses_ffmpeg(workspace) -> None:
    _mp4(workspace.root / "assets" / "sample.mp4")
    target = workspace.media.thumbnail("assets/sample.mp4", 60)
    assert target.is_file()
    assert target.stat().st_size > 0


def test_iter_file_reads_exact_range(workspace) -> None:
    path = workspace.root / "assets" / "sample.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"ok": true}', encoding="utf-8")
    safe = workspace.media.safe_path("assets/sample.json")
    size = safe.stat().st_size
    data = b"".join(workspace.media.iter_file(safe, 0, min(size - 1, 9)))
    assert len(data) == min(size, 10)
