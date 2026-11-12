"""Turn Wan PNG frame runs into shot clips and fit them to the edit timeline.

Wan saves PNG frames, not MP4. The original film assembler looked only for
``*.mp4``, so a completed Wan run was silently replaced by the keyframe. This
module owns the missing step and records the three lengths that must never be
conflated:

* ``source_seconds``   - what the model actually produced
* ``target_seconds``   - what the edit timeline needs
* ``effective_seconds``- what the encoded clip really is

A clip shorter than its target is extended with a last-frame hold by default.
Slowing a moving shot down is opt-in, because it can damage motion continuity.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from drama_studio.application.film.assets import ShotAsset, resolve_asset, resolve_for_encoding, sha256_file
from drama_studio.domain.film.schemas import EditTimeline, Storyboard

ExtendPolicy = Literal["hold_last", "slow", "trim"]
W, H = 1080, 1920
CLIP_MANIFEST = "clip_manifest.json"


class ClipError(RuntimeError):
    pass


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise ClipError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-2000:])
    return proc


def probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise ClipError(f"cannot probe {path}: {proc.stderr[-400:]}")
    return round(float(proc.stdout.strip() or 0.0), 6)


def _frame_pattern(frames: list[Path]) -> tuple[Path, int] | None:
    match = re.match(r"^(.*?)(\d+)(\D*)$", frames[0].name)
    if not match:
        return None
    prefix, digits, suffix = match.groups()
    expected = [f"{prefix}{index:0{len(digits)}d}{suffix}"
                for index in range(int(digits), int(digits) + len(frames))]
    if [frame.name for frame in frames] != expected:
        return None
    directory = frames[0].parent
    return directory / f"{prefix}%0{len(digits)}d{suffix}", int(digits)


def encode_frames(frames: list[Path], out: Path, *, fps: int = 24) -> Path:
    """Encode a contiguous Wan frame run without reordering a single frame."""
    if len(frames) < 2:
        raise ClipError(f"need at least two frames, got {len(frames)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    pattern = _frame_pattern(frames)
    if pattern is not None:
        path, start = pattern
        cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
               "-start_number", str(start), "-i", str(path),
               "-c:v", "libx264", "-crf", "18", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-an", str(out)]
    else:
        list_file = out.parent / f"{out.stem}_frames.txt"
        lines = []
        for frame in frames:
            lines.append(f"file '{frame.resolve().as_posix()}'")
            lines.append(f"duration {1.0 / fps:.6f}")
        lines.append(f"file '{frames[-1].resolve().as_posix()}'")
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
               "-i", str(list_file), "-r", str(fps),
               "-c:v", "libx264", "-crf", "18", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-an", str(out)]
    run(cmd)
    return out


def fit_clip(
    src: Path,
    out: Path,
    *,
    target_seconds: float,
    policy: ExtendPolicy = "hold_last",
    fps: int = 24,
    width: int = W,
    height: int = H,
) -> dict[str, Any]:
    """Fit one clip to ``target_seconds`` and return the measured lengths."""
    source_seconds = probe_duration(src)
    if abs(source_seconds - target_seconds) < 1.0 / fps:
        vf = (f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},setsar=1,fps={fps}")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-t", f"{target_seconds:.3f}", str(out)])
        return {"policy": "none", "source_seconds": source_seconds,
                "target_seconds": target_seconds,
                "effective_seconds": probe_duration(out)}

    if target_seconds < source_seconds:
        vf = (f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},setsar=1,fps={fps}")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-t", f"{target_seconds:.3f}", str(out)])
        return {"policy": "trim", "source_seconds": source_seconds,
                "target_seconds": target_seconds,
                "effective_seconds": probe_duration(out)}

    extra = target_seconds - source_seconds
    if policy == "slow":
        ratio = target_seconds / source_seconds
        vf = (f"setpts=PTS*{ratio:.6f},"
              f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},setsar=1,fps={fps}")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-t", f"{target_seconds:.3f}", str(out)])
        applied = "slow"
    elif policy == "trim":
        # Refuse to pretend a shorter source covers the target.
        raise ClipError(
            f"{src.name}: source {source_seconds:.3f}s is shorter than target "
            f"{target_seconds:.3f}s and policy=trim cannot extend it")
    else:
        vf = (f"tpad=stop_mode=clone:stop_duration={extra:.3f},"
              f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},setsar=1,fps={fps}")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-t", f"{target_seconds:.3f}", str(out)])
        applied = "hold_last"
    return {"policy": applied, "source_seconds": source_seconds,
            "target_seconds": target_seconds,
            "effective_seconds": probe_duration(out)}


def _color_drift(first: Path, last: Path) -> float | None:
    """Mean LAB distance between the first and last Wan frame.

    121 frames has a measured colour-drift risk. This records the risk; it does
    not decide whether the shot is usable.
    """
    try:
        from drama_studio.application.quality import image_metrics

        a = image_metrics(first)
        b = image_metrics(last)
        left = a.get("lab_mean") or []
        right = b.get("lab_mean") or []
        if len(left) == 3 and len(right) == 3:
            return round(sum(abs(float(x) - float(y)) for x, y in zip(left, right)), 2)
    except Exception:
        return None
    return None


def _manifest_for(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "qc" / CLIP_MANIFEST
    if path.is_file():
        try:
            return path, json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return path, {"schema_version": "1.0", "clips": {}}


def build_clips(
    project_root: Path,
    storyboard: Storyboard,
    timeline: EditTimeline,
    *,
    fps: int = 24,
    width: int = W,
    height: int = H,
    policy: ExtendPolicy = "hold_last",
    force: bool = False,
) -> dict[str, Any]:
    """Encode every image-sequence or video shot to a timeline-length clip.

    Still images are deliberately left alone: a still is rendered by the motion
    stage (camera move) or by r3_build Ken Burns, not by a frame encoder.
    """
    manifest_path, manifest = _manifest_for(project_root)
    entries = {entry.shot_id: entry for entry in timeline.entries}
    results: dict[str, Any] = dict(manifest.get("clips") or {})
    changed = 0
    for shot in storyboard.shots:
        entry = entries.get(shot.shot_id)
        if entry is None:
            continue
        target = (entry.end_ms - entry.start_ms) / 1000.0
        asset = resolve_for_encoding(project_root, shot.shot_id)
        if asset is None or asset.kind == "image":
            continue
        if asset.kind == "image_sequence":
            raw = project_root / "shots" / shot.shot_id / f"{shot.shot_id}_wan.mp4"
            if not raw.is_file() or force:
                encode_frames(list(asset.frames), raw, fps=fps)
            source = raw
            source_hash = asset.sha256 or sha256_file(raw)
            source_kind = "image_sequence"
            drift = _color_drift(asset.frames[0], asset.frames[-1])
        else:
            drift = None
        if asset.kind == "video":
            assert asset.path is not None
            source = asset.path
            source_hash = asset.sha256 or sha256_file(source)
            source_kind = "video"

        out = project_root / "shots" / shot.shot_id / f"{shot.shot_id}_clip.mp4"
        if source.name.endswith("_clip.mp4"):
            wan = project_root / "shots" / shot.shot_id / f"{shot.shot_id}_wan.mp4"
            if wan.is_file():
                source = wan
                source_hash = sha256_file(wan)
                source_kind = "video"
        if source.name.endswith("_motion.mp4"):
            # The deterministic motion renderer already produced a clip at the
            # exact timeline length; re-encoding it would soften it for nothing.
            motion_seconds = probe_duration(source)
            if abs(motion_seconds - target) > 1.0 / fps:
                raise ClipError(
                    f"{shot.shot_id}: motion clip is {motion_seconds:.3f}s but timeline needs "
                    f"{target:.3f}s; run `drama film motion --force`")
            results[shot.shot_id] = {
                "shot_id": shot.shot_id, "source_kind": "motion",
                "source": str(source), "source_sha256": source_hash,
                "target_seconds": round(target, 3), "fps": fps,
                "policy": "none", "source_seconds": probe_duration(source),
                "effective_seconds": probe_duration(source),
                "output": str(source), "output_sha256": source_hash,
            }
            continue
        if source.resolve() == out.resolve() and out.is_file() and not force:
            results[shot.shot_id] = dict(previous) if (previous := results.get(shot.shot_id)) else {
                "shot_id": shot.shot_id, "source_kind": source_kind, "source": str(source),
                "source_sha256": source_hash, "target_seconds": round(target, 3),
                "fps": fps, "policy": policy, "effective_seconds": probe_duration(out),
                "output": str(out), "output_sha256": sha256_file(out),
            }
            continue
        record = {
            "shot_id": shot.shot_id,
            "source_kind": source_kind,
            "source": str(source),
            "source_sha256": source_hash,
            "target_seconds": round(target, 3),
            "fps": fps,
            "policy": policy,
            "color_drift_lab": drift,
        }
        previous = results.get(shot.shot_id) or {}
        reuse = (
            not force
            and out.is_file()
            and previous.get("source_sha256") == source_hash
            and abs(float(previous.get("target_seconds") or 0) - target) < 0.001
            and previous.get("policy") == policy
        )
        if reuse:
            results[shot.shot_id] = previous
            continue
        measured = fit_clip(source, out, target_seconds=target, policy=policy,
                            fps=fps, width=width, height=height)
        record.update(measured)
        record["output"] = str(out)
        record["output_sha256"] = sha256_file(out)
        results[shot.shot_id] = record
        changed += 1

    payload = {
        "schema_version": "1.0",
        "project_id": storyboard.project_id,
        "fps": fps,
        "size": [width, height],
        "clips": results,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path), "clips": len(results), "changed": changed}
