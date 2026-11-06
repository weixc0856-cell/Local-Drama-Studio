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

WAN_FRAMES = {73: 73, 121: 121}


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
    _write(target / "manifest.json", {"project_id": project.project_id, "kind": "keyframes", "jobs": len(jobs)})
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
    frames: int = 121,
    allow_missing_keyframes: bool = False,
    steps: int = 20,
    cfg: float = 5.0,
    shift: float = 8.0,
    pack=None,
) -> dict:
    if project.storyboard is None or project.bible is None:
        raise ValueError("storyboard.json and visual_bible.yaml are required")
    if frames not in WAN_FRAMES:
        raise ValueError(f"frames must be one of {sorted(WAN_FRAMES)}; 121 has known colour drift, check first/last frames")
    project_root = (root / "projects" / project.project_id).resolve()
    keyframes = keyframes_dir or (project_root / "assets" / "keyframes")
    target = out_dir or (project_root / "jobs" / "shots")
    params_dir = target / "params"
    jobs = []
    for index, shot in enumerate(project.storyboard.shots):
        keyframe = latest_output(keyframes / shot.shot_id, shot.shot_id, ".png")
        if keyframe is None and not allow_missing_keyframes:
            raise FileNotFoundError(f"keyframe not found for {shot.shot_id} under {keyframes / shot.shot_id}")
        if pack is not None:
            layers = {"foreground": shot.layers.foreground, "background": shot.layers.background}
            video_prompt = compile_video_prompt(
                pack, camera_move=shot.camera.move.value, primary_motion=shot.motion.primary,
                secondary_motions=shot.motion.secondary, layers=layers)
        else:
            video_prompt = compile_shot_prompts(shot, project.bible)["video_prompt"]
        input_name = f"{project.project_id}_{shot.shot_id}_kf.png"
        params = {
            "positive_prompt": video_prompt,
            "negative_prompt": "",
            "seed": seed_base + index,
            "width": width,
            "height": height,
            "frames": frames,
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
            "reference": {"source": str(keyframe.relative_to(root)).replace("\\", "/") if keyframe else None,
                          "input_name": input_name},
        })
    _write(target / "jobs.json", jobs)
    _write(target / "manifest.json", {"project_id": project.project_id, "kind": "shots",
                                      "frames": frames, "jobs": len(jobs)})
    return {"jobs": str(target / "jobs.json"), "count": len(jobs), "frames": frames,
            "source_seconds": round(frames / 24.0, 2), "out_dir": str(target)}
