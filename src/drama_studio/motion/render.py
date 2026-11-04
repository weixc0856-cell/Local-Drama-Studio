"""Render a motion plan: one clip per shot, then an optional transition sequence.

The renderer is deliberately a thin FFmpeg graph builder. All style behaviour
comes from ``config/styles.yaml``; all content regions come from the shot plan.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from ..config import find_project_root
from ..quality import check_image, check_video
from ..style_presets import StylePreset, load_style_presets
from .camera import camera_post, camera_pre, camera_chain, intermediate_size, pan_speed
from .local import LayerRefused, LayerRender, prepare_layers
from .spec import H, W, MotionPlan, ShotSpec, resolve_camera
from .texture import make_texture
from .transition import assemble_sequence


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-3000:])
    return proc


def black_frames(video: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(video),
         "-vf", "blackdetect=d=0.1:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    hits = [line for line in proc.stderr.splitlines() if "black_start" in line]
    return {"returncode": proc.returncode, "black_segments": hits}


def sample_frames(video: Path, out_dir: Path, points: list[tuple[str, float]]) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for name, at in points:
        path = out_dir / f"frame_{name}.png"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", str(video),
             "-frames:v", "1", str(path)])
        frames.append({"name": name, "at_seconds": round(max(0.0, at), 3), "path": str(path),
                       **check_image(path)})
    return frames


def _mean_diff(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    width, height = image.size
    x0, y0, x1, y1 = (int(box[0] * (width - 1)), int(box[1] * (height - 1)),
                      int(box[2] * (width - 1)), int(box[3] * (height - 1)))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return round(ImageStat.Stat(image.crop((x0, y0, x1, y1))).mean[0], 4)


def _region_checks(first: Path, mid: Path, shot: ShotSpec, camera) -> dict:
    """Independent look at the animated region and the structure around it.

    For a static camera the guard bands must stay near zero. For a moving camera
    they include the camera move; the note says so instead of pretending the
    numbers isolate local motion.
    """
    left = Image.open(first).convert("L").resize((270, 480))
    right = Image.open(mid).convert("L").resize((270, 480))
    diff = ImageChops.difference(left, right)
    regions = []
    for layer in shot.local_motion:
        mask = layer.mask
        regions.append({
            "layer_id": layer.layer_id,
            "motion_type": layer.motion_type,
            "box": [mask.x0, mask.y0, mask.x1, mask.y1],
            "mean_abs_diff": _mean_diff(diff, (mask.x0, mask.y0, mask.x1, mask.y1)),
        })
    guards = [
        {"band": "sky_top", "box": [0.0, 0.0, 1.0, 0.15],
         "mean_abs_diff": _mean_diff(diff, (0.0, 0.0, 1.0, 0.15))},
        {"band": "upper_structure", "box": [0.0, 0.16, 1.0, 0.44],
         "mean_abs_diff": _mean_diff(diff, (0.0, 0.16, 1.0, 0.44))},
    ]
    static = camera.move == "static"
    return {
        "camera_move": camera.move,
        "isolates_local_motion": static,
        "regions": regions,
        "structure_bands": guards,
        "note": ("静态机位：区域差值可直接用于检查局部微动与结构保护"
                 if static else "机位在运动，结构带差值包含运镜位移，不能单独归因于局部微动"),
    }


def _resolve_path(value: str, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / path)


def _handle_for(plan: MotionPlan, index: int, shot: ShotSpec) -> float:
    required = 0.0
    if index < len(plan.shots) - 1:
        nxt = plan.shots[index + 1].transition_in
        if nxt is not None:
            required = nxt.duration_s
    return round(max(shot.handle_seconds, required), 3)


def _render_shot(
    *,
    plan: MotionPlan,
    index: int,
    shot: ShotSpec,
    preset: StylePreset,
    root: Path,
    out_dir: Path,
    texture: Path,
) -> dict:
    source = _resolve_path(shot.source, root)
    if not source.is_file():
        raise FileNotFoundError(f"{shot.id}: source not found: {source}")
    if shot.static_quality:
        quality_path = _resolve_path(shot.static_quality, root)
        if not quality_path.is_file():
            raise FileNotFoundError(f"{shot.id}: static quality report missing: {quality_path}")
        state = json.loads(quality_path.read_text(encoding="utf-8")).get("overall_status")
        if state not in ("PASS_STATIC", "PARTIAL"):
            raise ValueError(f"{shot.id}: static quality gate is {state}; repair the still first")
    with Image.open(source) as image:
        image = image.convert("RGB")
        source_size = image.size

    handle = _handle_for(plan, index, shot)
    render_duration = round(shot.duration_seconds + handle, 3)
    camera = resolve_camera(
        shot.model_copy(update={"duration_seconds": render_duration}), preset, source_size
    )
    if camera.move == "layered_parallax":
        raise ValueError(
            f"{shot.id}: layered_parallax needs explicit background/foreground layers; "
            "this shot has none")

    if shot.plates:
        # Layered path is opt-in: a shot without plates never enters here, so the
        # existing single-plane output is untouched.
        return _render_layered_shot(
            plan=plan, shot=shot, camera=camera, preset=preset, root=root,
            out_dir=out_dir, texture=texture, render_duration=render_duration,
            handle=handle, source=source, source_size=source_size)

    layers_dir = out_dir / shot.id / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    # Keep the source aspect ratio. Forcing 540x960 squashes a square source
    # and makes every authored mask disagree with the camera-transformed base.
    half_w = W // 2
    half_h = max(2, int(round(source_size[1] * half_w / source_size[0])))
    if half_h % 2:
        half_h += 1
    base_half = image.resize((half_w, half_h), Image.LANCZOS)
    gray_half = base_half.convert("L")
    layers: list[LayerRender] = []
    skipped: list[dict] = []
    for layer_spec in shot.local_motion:
        policy = preset.motion.local_policy.get(layer_spec.motion_type)
        if policy is None:
            raise ValueError(
                f"{shot.id}: {layer_spec.motion_type} is not configured for style {preset.id}"
            )
        if not policy.enabled:
            skipped.append({"layer_id": layer_spec.layer_id, "motion_type": layer_spec.motion_type,
                            "reason": f"{preset.id} 的 local_policy 未启用该类型"})
            continue
        try:
            layers.append(
                prepare_layers(
                    root=root,
                    base_half=base_half,
                    gray_half=gray_half,
                    spec=layer_spec,
                    policy=policy,
                    out_dir=layers_dir,
                    duration=render_duration,
                    fps=plan.fps,
                    regions=shot.regions,
                )
            )
        except LayerRefused as exc:
            # Refuse this local motion only; the shot still renders with the rest.
            skipped.append({
                "layer_id": layer_spec.layer_id,
                "motion_type": layer_spec.motion_type,
                "reason": exc.reason,
                "details": exc.details,
                "source": "region_contract",
            })

    inputs: list[str] = [
        "-framerate", str(plan.fps), "-loop", "1", "-i", str(source),
    ]
    # Standard order: scale to the source-aspect intermediate canvas, composite
    # every local layer there, then apply the camera crop/zoom. The mask and its
    # subject therefore travel through the same transform.
    inter_w, inter_h = intermediate_size(camera, source_size)
    graph = f"[0:v]{camera_pre(camera, plan.fps)}[base];"
    current = "base"
    next_index = 1
    scale_x = inter_w / W
    scale_y = inter_h / H

    def _scaled(expr: str, factor: float) -> str:
        if abs(factor - 1.0) < 1e-9 or expr.strip() in ("0", "0.0"):
            return expr
        return f"({expr})*{factor:.6f}"

    for number, layer in enumerate(layers, start=1):
        labels = []
        for item in layer.inputs:
            if item.sequence:
                inputs += ["-framerate", str(plan.fps), "-i", item.path]
            else:
                inputs += ["-framerate", str(plan.fps), "-loop", "1", "-i", item.path]
            labels.append(f"[{next_index}:v]")
            next_index += 1
        label = f"L{number}"
        if len(labels) == 2:
            graph += f"{labels[0]}{labels[1]}alphamerge[raw{number}];"
            graph += f"[raw{number}]scale={inter_w}:{inter_h}:flags=bicubic[{label}];"
        else:
            graph += f"{labels[0]}scale={inter_w}:{inter_h}:flags=bicubic[{label}];"
        nxt = f"S{number}"
        graph += (
            f"[{current}][{label}]overlay=x='{_scaled(layer.overlay_x, scale_x)}':"
            f"y='{_scaled(layer.overlay_y, scale_y)}':format=auto[{nxt}];"
        )
        current = nxt

    graph += f"[{current}]{camera_post(camera, plan.fps)}[cam];"
    current = "cam"

    texture_path = texture
    inputs += ["-framerate", str(plan.fps), "-loop", "1", "-i", str(texture_path)]
    texture_index = next_index
    next_index += 1
    audio_index = next_index
    inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"]

    opacity = preset.compositing.texture.opacity
    graph += (
        f"[{texture_index}:v]scale={W}:{H}:flags=bicubic[tex];"
        f"[{current}][tex]blend=all_mode=overlay:all_opacity={opacity:.2f},"
        f"format=yuv420p[outv]"
    )

    output = out_dir / f"{shot.id}.mp4"
    cmd = [
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", graph,
        "-map", "[outv]", "-map", f"{audio_index}:a",
        "-t", f"{render_duration:.3f}", "-r", str(plan.fps),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(output),
    ]
    run(cmd)

    points = [("first", 0.2), ("mid", shot.duration_seconds / 2.0),
              ("last", max(0.2, shot.duration_seconds - 0.3))]
    video_check = check_video(output, expected_width=W, expected_height=H)
    sampled = sample_frames(output, out_dir / shot.id / "frames", points)
    by_name = {item["name"]: Path(item["path"]) for item in sampled}
    region_checks = (
        _region_checks(by_name["first"], by_name["mid"], shot, camera)
        if "first" in by_name and "mid" in by_name else None
    )
    return {
        "id": shot.id,
        "source": rel(source, root),
        "source_sha256": sha256(source),
        "source_size": list(source_size),
        "motion_hint": shot.motion,
        "camera": camera.model_dump(),
        "pan_speed_px_s": pan_speed(camera),
        "duration_seconds": shot.duration_seconds,
        "handle_seconds": handle,
        "render_duration_seconds": render_duration,
        "transition_in": shot.transition_in.model_dump() if shot.transition_in else None,
        "static_quality": shot.static_quality,
        "layers": [
            {"layer_id": layer.layer_id, "motion_type": layer.motion_type,
             "overlay_x": layer.overlay_x, "overlay_y": layer.overlay_y, "info": layer.info}
            for layer in layers
        ],
        "layers_skipped": skipped,
        "regions": [region.model_dump() for region in shot.regions],
        "region_model": "semantic" if shot.regions else "legacy",
        "output": rel(output, root),
        "output_sha256": sha256(output),
        "bytes": output.stat().st_size,
        "argv": cmd,
        "video_check": video_check,
        "black_frames": black_frames(output),
        "sample_frames": sampled,
        "region_checks": region_checks,
    }


def _render_layered_shot(
    *,
    plan: MotionPlan,
    shot: ShotSpec,
    camera,
    preset: StylePreset,
    root: Path,
    out_dir: Path,
    texture: Path,
    render_duration: float,
    handle: float,
    source: Path,
    source_size: tuple[int, int],
) -> dict:
    """Render a shot whose motion comes from plates instead of one still.

    Every plate is verified against its recorded hash first: a plate that has
    been edited since the snapshot would silently change the shot.
    """
    from .plates import (CameraState, background_pan, background_scale, compose,
                         load_plate, plate_scale)

    from .plates import enforce_policy

    policy = preset.compositing.parallax
    enforce_policy(policy, shot_id=shot.id, move=str(camera.move), plates=shot.plates)

    if camera.move == "layered_parallax":
        camera = camera.model_copy(update={"move": "slow_push_in"})

    loaded = []
    plates_record = []
    for plate in sorted(shot.plates, key=lambda item: item.z_order):
        loaded.append(load_plate(plate, root))
        path = Path(plate.path)
        path = path if path.is_absolute() else root / path
        digest = sha256(path)
        if digest != plate.sha256:
            raise ValueError(
                f"{shot.id}/{plate.id}: plate sha256 mismatch "
                f"(recorded {plate.sha256[:12]}, file {digest[:12]})")
        plates_record.append({
            "id": plate.id, "source": plate.source, "path": plate.path,
            "sha256": digest, "z_order": plate.z_order,
            "depth_alpha": plate.depth_alpha, "coverage": plate.coverage,
            "anchor": plate.anchor.model_dump() if plate.anchor else None,
            "hole_mask": plate.hole_mask, "hole_mask_sha256": plate.hole_mask_sha256,
            "provenance": plate.provenance.model_dump() if plate.provenance else None,
        })

    frames = max(1, int(round(render_duration * plan.fps)))
    frame_dir = out_dir / shot.id / "plate_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    # Pan travel is measured in output pixels of the background panel; the panel
    # is the background plate scaled so its height matches the output.
    background = next(item for item in loaded if item.spec.coverage == "full_frame")
    panel_width = background.image.width * H / background.image.height
    pan_move = camera.move in ("scroll_pan", "slow_lateral_track")

    states = []
    for index in range(frames):
        states.append(
            CameraState(mode="pan",
                             pan=background_pan(camera, index, frames, panel_width),
                         pan_start=float(camera.pan_start_px) / max(1.0, panel_width),
                         span=W / max(1.0, panel_width))
            if pan_move else
            CameraState(mode="dolly", scale=background_scale(camera, index, frames),
                        focus=camera.focus))

    # The background must be covered on every frame. A window that leaves the
    # plate renders as a black bar; a window that eats into the margin leaves no
    # room for the next cut. Both are refused before a single frame is written.
    margin = policy.background_margin
    for index, state in enumerate(states):
        x0, _, span_x, _ = state.plane_window(1.0)
        if x0 < margin - 1e-6 or x0 + span_x > 1 - margin + 1e-6:
            raise ValueError(
                f"{shot.id}: 第 {index} 帧背景窗口 [{x0:.4f}, {x0 + span_x:.4f}] "
                f"越出画板或余量不足（风格 {preset.id} 要求两侧各留 {margin:.2f}）")

    samples = []
    for index, state in enumerate(states):
        compose(loaded, state, (W, H)).save(frame_dir / f"f_{index:04d}.png")
        if index in (0, frames // 2, frames - 1):
            samples.append({
                "frame": index,
                "mode": state.mode,
                "background": ({"pan": round(state.pan, 6)} if pan_move else
                               {"scale": round(state.scale, 6)}),
                "plate_windows": {item.spec.id: [round(v, 6) for v in
                                                 state.plane_window(item.spec.depth_alpha)]
                                  for item in loaded},
            })

    output = out_dir / f"{shot.id}.mp4"
    inputs = [
        "-framerate", str(plan.fps), "-i", str(frame_dir / "f_%04d.png"),
        "-loop", "1", "-i", str(texture),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
    ]
    graph = (
        f"[1:v]scale={W}:{H}:flags=bicubic[tex];"
        f"[0:v][tex]blend=all_mode=overlay:all_opacity="
        f"{preset.compositing.texture.opacity:.2f},format=yuv420p[outv]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error", *inputs,
        "-filter_complex", graph,
        "-map", "[outv]", "-map", "2:a",
        "-t", f"{render_duration:.3f}", "-r", str(plan.fps),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(output),
    ]
    run(cmd)

    points = [("first", 0.2), ("mid", shot.duration_seconds / 2.0),
              ("last", max(0.2, shot.duration_seconds - 0.3))]
    return {
        "id": shot.id,
        "source": rel(source, root),
        "source_sha256": sha256(source),
        "source_size": list(source_size),
        "motion_hint": shot.motion,
        "camera": camera.model_dump(),
        "render_mode": "plates",
        "plates": plates_record,
        "plate_camera_samples": samples,
        "duration_seconds": shot.duration_seconds,
        "handle_seconds": handle,
        "render_duration_seconds": render_duration,
        "transition_in": shot.transition_in.model_dump() if shot.transition_in else None,
        "static_quality": shot.static_quality,
        "layers": [],
        "layers_skipped": [],
        "regions": [region.model_dump() for region in shot.regions],
        "region_model": "semantic" if shot.regions else "legacy",
        "output": rel(output, root),
        "output_sha256": sha256(output),
        "bytes": output.stat().st_size,
        "argv": cmd,
        "video_check": check_video(output, expected_width=W, expected_height=H),
        "black_frames": black_frames(output),
        "sample_frames": sample_frames(output, out_dir / shot.id / "frames", points),
        "region_checks": None,
    }


def render_plan(
    plan: MotionPlan,
    *,
    root: Path | None = None,
    out_root: Path,
    build_sequence: bool = True,
) -> dict:
    root = (root or find_project_root()).resolve()
    out_root = out_root if out_root.is_absolute() else (root / out_root)
    preset = load_style_presets(root).get(plan.style_id)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = out_root / f"build-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    texture_kind = preset.compositing.texture.kind
    if texture_kind not in ("silk", "raw_paper"):
        raise ValueError(f"{preset.id}: no renderable texture kind ({texture_kind})")
    texture = out_dir / f"texture_{texture_kind}.png"
    texture_info = make_texture(texture_kind, texture)

    shots: list[dict] = []
    clips: list[Path] = []
    for index, shot in enumerate(plan.shots):
        record = _render_shot(
            plan=plan, index=index, shot=shot, preset=preset, root=root,
            out_dir=out_dir, texture=texture,
        )
        shots.append(record)
        clips.append(root / record["output"] if not Path(record["output"]).is_absolute() else Path(record["output"]))
        print(json.dumps({"shot": shot.id, "camera": record["camera"]["move"],
                          "duration": record["duration_seconds"],
                          "layers": len(record["layers"]),
                          "check": record["video_check"]["status"]}, ensure_ascii=False))

    sequence_info = None
    if build_sequence and len(plan.shots) > 1:
        sequence_info = assemble_sequence(plan, clips, out_dir / "sequence", fps=plan.fps)
        sequence_path = Path(sequence_info["sequence"])
        sequence_info["video_check"] = check_video(sequence_path, expected_width=W, expected_height=H)
        sequence_info["black_frames"] = black_frames(sequence_path)
        sequence_info["sha256"] = sha256(sequence_path)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json",
             str(sequence_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        measured = float(json.loads(probe.stdout or "{}").get("format", {}).get("duration") or 0)
        sequence_info["measured_seconds"] = round(measured, 3)
        sequence_info["duration_error_seconds"] = round(measured - plan.total_seconds, 3)
        sequence_info["relative"] = rel(sequence_path, root)
        sequence_info["sample_frames"] = sample_frames(
            sequence_path, out_dir / "sequence" / "frames",
            [("first", 0.5), ("mid", plan.total_seconds / 2.0),
             ("last", max(0.5, plan.total_seconds - 0.5))],
        )

    style_config = root / "config" / "styles.yaml"
    manifest = {
        "stage": "motion.render",
        "style_id": preset.id,
        "style_name": preset.name,
        "style_config": rel(style_config, root),
        "style_config_sha256": sha256(style_config),
        "plan": plan.model_dump(),
        "texture": {**texture_info, "path": rel(texture, root), "sha256": sha256(texture),
                    "opacity": preset.compositing.texture.opacity},
        "shots": shots,
        "sequence": sequence_info,
        "total_seconds": plan.total_seconds,
        "fps": plan.fps,
        "size": [W, H],
        "human_review": {
            "status": "PENDING",
            "note": "机械参数与解码已检查；运动是否自然、风格是否成立必须人工看片",
        },
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "motion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "build": rel(out_dir, root),
        "manifest": rel(manifest_path, root),
        "shots": len(shots),
        "sequence": sequence_info["relative"] if sequence_info else None,
        "sequence_seconds": sequence_info["measured_seconds"] if sequence_info else None,
    }
