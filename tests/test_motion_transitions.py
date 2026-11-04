from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from drama_studio.motion.spec import MotionPlan, ShotSpec, TransitionSpec
from drama_studio.motion.transition import (
    assemble_sequence,
    make_masks,
    render_transition,
)
from drama_studio.quality import FAIL, PASS, check_temporal_continuity

ROOT = Path(__file__).resolve().parents[1]
FPS = 24


def _encode(frames: list[Image.Image], out: Path, fps: int = FPS) -> Path:
    frame_dir = out.parent / f"frames_{out.stem}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("f_*.png"):
        old.unlink()
    for index, frame in enumerate(frames):
        frame.convert("RGB").save(frame_dir / f"f_{index:04d}.png")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
         "-i", str(frame_dir / "f_%04d.png"), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", str(out)],
        check=True, capture_output=True,
    )
    return out


def _solid(path: Path, color: str, seconds: float) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"color=c={color}:s=270x480:d={seconds}:r={FPS}",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", str(path)],
        check=True, capture_output=True,
    )
    return path


def _changing_left(path: Path) -> Path:
    colors = [(240, 30, 30), (30, 200, 60), (30, 60, 220), (245, 235, 40)]
    frames = [Image.new("RGB", (270, 480), colors[min(3, index // 24)]) for index in range(96)]
    return _encode(frames, path)


def _mean_rgb(path: Path, at: float) -> tuple[float, float, float]:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", str(path),
         "-frames:v", "1", "-vf", "scale=32:32,format=rgb24", "-f", "rawvideo", "-"],
        check=True, capture_output=True,
    )
    data = proc.stdout[: 32 * 32 * 3]
    count = 32 * 32
    return tuple(sum(data[i + c] for i in range(0, len(data), 3)) / count for c in range(3))


def _fps(path: Path) -> str:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(proc.stdout)["streams"][0]["r_frame_rate"]


def _render(tmp_path: Path, left: Path, right: Path, kind: str,
            duration: float = 0.8, **kwargs):
    spec = TransitionSpec(type=kind, duration_s=duration, feather=0.12, seed=13)
    mask_dir = tmp_path / f"masks_{kind}"
    if kind != "crossfade":
        make_masks(spec, mask_dir, duration, FPS)
    out = tmp_path / f"transition_{kind}.mp4"
    result = render_transition(left, right, out, spec, mask_dir, fps=FPS, **kwargs)
    return result, out


def test_left_handle_starts_at_the_tail_not_the_head(tmp_path: Path) -> None:
    left = _changing_left(tmp_path / "left.mp4")
    right = _solid(tmp_path / "right.mp4", "0x808080", 3.0)
    result, out = _render(tmp_path, left, right, "ink_dissolve", duration=0.5)
    # 4.0 s left clip - 0.5 s transition = the last half second (yellow segment).
    assert result["timing"]["left_start"] == pytest.approx(3.5, abs=1e-3)
    argv = result["argv"]
    ss_values = [argv[i + 1] for i, value in enumerate(argv) if value == "-ss"]
    assert "3.500" in ss_values
    first = _mean_rgb(out, 0.0)
    # yellow, not the red head at t=0
    assert first[0] > 150 and first[1] > 150 and first[2] < 120
    assert result["algorithm"] == "alphamerge_overlay"


def test_zero_start_is_rejected(tmp_path: Path) -> None:
    left = _solid(tmp_path / "left.mp4", "0xC02020", 1.0)
    right = _solid(tmp_path / "right.mp4", "0x2040C0", 1.0)
    spec = TransitionSpec(type="crossfade", duration_s=0.4, feather=0.12, seed=13)
    with pytest.raises(ValueError, match="must start after 0"):
        render_transition(left, right, tmp_path / "x.mp4", spec,
                          tmp_path / "masks", fps=FPS, left_start=0.0)


@pytest.mark.parametrize("kind", ["crossfade", "ink_dissolve", "ink_reveal", "ink_spread"])
def test_four_transitions_keep_fps_and_colour(tmp_path: Path, kind: str) -> None:
    left = _solid(tmp_path / f"left_{kind}.mp4", "0xB02C26", 2.0)
    right = _solid(tmp_path / f"right_{kind}.mp4", "0x1E4478", 2.0)
    result, out = _render(tmp_path, left, right, kind, duration=0.8)
    assert _fps(out) == "24/1"
    assert result["algorithm"] == ("xfade" if kind == "crossfade" else "alphamerge_overlay")
    assert "maskedmerge" not in " ".join(result["argv"])
    start = _mean_rgb(out, 0.0)
    mid = _mean_rgb(out, 0.4)
    end = _mean_rgb(out, 0.75)
    left_rgb = (176, 44, 38)
    right_rgb = (30, 68, 120)
    assert sum(abs(a - b) for a, b in zip(start, left_rgb)) < 90
    assert sum(abs(a - b) for a, b in zip(end, right_rgb)) < 90
    for channel in range(3):
        low = min(left_rgb[channel], right_rgb[channel]) - 25
        high = max(left_rgb[channel], right_rgb[channel]) + 25
        assert low <= mid[channel] <= high
    black = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(out),
         "-vf", "blackdetect=d=0.1:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert "black_start" not in black.stderr


def test_cross_style_transition_is_flagged_in_the_manifest(tmp_path: Path) -> None:
    left = _solid(tmp_path / "grey.mp4", "0x808080", 2.0)
    right = _solid(tmp_path / "green.mp4", "0x00B400", 2.0)
    result, _ = _render(tmp_path, left, right, "ink_dissolve", duration=0.6)
    check = result["colour"]
    assert check["warning"] == "style_jump"
    assert check["delta_e"] > 12


def test_hard_cut_is_exempted_with_a_transition_manifest(tmp_path: Path) -> None:
    frames = [Image.new("RGB", (270, 480), (180, 180, 180)) for _ in range(24)]
    frames += [Image.new("RGB", (270, 480), (120, 120, 120)) for _ in range(24)]
    video = _encode(frames, tmp_path / "cut.mp4")

    without = check_temporal_continuity(video)
    assert without["status"] == FAIL
    assert "TEMPORAL_FRAME_JUMP" in without["codes"]

    manifest = {
        "shots": [{"duration_seconds": 1.0}, {"duration_seconds": 1.0}],
        "sequence": {"transitions": []},
    }
    with_manifest = check_temporal_continuity(video, transition_manifest=manifest)
    assert with_manifest["status"] == PASS
    assert with_manifest["exempted_jumps"]
    assert with_manifest["frame_jumps"] == []


def test_transition_window_is_exempted(tmp_path: Path) -> None:
    frames = [Image.new("RGB", (270, 480), (180, 180, 180)) for _ in range(24)]
    frames += [Image.new("RGB", (270, 480), (120, 120, 120)) for _ in range(24)]
    video = _encode(frames, tmp_path / "cut2.mp4")
    manifest = {
        "shots": [{"duration_seconds": 1.0}, {"duration_seconds": 1.0}],
        "sequence": {"transitions": [{"before_index": 1, "spec": {"duration_s": 0.4}}]},
    }
    result = check_temporal_continuity(video, transition_manifest=manifest)
    assert result["status"] == PASS
    assert result["known_windows"][0] == [1.0, 1.4]


def test_sequence_duration_matches_plan_total(tmp_path: Path) -> None:
    left = _solid(tmp_path / "left.mp4", "0xB02C26", 1.4)
    right = _solid(tmp_path / "right.mp4", "0x1E4478", 1.0)
    plan = MotionPlan(
        style_id="ink_wash",
        shots=[
            ShotSpec(id="shot_001", source="a.png", duration_seconds=1.0),
            ShotSpec(id="shot_002", source="b.png", duration_seconds=1.0,
                     transition_in=TransitionSpec(type="ink_dissolve", duration_s=0.4,
                                                  feather=0.12, seed=13)),
        ],
    )
    info = assemble_sequence(plan, [left, right], tmp_path / "sequence", fps=FPS)
    assert info["duration_ok"] is True
    assert info["measured_seconds"] == pytest.approx(2.0, abs=1.0 / FPS + 0.02)
    transition = info["transitions"][0]
    assert transition["timing"]["left_start"] == 1.0
    assert transition["timing"]["right_start"] == 0.0
    assert transition["algorithm"] == "alphamerge_overlay"
