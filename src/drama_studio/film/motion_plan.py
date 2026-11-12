"""Map a film storyboard onto the deterministic motion renderer.

The motion renderer already owns camera easing, texture compositing and
transition geometry. This module does not re-implement any of that: it turns
``ShotSpec`` camera language into the renderer's mechanical vocabulary and
renders only the still shots. Wan shots are used as generated.

A style pack without a ``styles.yaml`` motion preset is reported as skipped, and
the assembler keeps the r3_build Ken Burns path for those shots. Borrowing
another style's preset would silently change the paper texture and easing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .assets import ShotAsset, resolve_asset, sha256_file
from .config import ProductionSettings, mechanical_camera, motion_preset_for
from .schemas import EditTimeline, Storyboard

MOTION_CLIP = "_motion.mp4"


def motion_source_for(project_root: Path, shot_id: str) -> Path | None:
    directory = project_root / "shots" / shot_id
    target = directory / f"{shot_id}{MOTION_CLIP}"
    return target if target.is_file() else None


def build_motion_plan(
    project_root: Path,
    storyboard: Storyboard,
    timeline: EditTimeline,
    *,
    root: Path,
    style_id: str | None,
    settings: ProductionSettings,
    assets: dict[str, ShotAsset] | None = None,
    only: set[str] | None = None,
):
    """Build a MotionPlan for the shots that are still images.

    Returns ``(plan, skipped)``. ``plan`` is ``None`` when the style has no
    motion preset or when every shot is already a generated clip.
    """
    from drama_studio.motion.spec import (
        CameraOverride, LocalMotionSpec, MaskSpec, MotionPlan, ShotSpec,
    )

    preset = motion_preset_for(style_id, settings.motion)
    if not settings.motion.enabled:
        return None, {"reason": "motion disabled in project.json"}
    if preset is None:
        return None, {"reason": f"no motion preset for style {style_id!r}"}
    if (settings.width, settings.height) != (1080, 1920):
        return None, {"reason": f"motion renderer is fixed at 1080x1920, project uses {settings.width}x{settings.height}"}

    entries = {entry.shot_id: entry for entry in timeline.entries}
    shots = []
    skipped: dict[str, str] = {}
    for shot in storyboard.shots:
        if only and shot.shot_id not in only:
            continue
        entry = entries[shot.shot_id]
        asset = (assets or {}).get(shot.shot_id) or resolve_asset(project_root, shot.shot_id)
        if asset is None:
            skipped[shot.shot_id] = "no asset"
            continue
        source = asset.path
        if asset.kind == "video" and source is not None and source.name.endswith("_motion.mp4"):
            # Re-rendering an existing motion clip must start from the still,
            # not from the previous render.
            from .assets import latest_output
            source = latest_output(project_root / "assets" / "keyframes" / shot.shot_id,
                                   shot.shot_id, ".png")
            if source is None:
                skipped[shot.shot_id] = "motion clip has no source still"
                continue
        elif asset.kind != "image":
            skipped[shot.shot_id] = f"already {asset.kind}"
            continue
        duration = (entry.end_ms - entry.start_ms) / 1000.0
        layers_text = " ".join([
            shot.layers.foreground, shot.layers.midground, shot.layers.background,
        ]).lower()
        local_motion = []
        if any(word in layers_text for word in (
                "cloud", "mist", "fog", "sky", "afterglow", "glow", "bokeh",
                "云", "雾", "霭", "烟")):
            local_motion.append(LocalMotionSpec(
                layer_id="clouds",
                motion_type="cloud_drift",
                mask=MaskSpec(kind="band", x0=0.0, x1=1.0, y0=0.0, y1=0.42,
                              feather_px=50.0),
                amplitude=10.0,
                frequency=0.10,
                direction="ltr",
                easing="ease_in_out",
            ))
        if any(word in layers_text for word in (
                "river", "water", "wave", "lake", "sea",
                "江", "河", "湖", "海", "水", "波", "浪")):
            local_motion.append(LocalMotionSpec(
                layer_id="water",
                motion_type="water_ripple",
                mask=MaskSpec(kind="band", x0=0.0, x1=1.0, y0=0.58, y1=1.0,
                              feather_px=40.0),
                amplitude=8.0,
                frequency=0.18,
                direction="ltr",
                easing="ease_in_out",
            ))
        if any(word in layers_text for word in (
                "tree", "branch", "foliage", "reed", "pine",
                "树", "木", "枝", "柳", "草", "竹")):
            local_motion.append(LocalMotionSpec(
                layer_id="foliage",
                motion_type="leaf_sway",
                mask=MaskSpec(kind="band", x0=0.0, x1=1.0, y0=0.35, y1=0.95,
                              feather_px=45.0),
                amplitude=8.0,
                frequency=0.14,
                direction="ltr",
                easing="ease_in_out",
            ))
        motion_text = " ".join([
            shot.camera.move.value,
            shot.motion.primary,
            *shot.motion.secondary,
        ])
        shots.append(
            ShotSpec(
                id=shot.shot_id,
                source=str(Path(source).resolve().relative_to(Path(root).resolve()).as_posix())
                if source else "",
                duration_seconds=duration,
                motion=motion_text,
                camera=CameraOverride(
                    move=mechanical_camera(shot.camera.move.value),
                    scale_start=1.12 if shot.camera.move.value == "dolly_out" else None,
                    scale_end=(
                        1.12 if shot.camera.move.value in ("dolly_in", "tracking", "crane")
                        else 1.08 if shot.camera.move.value == "static" else None
                    ),
                ),
                local_motion=local_motion,
                handle_seconds=0.0,
                transition_in=None,
                text={
                    "line_ids": ",".join(shot.narration_ids),
                    "visual_prompt": shot.keyframe_note or "",
                },
            )
        )

    if not shots:
        return None, {"reason": "no still shots", "skipped": skipped}
    plan = MotionPlan(
        style_id=preset,
        fps=settings.fps,
        shots=shots,
    )
    return plan, {"preset": preset, "shots": len(shots), "skipped": skipped}


def render_motion(project_root: Path, plan, *, root: Path) -> dict[str, Any]:
    """Render per-shot clips and copy them next to the shot assets."""
    from drama_studio.motion.render import render_plan

    result = render_plan(plan, root=root, out_root=project_root / "motion", build_sequence=False)
    manifest_path = root / result["manifest"]
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    copied: dict[str, dict[str, Any]] = {}
    for record in manifest.get("shots", []):
        source = root / record["output"]
        target = project_root / "shots" / record["id"] / f"{record['id']}{MOTION_CLIP}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        # A hard link would keep the versioned motion build authoritative while
        # making the shot directory resolvable; copy is used because the two
        # paths can be on different volumes.
        import shutil

        shutil.copy2(source, target)
        copied[record["id"]] = {
            "clip": str(target),
            "sha256": sha256_file(target),
            "source": record["output"],
            "camera": (record.get("camera") or {}).get("move"),
            "camera_fallback": (record.get("camera") or {}).get("fallback_reason"),
            "duration_seconds": record.get("duration_seconds"),
        }
    return {
        "build": result["build"],
        "manifest": result["manifest"],
        "clips": copied,
        "shots": len(copied),
    }
