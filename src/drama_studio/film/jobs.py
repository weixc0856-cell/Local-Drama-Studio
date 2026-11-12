"""Generate ComfyUI job files from a storyboard (no execution).

Keyframes use the FLUX.3 workflow; shots use the Wan2.2 TI2V 5B workflow.
Running the jobs is a separate, GPU-owning step (scripts/r1_batch.py).
"""

from __future__ import annotations

import json
from pathlib import Path

from .assets import latest_output
from .project import FilmProject
from ..style_engine import compile_image_prompt, compile_video_prompt
from .prompts import compile_shot_prompts
from .schemas import Storyboard, VisualBible

FLUX_WORKFLOW = "workflows/flux3_t2i_api.json"
WAN_WORKFLOW = "workflows/r0_wan_i2v_api.json"

WAN_FRAMES = {49: 49, 65: 65, 73: 73, 81: 81, 121: 121}


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_keyframe_jobs(
    project: FilmProject,
    root: Path,
    *,
    out_dir: Path | None = None,
    seed_base: int = 9100,
    width: int = 576,
    height: int = 1024,
    steps: int = 16,
    cfg: float = 1.0,
    pack=None,
) -> dict:
    if project.storyboard is None or project.bible is None:
        raise ValueError("storyboard.json and visual_bible.yaml are required")
    project_root = (root / "projects" / project.project_id).resolve()
    target = out_dir or (project_root / "jobs" / "keyframes")
    params_dir = target / "params"
    if pack is None and project.style_id:
        try:
            from ..style_engine import get_pack
            pack = get_pack(root, project.style_id)
        except KeyError:
            pack = None
    style_meta = {
        "style_id": getattr(getattr(pack, "identity", None), "id", None),
        "style_version": getattr(getattr(pack, "identity", None), "version", None),
    }
    jobs = []
    for index, shot in enumerate(project.storyboard.shots):
        if pack is not None:
            layers = {"foreground": shot.layers.foreground, "midground": shot.layers.midground,
                      "background": shot.layers.background}
            subject = f"scene {shot.scene_id}"
            if not shot.character_in_frame:
                subject += ", no people, empty landscape"
            keyframe_prompt = compile_image_prompt(
                pack, subject=subject, layers=layers, camera_move=shot.camera.move.value,
                extra_note=shot.keyframe_note)
        else:
            keyframe_prompt = compile_shot_prompts(shot, project.bible)["keyframe_prompt"]
        params = {
            "positive_prompt": keyframe_prompt,
            "seed": seed_base + index,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "filename_prefix": f"{project.project_id}/keyframes/{shot.shot_id}",
            **style_meta,
        }
        params_path = params_dir / f"{shot.shot_id}.json"
        _write(params_path, params)
        jobs.append({
            "id": shot.shot_id,
            "workflow": FLUX_WORKFLOW,
            "params": str(params_path.relative_to(root)).replace("\\", "/"),
            "out": str((project_root / "assets" / "keyframes" / shot.shot_id).relative_to(root)).replace("\\", "/"),
        })
    _write(target / "jobs.json", jobs)
    _write(target / "manifest.json", {"project_id": project.project_id, "kind": "keyframes",
                                      "jobs": len(jobs), **style_meta})
    return {"jobs": str(target / "jobs.json"), "count": len(jobs), "out_dir": str(target)}


def build_wan_jobs(
    project: FilmProject,
    root: Path,
    *,
    keyframes_dir: Path | None = None,
    out_dir: Path | None = None,
    seed_base: int = 7100,
    width: int = 576,
    height: int = 1024,
    frames: int | None = None,
    allow_missing_keyframes: bool = False,
    steps: int = 20,
    cfg: float = 5.0,
    shift: float = 8.0,
    pack=None,
    camera_override: str | None = None,
) -> dict:
    if project.storyboard is None or project.bible is None:
        raise ValueError("storyboard.json and visual_bible.yaml are required")
    if frames is not None and frames not in WAN_FRAMES:
        raise ValueError(f"frames must be one of {sorted(WAN_FRAMES)} (4n+1); 121 has known colour drift")
    project_root = (root / "projects" / project.project_id).resolve()
    keyframes = keyframes_dir or (project_root / "assets" / "keyframes")
    target = out_dir or (project_root / "jobs" / "shots")
    params_dir = target / "params"
    if pack is None and project.style_id:
        try:
            from ..style_engine import get_pack
            pack = get_pack(root, project.style_id)
        except KeyError:
            pack = None
    style_meta = {
        "style_id": getattr(getattr(pack, "identity", None), "id", None),
        "style_version": getattr(getattr(pack, "identity", None), "version", None),
    }
    jobs = []
    for index, shot in enumerate(project.storyboard.shots):
        keyframe = latest_output(keyframes / shot.shot_id, shot.shot_id, ".png")
        if keyframe is None and not allow_missing_keyframes:
            raise FileNotFoundError(f"keyframe not found for {shot.shot_id} under {keyframes / shot.shot_id}")
        # 73 frames is the measured safe default (3.04 s); 121 covers 5.04 s.
        # A longer target is still generated at 121 and extended by film clips.
        shot_frames = frames or (121 if shot.duration_seconds > 3.5 else 73)
        if width % 32 or height % 32:
            raise ValueError(f"Wan width/height must be divisible by 32, got {width}x{height}")
        if pack is not None:
            from .prompts import FILM_NEGATIVE, cinematic_video_prefix, physical_motion_for, motion_phrase

            layers = {"foreground": shot.layers.foreground, "background": shot.layers.background}
            video_prompt = compile_video_prompt(
                pack, camera_move=camera_override or shot.camera.move.value,
                primary_motion=motion_phrase(
                    "environment_drift" if camera_override == "static" else shot.motion.primary),
                secondary_motions=shot.motion.secondary, layers=layers)
            physical = physical_motion_for(shot)
            if camera_override == "static" and physical:
                physical = "; ".join(
                    part for part in physical.split("; ") if not part.startswith("camera"))
            prefix = ("locked-off camera, no camera movement, preserve architecture. "
                      if camera_override == "static" else cinematic_video_prefix(shot) + ". ")
            video_prompt = prefix + video_prompt
            if physical:
                video_prompt = video_prompt + ". physical motion: " + physical
        else:
            video_prompt = compile_shot_prompts(shot, project.bible)["video_prompt"]
        from .prompts import FILM_NEGATIVE as _FILM_NEGATIVE
        negative = _FILM_NEGATIVE
        if pack is not None:
            avoid = getattr(getattr(pack, "video", None), "avoid", None) or []
            if avoid:
                negative = negative + ", " + ", ".join(avoid)
        input_name = f"{project.project_id}_{shot.shot_id}_kf.png"
        params = {
            "positive_prompt": video_prompt,
            "negative_prompt": negative,
            "seed": seed_base + index,
            "width": width,
            "height": height,
            "frames": shot_frames,
            "source_seconds": round(shot_frames / 24.0, 3),
            "target_seconds": round(shot.duration_seconds, 3),
            "steps": steps,
            "cfg": cfg,
            "shift": shift,
            "input_image": input_name,
            "filename_prefix": f"{project.project_id}/shots/{shot.shot_id}",
        }
        params_path = params_dir / f"{shot.shot_id}.json"
        _write(params_path, params)
        jobs.append({
            "id": shot.shot_id,
            "workflow": WAN_WORKFLOW,
            "params": str(params_path.relative_to(root)).replace("\\", "/"),
            "out": str((project_root / "shots" / shot.shot_id).relative_to(root)).replace("\\", "/"),
            "reference": {
                # Resolve the newest keyframe at run time: a later keyframe
                # regeneration must not silently leave Wan pinned to an old image.
                "shot_id": shot.shot_id,
                "selector": "latest",
                "keyframe_dir": str((keyframes / shot.shot_id).relative_to(root)).replace("\\", "/"),
                "pinned_source": str(keyframe.relative_to(root)).replace("\\", "/") if keyframe else None,
                "pinned_sha256": _sha256(keyframe) if keyframe else None,
                "input_name": input_name,
            },
        })
    _write(target / "jobs.json", jobs)
    _write(target / "manifest.json", {"project_id": project.project_id, "kind": "shots",
                                      "frames": frames, "jobs": len(jobs), **style_meta})
    return {"jobs": str(target / "jobs.json"), "count": len(jobs), "frames": frames,
            "out_dir": str(target)}
