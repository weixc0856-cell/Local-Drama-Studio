"""Deterministic FFmpeg assembly from the edit timeline.

Video: shot clips when present, otherwise the approved keyframe as a still.
Audio: per-segment narration placed at its shot span + optional BGM bed.
This module builds or runs one FFmpeg command; it owns no creative decisions.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .assets import latest_output
from .project import FilmProject, project_dir
from .timeline import narration_spans
from .schemas import EditTimeline


def _visual(project_root: Path, shot_id: str, duration: float) -> tuple[str, Path, float]:
    clip = latest_output(project_root / "shots" / shot_id, shot_id, ".mp4")
    if clip is not None:
        return "video", clip, duration
    still = latest_output(project_root / "assets" / "keyframes" / shot_id, shot_id, ".png")
    if still is not None:
        return "image", still, duration
    raise FileNotFoundError(f"{shot_id}: neither clip nor keyframe exists under {project_root}")


def load_narration_manifest(project_root: Path) -> dict:
    path = project_root / "assets" / "audio" / "narration_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing narration manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_assemble_command(
    project_root: Path,
    timeline: EditTimeline,
    narration: dict,
    out_path: Path,
    *,
    bgm: Path | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 18,
) -> list[str]:
    cmd: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    filters: list[str] = []
    visual_labels: list[str] = []
    index = 0

    for entry in timeline.entries:
        duration = (entry.end_ms - entry.start_ms) / 1000.0
        kind, path, _ = _visual(project_root, entry.shot_id, duration)
        if kind == "image":
            cmd += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(path)]
        else:
            cmd += ["-t", f"{duration:.3f}", "-i", str(path)]
        filters.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps={fps}[v{index}]"
        )
        visual_labels.append(f"[v{index}]")
        index += 1

    filters.append("".join(visual_labels) + f"concat=n={len(visual_labels)}:v=1:a=0[vout]")

    segments = {item["id"]: item for item in narration.get("segments", [])}
    spans = narration_spans(timeline)
    audio_labels: list[str] = []
    for line_id, (start_ms, _end_ms) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        record = segments.get(line_id)
        if record is None:
            continue
        wav = project_root / record["wav"]
        if not wav.is_file():
            raise FileNotFoundError(f"narration wav missing: {wav}")
        cmd += ["-i", str(wav)]
        label = f"a{len(audio_labels)}"
        filters.append(f"[{index}:a]aresample=48000,adelay={start_ms}|{start_ms}[{label}]")
        audio_labels.append(f"[{label}]")
        index += 1

    if bgm is not None:
        cmd += ["-stream_loop", "-1", "-t", f"{timeline.total_ms / 1000.0:.3f}", "-i", str(bgm)]
        filters.append(f"[{index}:a]aresample=48000,volume=0.25[abgm]")
        audio_labels.append("[abgm]")
        index += 1

    if not audio_labels:
        cmd += ["-f", "lavfi", "-t", f"{timeline.total_ms / 1000.0:.3f}", "-i", "anullsrc=r=48000:cl=mono"]
        audio_labels.append(f"[{index}:a]")
        index += 1

    if len(audio_labels) == 1:
        filters.append(f"{audio_labels[0]}alimiter=limit=0.95[aout]")
    else:
        filters.append("".join(audio_labels)
                       + f"amix=inputs={len(audio_labels)}:duration=longest:normalize=0,"
                         "alimiter=limit=0.95[aout]")

    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-t", f"{timeline.total_ms / 1000.0:.3f}", str(out_path)]
    return cmd


def assemble(project: FilmProject, root: Path, *, out: Path | None = None, bgm: Path | None = None,
             dry_run: bool = False) -> dict:
    directory = project_dir(root, project.project_id)
    timeline_path = directory / "timeline.json"
    if not timeline_path.is_file():
        raise FileNotFoundError(f"missing timeline: {timeline_path}")
    timeline = EditTimeline.model_validate(json.loads(timeline_path.read_text(encoding="utf-8")))
    narration = load_narration_manifest(directory)
    out_path = out or (directory / "renders" / "final_9x16.mp4")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_assemble_command(directory, timeline, narration, out_path, bgm=bgm)
    if not dry_run:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{proc.stderr[-2000:]}")
    return {"command": cmd, "out": str(out_path), "dry_run": dry_run}
