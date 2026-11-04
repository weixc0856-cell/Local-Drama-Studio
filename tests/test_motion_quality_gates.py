from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from drama_studio.motion.render import render_plan
from drama_studio.motion.spec import (
    CameraOverride,
    LocalMotionSpec,
    MaskSpec,
    MotionPlan,
    ShotSpec,
    resolve_camera,
)
from drama_studio.motion.camera import camera_chain, camera_post, camera_pre, intermediate_size
from drama_studio.quality import (
    FAIL,
    PASS,
    camera_box_at,
    check_rigid_protection,
    check_temporal_continuity,
)
from drama_studio.style_presets import load_style_presets

ROOT = Path(__file__).resolve().parents[1]


def _encode(frames: list[Image.Image], out: Path, fps: int = 24) -> Path:
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


def _subject_frames(count: int, step: int) -> list[Image.Image]:
    frames = []
    for index in range(count):
        image = Image.new("RGB", (270, 480), (245, 245, 245))
        draw = ImageDraw.Draw(image)
        x = 60 + step * index
        draw.rectangle([x, 200, x + 50, 250], fill=(10, 10, 10))
        frames.append(image)
    return frames


def _shot(box: tuple[float, float, float, float]) -> dict:
    return {
        "id": "shot_001",
        "camera": {"move": "static", "duration_seconds": 1.0, "source_size": [270, 480]},
        "regions": [{
            "id": "subject", "role": "rigid_object", "permission": "locked",
            "box": {"x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]},
        }],
    }


def test_rigid_protection_flags_a_moving_subject(tmp_path: Path) -> None:
    video = _encode(_subject_frames(24, step=2), tmp_path / "moving.mp4")
    result = check_rigid_protection(_shot((0.15, 0.38, 0.55, 0.57)), video)
    assert result["status"] == FAIL
    assert result["code"] == "RIGID_OBJECT_VIOLATION"
    assert result["regions"][0]["violated"] is True
    assert "edge_drift" in result["regions"][0]["reasons"]


def test_rigid_protection_passes_a_static_subject(tmp_path: Path) -> None:
    video = _encode(_subject_frames(24, step=0), tmp_path / "static.mp4")
    result = check_rigid_protection(_shot((0.15, 0.38, 0.55, 0.57)), video)
    assert result["status"] == PASS
    assert result["code"] == "RIGID_PROTECTION_OK"


def test_no_locked_regions_is_not_a_failure(tmp_path: Path) -> None:
    video = _encode(_subject_frames(12, step=0), tmp_path / "plain.mp4")
    result = check_rigid_protection({"id": "shot_001", "regions": []}, video)
    assert result["status"] == PASS
    assert result["code"] == "NO_LOCKED_REGIONS"


def test_temporal_continuity_detects_tail_darkening(tmp_path: Path) -> None:
    frames = []
    for index in range(72):
        if index < 48:
            value = 180
        else:
            value = int(round(180 * (1 - (index - 48) / 24)))
        frames.append(Image.new("RGB", (270, 480), (value, value, value)))
    video = _encode(frames, tmp_path / "tail.mp4")
    result = check_temporal_continuity(video)
    assert result["status"] == FAIL
    assert "TAIL_DARKENING" in result["codes"]
    assert result["tail"]["drop_luma"] > 5


def test_temporal_continuity_detects_a_shot_brightness_jump(tmp_path: Path) -> None:
    frames = [Image.new("RGB", (270, 480), (180, 180, 180)) for _ in range(24)]
    frames += [Image.new("RGB", (270, 480), (120, 120, 120)) for _ in range(24)]
    video = _encode(frames, tmp_path / "cut.mp4")
    result = check_temporal_continuity(video)
    assert result["status"] == FAIL
    assert "TEMPORAL_FRAME_JUMP" in result["codes"]
    assert result["frame_jumps"][0]["seconds"] == pytest.approx(1.0, abs=0.05)


def test_temporal_continuity_passes_a_clean_clip(tmp_path: Path) -> None:
    frames = [Image.new("RGB", (270, 480), (180, 180, 180)) for _ in range(48)]
    video = _encode(frames, tmp_path / "clean.mp4")
    result = check_temporal_continuity(video)
    assert result["status"] == PASS
    assert result["codes"] == []


def test_camera_chain_is_split_without_changing_the_full_chain() -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    shot = ShotSpec(id="shot_001", source="a.png", duration_seconds=5.0,
                    motion="slow push-in")
    camera = resolve_camera(shot, ink, (576, 1024))
    assert camera_chain(camera) == f"{camera_pre(camera)},{camera_post(camera)}"
    assert intermediate_size(camera, (576, 1024)) == (2160, 3840)


def test_camera_box_mapping_expands_with_push_in() -> None:
    ink = load_style_presets(ROOT).get("ink_wash")
    shot = ShotSpec(id="shot_001", source="a.png", duration_seconds=5.0,
                    motion="slow push-in",
                    camera=CameraOverride(move="slow_push_in", scale_end=1.05))
    camera = resolve_camera(shot, ink, (576, 1024)).model_dump()
    start = camera_box_at(camera, [0.45, 0.45, 0.55, 0.55], 0.0)
    end = camera_box_at(camera, [0.45, 0.45, 0.55, 0.55], 5.0)
    assert end[2] - end[0] > start[2] - start[0]
    assert end[3] - end[1] > start[3] - start[1]


def test_workspace_params_expose_motion_quality() -> None:
    from drama_studio.workspace.tasks import MotionRenderParams, QualityParams

    quality = QualityParams(episode_id="ep", motion_manifest="motion_manifest.json")
    assert quality.motion_manifest == "motion_manifest.json"
    assert MotionRenderParams(episode_id="ep").quality is True
    assert MotionRenderParams(episode_id="ep", quality=False).quality is False


def test_square_source_keeps_the_source_aspect_for_layers(tmp_path: Path) -> None:
    source = tmp_path / "square.png"
    Image.new("RGB", (1024, 1024), (200, 200, 200)).save(source)
    plan = MotionPlan(
        style_id="ink_wash",
        shots=[ShotSpec(
            id="shot_001", source=str(source), duration_seconds=0.25, motion="static",
            local_motion=[LocalMotionSpec(
                layer_id="cloud", motion_type="cloud_drift",
                mask=MaskSpec(y0=0.1, y1=0.4), amplitude=8.0, frequency=0.05,
            )],
        )],
    )
    result = render_plan(plan, root=ROOT, out_root=tmp_path / "renders",
                         build_sequence=False)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    shot = manifest["shots"][0]
    first = Path(shot["layers"][0]["info"]["frames_dir"]) / "f_0000.png"
    assert Image.open(first).size == (540, 540)
    argv = shot["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    assert "scale=1920:1920" in graph
    assert "crop=1080:1920" in graph


def test_render_composites_layers_before_the_camera(tmp_path: Path) -> None:
    source = tmp_path / "still.png"
    Image.new("RGB", (576, 1024), (200, 200, 200)).save(source)
    plan = MotionPlan(
        style_id="ink_wash",
        shots=[ShotSpec(
            id="shot_001",
            source=str(source),
            duration_seconds=0.5,
            motion="slow push-in",
            camera=CameraOverride(move="slow_push_in", scale_end=1.05),
            local_motion=[LocalMotionSpec(
                layer_id="cloud", motion_type="cloud_drift",
                mask=MaskSpec(y0=0.1, y1=0.4), amplitude=8.0, frequency=0.05,
            )],
        )],
    )
    result = render_plan(plan, root=ROOT, out_root=tmp_path / "renders",
                         build_sequence=False)
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    argv = manifest["shots"][0]["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    assert graph.index("scale=2160:3840") < graph.index("overlay")
    assert graph.index("overlay") < graph.index("zoompan")
