"""Chain Wan segments so one shot becomes a continuous action.

A single 65-frame Wan run at 448x768 is about 2.7 s. A six-second shot needs
either a frozen tail or a second run. This module does the second run: it feeds
the last frame of segment N into segment N+1, then encodes the concatenated
frames as one clip. The shots stay independent; only motion inside a shot is
chained.

This is intentionally a foreground, one-GPU process. It uses the existing
``r1_batch.py`` runner and refuses to run two chains at once.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from drama_studio.application.film.assets import latest_output, sha256_file
from drama_studio.application.film.clips import encode_frames, probe_duration
from drama_studio.application.film.jobs import build_wan_jobs
from drama_studio.application.film.wan_qc import select_clean_prefix
from drama_studio.application.film.project import FilmProject

CHAIN_MANIFEST = "chain_manifest.json"


class ChainError(RuntimeError):
    pass


def _write(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _seam_diff(previous: Path | None, first: Path) -> float | None:
    """Mean absolute difference between the input frame and the new first frame.

    The first frame of a chained segment should be almost identical to the last
    clean frame fed in. A large value means the model re-imagined the scene at
    the seam, which is exactly the jump this chain exists to avoid.
    """
    if previous is None or not previous.is_file() or not first.is_file():
        return None
    try:
        with Image.open(previous) as left, Image.open(first) as right:
            a = left.convert("L")
            b = right.convert("L")
            if a.size != b.size:
                b = b.resize(a.size, Image.LANCZOS)
            return round(ImageStat.Stat(ImageChops.difference(a, b)).mean[0], 3)
    except OSError:
        return None


def _frames(directory: Path) -> list[Path]:
    return sorted((path for path in directory.glob("*.png") if path.is_file()),
                  key=lambda path: path.name)


def chain_shot(
    project: FilmProject,
    root: Path,
    shot_id: str,
    *,
    segments: int = 3,
    frames: int = 49,
    width: int = 448,
    height: int = 768,
    steps: int = 20,
    cfg: float = 5.0,
    shift: float = 8.0,
    seed_base: int = 7100,
    timeout: int = 7200,
    pack=None,
    reuse_first: bool = True,
    reuse_existing: bool = True,
    camera_override: str | None = None,
) -> dict[str, Any]:
    if project.storyboard is None:
        raise ChainError("storyboard.json is required")
    if width % 32 or height % 32:
        raise ChainError(f"Wan width/height must be divisible by 32, got {width}x{height}")
    if segments < 1:
        raise ChainError("segments must be >= 1")
    shot = next((item for item in project.storyboard.shots if item.shot_id == shot_id), None)
    if shot is None:
        raise ChainError(f"unknown shot: {shot_id}")

    # Reuse the normal job builder so the prompt and style metadata cannot drift.
    build_wan_jobs(project, root, frames=frames, width=width, height=height,
                   allow_missing_keyframes=False, pack=pack, seed_base=seed_base,
                   camera_override=camera_override)
    jobs_path = root / "projects" / project.project_id / "jobs" / "shots" / "jobs.json"
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    base_job = next((item for item in jobs if item["id"] == shot_id), None)
    if base_job is None:
        raise ChainError(f"job not generated for {shot_id}")
    base_params = json.loads((root / base_job["params"]).read_text(encoding="utf-8"))

    project_root = root / "projects" / project.project_id
    chain_root = project_root / "shots" / shot_id / "chain"
    chain_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    collected: list[Path] = []
    previous_last: Path | None = None

    for index in range(1, segments + 1):
        out_dir = chain_root / f"seg{index:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        if index == 1 and reuse_first:
            existing = _frames(project_root / "shots" / shot_id)
            if len(existing) == frames:
                for source in existing:
                    target = out_dir / source.name
                    if not target.is_file():
                        target.write_bytes(source.read_bytes())
        segment_reference = (
            {
                "source": str(previous_last.relative_to(root)).replace("\\", "/"),
                "input_name": f"{project.project_id}_{shot_id}_chain{index:02d}.png",
            }
            if index > 1 and previous_last is not None
            else base_job["reference"]
        )
        # Resume: any segment directory with the expected frame count is reused.
        existing = _frames(out_dir)
        if reuse_existing and len(existing) == frames:
            clean, qc = select_clean_prefix(existing)
            if len(clean) < 8:
                raise ChainError(f"segment {index}: only {len(clean)} clean frames")
            seam = _seam_diff(previous_last if index > 1 else None, clean[0])
            previous_last = clean[-1]
            collected.extend(clean)
            records.append({
                "segment": index,
                "frames": len(existing),
                "clean_frames": len(clean),
                "qc": qc,
                "seam_luma_diff": seam,
                "seam_status": "PASS" if seam is None or seam <= 4.0 else "REVIEW",
                "reference": segment_reference,
                "first": str(clean[0].relative_to(root)).replace("\\", "/"),
                "last": str(previous_last.relative_to(root)).replace("\\", "/"),
                "sha256": sha256_file(previous_last),
                "reused": True,
            })
            continue
        params = dict(base_params)
        params.update({
            "frames": frames,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "shift": shift,
            "seed": seed_base + index - 1,
            "filename_prefix": f"{project.project_id}/shots/{shot_id}_chain{index:02d}",
        })
        reference = segment_reference
        params["input_image"] = reference["input_name"]
        params_path = chain_root / f"seg{index:02d}_params.json"
        _write(params_path, params)
        job = {
            "id": f"{shot_id}_chain{index:02d}",
            "workflow": base_job["workflow"],
            "params": str(params_path.relative_to(root)).replace("\\", "/"),
            "out": str(out_dir.relative_to(root)).replace("\\", "/"),
            "reference": reference,
        }
        jobs_file = chain_root / f"seg{index:02d}_job.json"
        _write(jobs_file, [job])
        proc = subprocess.run(
            [sys.executable, "scripts/r1_batch.py", "--jobs", str(jobs_file),
             "--force", "--timeout", str(timeout)],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise ChainError(
                f"segment {index} failed; see {out_dir / 'probe_attempt1.log'}\n"
                f"{proc.stderr[-1500:]}")
        produced = _frames(out_dir)
        if len(produced) != frames:
            raise ChainError(f"segment {index}: expected {frames} frames, got {len(produced)}")
        clean, qc = select_clean_prefix(produced)
        if len(clean) < 8:
            raise ChainError(f"segment {index}: only {len(clean)} clean frames")
        seam = _seam_diff(previous_last if index > 1 else None, clean[0])
        previous_last = clean[-1]
        collected.extend(clean)
        records.append({
            "segment": index,
            "frames": len(produced),
            "clean_frames": len(clean),
            "qc": qc,
            "seam_luma_diff": seam,
            "seam_status": "PASS" if seam is None or seam <= 4.0 else "REVIEW",
            "reference": reference,
            "first": str(clean[0].relative_to(root)).replace("\\", "/"),
            "last": str(previous_last.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(previous_last),
            "reused": False,
        })

    all_frames = collected
    if len(all_frames) < 8:
        raise ChainError(f"{shot_id}: only {len(all_frames)} clean frames across all segments")
    clip = project_root / "shots" / shot_id / f"{shot_id}_wan.mp4"
    encode_frames(all_frames, clip, fps=24)
    manifest = {
        "schema_version": "1.0",
        "project_id": project.project_id,
        "shot_id": shot_id,
        "segments": records,
        "frames": len(all_frames),
        "raw_frames": sum(record["frames"] for record in records),
        "truncated_frames": sum(record["frames"] - record["clean_frames"] for record in records),
        "width": width,
        "height": height,
        "fps": 24,
        "source_seconds": probe_duration(clip),
        "clip": str(clip.relative_to(root)).replace("\\", "/"),
        "clip_sha256": sha256_file(clip),
        "prompt": base_params.get("positive_prompt"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write(project_root / "shots" / shot_id / CHAIN_MANIFEST, manifest)
    return manifest
