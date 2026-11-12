"""Assemble a film through the verified r3_build engine.

This module owns no subtitles, mixing, loudness or encoding of its own. It
prepares the two contracts r3_build understands (``segments.json`` and
``audio_manifest.json``), optionally renders deterministic motion for stills,
and writes every build into a new ``renders/build-<stamp>/`` directory.

The previous implementation concatenated the timeline itself. That is exactly
how a finished film ended up with no subtitles, no loudness pass and a stale
narration path. Keeping one build engine is the point of this module.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import paths
from .. import quality
from .assets import ShotAsset, resolve_all
from .audio import AudioError, load_audio_manifest, write_manifest
from .clips import build_clips
from .config import ProductionSettings, load_production
from .motion_plan import build_motion_plan, render_motion
from .static_gate import run_static_gate
from .upscale import UpscaleError, upscale_wan_clips
from .project import FilmProject, project_dir
from .segments import (
    SegmentError,
    build_audio_manifest,
    build_audio_timeline,
    build_segments,
    write_json,
)
from .timeline import build_edit_timeline, build_timeline


class AssembleError(RuntimeError):
    pass


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _load_meta(project_root: Path) -> dict[str, Any]:
    return json.loads((project_root / "project.json").read_text(encoding="utf-8"))


def prepare(
    project: FilmProject,
    root: Path,
    *,
    settings: ProductionSettings | None = None,
) -> dict[str, Any]:
    """Build every input r3_build needs, without running it."""
    if project.storyboard is None:
        raise AssembleError("storyboard.json is required")
    directory = project_dir(root, project.project_id)
    meta = _load_meta(directory)
    settings = settings or load_production(meta)
    if (settings.width, settings.height) != (1080, 1920):
        raise AssembleError(
            f"r3_build is fixed at 1080x1920; project asks for {settings.width}x{settings.height}")
    if settings.fps != 24:
        raise AssembleError(f"r3_build is fixed at 24 fps; project asks for {settings.fps}")

    audio_path = directory / "assets" / "audio" / "audio_manifest.json"
    try:
        audio_manifest = load_audio_manifest(audio_path)
    except AudioError as exc:
        raise AssembleError(
            f"{exc}; run `drama film voice` before assembling") from exc

    assets = resolve_all(directory, [shot.shot_id for shot in project.storyboard.shots])
    timeline = build_edit_timeline(
        project.storyboard,
        audio_manifest,
        settings=settings,
        assets=assets,
    )
    return {
        "directory": directory,
        "meta": meta,
        "settings": settings,
        "audio_manifest": audio_manifest,
        "timeline": timeline,
        "assets": assets,
    }


def _r3_command(
    root: Path,
    directory: Path,
    build_dir: Path,
    settings: ProductionSettings,
    *,
    audio_timeline: Path | None,
) -> list[str]:
    repo = paths.repo_root()
    command = [
        sys.executable,
        str(repo / "scripts" / "r3_build.py"),
        "--segments", str(build_dir / "segments.json"),
        "--audio", str(build_dir / "audio_manifest.json"),
        "--out", str(build_dir),
        "--content-type", settings.content_type,
        "--leading-ms", str(settings.leading_silence_ms),
        "--crossfade", str(settings.crossfade_seconds),
    ]
    if audio_timeline is not None:
        command += [
            "--audio-timeline", str(audio_timeline),
            "--audio-assets", str(repo / "assets" / "audio" / "manifest.json"),
        ]
    return command


def _motion_current(directory: Path, plan, *, root: Path, timeline) -> dict[str, str] | None:
    """Reuse motion clips that are newer than their source still and the right length.

    Re-rendering eight 6-second 1080x1920 clips on every assemble costs minutes
    and produces an identical file; a stale source still or a changed timeline
    duration forces a re-render.
    """
    from .clips import probe_duration

    durations = {entry.shot_id: (entry.end_ms - entry.start_ms) / 1000.0
                 for entry in timeline.entries}
    current: dict[str, str] = {}
    for shot in plan.shots:
        target = directory / "shots" / shot.id / f"{shot.id}_motion.mp4"
        source = root / shot.source
        if not target.is_file() or not source.is_file():
            return None
        if target.stat().st_mtime < source.stat().st_mtime:
            return None
        expected = durations.get(shot.id)
        if expected is None or abs(probe_duration(target) - expected) > 1.0 / 24:
            return None
        current[shot.id] = str(target)
    return current or None


def verify_build(build_manifest: dict, timeline) -> dict:
    """Check that picture, audio and subtitles share the film timeline.

    This is the consistency gate the chain was missing: r3_build already derives
    subtitles from the same lines as the mix, but a stale or hand-edited build
    could still drift. Everything here is an exact comparison, not a heuristic.
    """
    streams = ((build_manifest.get("ffprobe") or {}).get("streams") or [])
    if timeline.narration_events and not any(s.get("codec_type") == "subtitle" for s in streams):
        raise AssembleError("成片没有字幕流；字幕、旁白与画面必须同时存在")
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    final_duration = float(
        video_stream.get("duration")
        or (build_manifest.get("ffprobe") or {}).get("format", {}).get("duration") or 0)
    if abs(final_duration - timeline.total_ms / 1000.0) > 0.2:
        raise AssembleError(
            f"成片时长 {final_duration:.3f}s 与时间轴 {timeline.total_ms / 1000.0:.3f}s 不一致")
    expected_starts = [event.start_ms for event in timeline.narration_events]
    actual_starts = [int(value) for value in (build_manifest.get("line_starts_ms") or [])]
    if expected_starts != actual_starts:
        raise AssembleError(
            "字幕/混音起点与电影时间轴不一致："
            f"expected {expected_starts}, build {actual_starts}")
    return {
        "subtitle_stream": True if timeline.narration_events else False,
        "final_seconds": final_duration,
        "line_starts_ms": actual_starts,
    }


def assemble(
    project: FilmProject,
    root: Path,
    *,
    out: Path | None = None,
    settings: ProductionSettings | None = None,
    with_motion: bool = True,
    force_motion: bool = False,
    skip_static_gate: bool = False,
    force_clips: bool = False,
    dry_run: bool = False,
    allow_overwrite: bool = False,
    write_timeline: bool = True,
) -> dict[str, Any]:
    prepared = prepare(project, root, settings=settings)
    directory: Path = prepared["directory"]
    settings = prepared["settings"]
    timeline = prepared["timeline"]
    assets: dict[str, ShotAsset] = prepared["assets"]

    if out is None:
        build_dir = directory / "renders" / f"build-{_stamp()}"
    else:
        build_dir = out if out.is_absolute() else (root / out)
    projects_root = (root / "projects").resolve()
    if not build_dir.resolve().is_relative_to(projects_root):
        raise AssembleError(f"build directory must live under projects/: {build_dir}")
    if build_dir.exists() and any(build_dir.iterdir()) and not allow_overwrite:
        raise AssembleError(f"build directory is not empty: {build_dir}; choose a new one")
    build_dir.mkdir(parents=True, exist_ok=True)

    static_report = None
    if not skip_static_gate and project.storyboard is not None:
        static_report = run_static_gate(
            directory, project.storyboard, root=root, style_id=project.style_id)

    motion_report: dict[str, Any] | None = None
    if with_motion and project.storyboard is not None:
        plan, info = build_motion_plan(
            directory,
            project.storyboard,
            timeline,
            root=root,
            style_id=project.style_id,
            settings=settings,
            assets=assets,
        )
        if plan is not None and dry_run:
            motion_report = {"plan": info, "render": {"skipped": "dry_run"}}
        elif plan is not None:
            reused = None if force_motion else _motion_current(directory, plan, root=root, timeline=timeline)
            if reused:
                motion_report = {"plan": info, "render": {"reused": True, "clips": reused}}
            else:
                motion_report = {"plan": info, "render": render_motion(directory, plan, root=root)}
            assets = resolve_all(directory, [shot.shot_id for shot in project.storyboard.shots])
        else:
            motion_report = {"plan": info, "render": None}

    clips_report = build_clips(
        directory,
        project.storyboard,
        timeline,
        fps=settings.fps,
        width=settings.width,
        height=settings.height,
        policy=settings.clip_extend_policy,
        force=force_clips,
    )
    upscale_report = None
    if settings.upscale_backend != "lanczos":
        upscale_report = upscale_wan_clips(
            directory,
            [shot.shot_id for shot in project.storyboard.shots],
            backend=settings.upscale_backend,
            width=settings.width,
            height=settings.height,
            denoise=settings.upscale_denoise,
        )
    assets = resolve_all(directory, [shot.shot_id for shot in project.storyboard.shots])

    try:
        segments = build_segments(directory, project.storyboard, timeline, root=root, assets=assets)
        audio_manifest = build_audio_manifest(prepared["audio_manifest"], timeline, root=root)
    except SegmentError as exc:
        raise AssembleError(str(exc)) from exc

    write_json(build_dir / "segments.json", segments)
    write_manifest(build_dir / "audio_manifest.json", audio_manifest)
    write_json(build_dir / "film_timeline.json", timeline.model_dump(mode="json"))
    if write_timeline:
        write_json(directory / "timeline.json", timeline.model_dump(mode="json"))

    audio_timeline = None
    if settings.bgm_asset_id or settings.ambience_asset_id:
        payload = build_audio_timeline(
            prepared["audio_manifest"], timeline, root=root,
            bgm_asset_id=settings.bgm_asset_id,
            ambience_asset_id=settings.ambience_asset_id,
            ambience_gain_db=settings.ambience_gain_db,
        )
        if payload is not None:
            audio_timeline = write_json(build_dir / "audio_timeline.json", payload)

    command = _r3_command(root, directory, build_dir, settings, audio_timeline=audio_timeline)
    quality_command = [
        sys.executable, "-m", "drama_studio.quality",
        "--manifest", str(build_dir / "build_manifest.json"),
    ]
    plan = {
        "project_id": project.project_id,
        "build_dir": _rel(build_dir, root),
        "segments": len(segments),
        "total_seconds": round(timeline.total_ms / 1000.0, 3),
        "kinds": {item["shot_id"]: item["asset_kind"] for item in segments},
        "static_gate": static_report,
        "motion": motion_report,
        "clips": clips_report,
        "upscale": upscale_report,
        "bgm_asset_id": settings.bgm_asset_id,
        "ambience_asset_id": settings.ambience_asset_id,
        "r3_build": command,
        "quality": quality_command,
    }
    write_json(build_dir / "assemble_plan.json", plan)

    if dry_run:
        return {"plan": plan, "build_dir": str(build_dir), "dry_run": True}

    proc = subprocess.run(command, cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    (build_dir / "r3_build.log").write_text(
        (proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        raise AssembleError(
            f"r3_build failed ({proc.returncode}); see {build_dir / 'r3_build.log'}\n"
            f"{proc.stderr[-1500:]}")

    manifest_path = build_dir / "build_manifest.json"
    if not manifest_path.is_file():
        raise AssembleError(f"r3_build produced no build_manifest.json in {build_dir}")
    report = quality.check_build(manifest_path, root=root)
    build_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    consistency = verify_build(build_manifest, timeline)

    assemble_manifest = {
        "schema_version": "1.0",
        "project_id": project.project_id,
        "build_dir": _rel(build_dir, root),
        "style_id": project.style_id,
        "settings": settings.model_dump(mode="json"),
        "static_gate": static_report,
        "motion": motion_report,
        "clips": clips_report,
        "segments_sha256": {
            item["shot_id"]: item.get("sha256") for item in segments
        },
        "quality": {
            "status": report.get("status"),
            "report": _rel(build_dir / "quality_report.json", root),
        },
        "consistency": consistency,
        "outputs": json.loads(manifest_path.read_text(encoding="utf-8")).get("outputs"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(build_dir / "assemble_manifest.json", assemble_manifest)
    return {
        "build_dir": str(build_dir),
        "final": assemble_manifest["outputs"]["final"] if assemble_manifest["outputs"] else None,
        "quality": report.get("status"),
        "total_seconds": plan["total_seconds"],
        "plan": plan,
    }
