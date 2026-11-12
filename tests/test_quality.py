from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

from PIL import Image

from drama_studio.application.quality import check_audio, check_build, check_image, check_video


def _noise(path: Path, size: tuple[int, int] = (64, 64)) -> None:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 7) % 255, (y * 11) % 255, ((x + y) * 13) % 255)
    image.save(path)


def _mp4(path: Path, size: tuple[int, int] = (64, 64), seconds: float = 0.5) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"color=c=black:s={size[0]}x{size[1]}:d={seconds}",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-t", str(seconds), str(path),
        ],
        check=True,
        capture_output=True,
    )


def _wav(path: Path, seconds: float = 0.3) -> None:
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(48000)
        fh.writeframes(b"\x00\x00" * int(48000 * seconds))


def test_check_image_detects_blank_and_black(tmp_path: Path) -> None:
    good = tmp_path / "good.png"
    _noise(good)
    assert check_image(good)["status"] == "PASS"

    blank = tmp_path / "blank.png"
    Image.new("RGB", (32, 32), (128, 128, 128)).save(blank)
    assert check_image(blank)["status"] == "FAIL"

    black = tmp_path / "black.png"
    Image.new("RGB", (32, 32), (0, 0, 0)).save(black)
    result = check_image(black)
    assert result["status"] == "FAIL"
    assert result["black"] is True


def test_check_video_and_audio(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    _mp4(video)
    result = check_video(video)
    assert result["status"] == "PASS"
    assert result["decode_returncode"] == 0
    assert result["width"] == 64

    audio = tmp_path / "silence.wav"
    _wav(audio)
    assert check_audio(audio)["status"] == "PASS"


def test_check_build_writes_report(tmp_path: Path) -> None:
    root = tmp_path
    build = root / "build-test"
    build.mkdir()
    final = build / "final.mp4"
    _mp4(final, size=(1080, 1920), seconds=0.4)
    image = build / "scene.png"
    _noise(image)
    mixed = build / "mixed.wav"
    _wav(mixed)
    manifest = build / "build_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "segments": [{"source": str(image)}],
                "outputs": {
                    "final": str(final),
                    "final_sha256": __import__("hashlib").sha256(final.read_bytes()).hexdigest(),
                    "mixed": str(mixed),
                },
            }
        ),
        encoding="utf-8",
    )
    result = check_build(manifest, root=root)
    assert result["status"] == "PASS"
    assert (build / "quality_report.json").is_file()
    assert result["final"]["width"] == 1080
    assert result["final"]["height"] == 1920


def test_check_build_accepts_a_source_video_smaller_than_the_final(tmp_path: Path) -> None:
    root = tmp_path
    build = root / "build-video"
    build.mkdir()
    final = build / "final.mp4"
    _mp4(final, size=(1080, 1920), seconds=0.4)
    clip = build / "wan_source.mp4"
    _mp4(clip, size=(576, 1024), seconds=0.4)
    mixed = build / "mixed.wav"
    _wav(mixed)
    manifest = build / "build_manifest.json"
    manifest.write_text(
        json.dumps({
            "segments": [{"source": str(clip), "type": "video"}],
            "outputs": {
                "final": str(final),
                "final_sha256": __import__("hashlib").sha256(final.read_bytes()).hexdigest(),
                "mixed": str(mixed),
            },
        }), encoding="utf-8")
    result = check_build(manifest, root=root)
    assert result["status"] == "PASS"
    assert result["images"][0]["path"].endswith("wan_source.mp4")
