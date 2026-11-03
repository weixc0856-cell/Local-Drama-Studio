"""Deterministic production adapters.

The functions here are the only place that maps the editable ProductionScript
to the verified R3 build inputs (ComfyUI jobs, segments.json). Every output
contains explicit paths and hashes; missing inputs fail loudly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .script_engine import ProductionScript

FLUX_WORKFLOW = "workflows/r0_flux_t2i_api.json"


class ProductionError(RuntimeError):
    pass


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _shots(script: Any) -> list[Any]:
    return script.get("shots") if isinstance(script, dict) else script.shots


def _field(item: Any, name: str, default: Any = None) -> Any:
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_jobs(
    script: Any,
    *,
    root: Path,
    episode_root: Path,
    jobs_path: Path,
    workflow: str = FLUX_WORKFLOW,
    seed_base: int = 7100,
    width: int = 576,
    height: int = 1024,
    steps: int = 4,
    cfg: float = 1.0,
) -> dict[str, Any]:
    """Write r1_batch-compatible jobs and per-shot parameter files."""
    params_dir = episode_root / "comfy" / "params"
    params_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for shot in _shots(script):
        shot_id = _field(shot, "shot_id")
        if _field(shot, "type") != "image":
            raise ProductionError(f"{shot_id}: only image shots are supported by the FLUX job builder")
        params = {
            "positive_prompt": _field(shot, "visual_prompt"),
            "negative_prompt": _field(shot, "negative_prompt", ""),
            "seed": seed_base + _field(shot, "index", 0),
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "filename_prefix": f"p1/{shot_id}",
        }
        params_file = params_dir / f"{shot_id}.json"
        params_file.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jobs.append(
            {
                "id": shot_id,
                "workflow": workflow,
                "params": _rel(params_file, root),
                "out": _rel(episode_root / "assets" / "images" / shot_id, root),
            }
        )
    jobs_path.parent.mkdir(parents=True, exist_ok=True)
    jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "jobs": _rel(jobs_path, root),
        "job_count": len(jobs),
        "workflow": workflow,
        "workflow_sha256": _sha256(root / workflow),
    }


def _find_image(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    candidates = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def build_segments(
    script: Any,
    *,
    root: Path,
    episode_root: Path,
    images_dir: Path,
    audio_manifest: Path,
    out_path: Path,
) -> dict[str, Any]:
    """Map shots to R3 segments.json; every shot must have a real image and one bound line."""
    if not audio_manifest.is_file():
        raise ProductionError(f"缺少 audio_manifest.json: {audio_manifest}")
    audio = json.loads(audio_manifest.read_text(encoding="utf-8"))
    if not audio.get("lines"):
        raise ProductionError("audio_manifest.json 没有 lines")
    segments = []
    for shot in _shots(script):
        shot_id = _field(shot, "shot_id")
        image = _find_image(images_dir / shot_id)
        if image is None:
            raise ProductionError(f"{shot_id}: 没有生成图片（{images_dir / shot_id}）")
        segments.append(
            {
                "id": shot_id,
                "type": "image",
                "source": _rel(image, root),
                "duration": _field(shot, "duration_seconds"),
                "motion": _field(shot, "motion"),
                "line_ids": _field(shot, "line_ids"),
                "visual_prompt": _field(shot, "visual_prompt"),
                "sha256": _sha256(image),
            }
        )
    payload = {
        "generated_at": _field(script, "generated_at"),
        "script_sha256": _sha256(episode_root / "production_script.json"),
        "audio_manifest": _rel(audio_manifest, root),
        "segments": segments,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    # Keep the audit record next to the R3 input, without changing its format.
    (out_path.parent / "segments.meta.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"segments": _rel(out_path, root), "count": len(segments)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = root / script_path
    try:
        from .script_engine import ProductionScript

        script = ProductionScript.model_validate(json.loads(script_path.read_text(encoding="utf-8")))
        result = build_segments(
            script,
            root=root,
            episode_root=script_path.parent,
            images_dir=Path(args.images) if Path(args.images).is_absolute() else root / args.images,
            audio_manifest=Path(args.audio) if Path(args.audio).is_absolute() else root / args.audio,
            out_path=Path(args.out) if Path(args.out).is_absolute() else root / args.out,
        )
    except (ProductionError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
