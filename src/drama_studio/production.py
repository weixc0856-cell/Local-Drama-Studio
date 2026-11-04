"""Deterministic production adapters.

The functions here are the only place that maps the editable ProductionScript
to the verified R3 build inputs (ComfyUI jobs, segments.json). Every output
contains explicit paths and hashes; missing inputs fail loudly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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


def build_aesthetic_jobs(
    plan: Any,
    *,
    root: Path,
    snapshot_dir: Path,
    variant_id: str,
    workflow: str = FLUX_WORKFLOW,
    seed_base: int = 8100,
    width: int = 576,
    height: int = 1024,
    steps: int = 4,
    cfg: float = 1.0,
) -> dict[str, Any]:
    """Freeze one A/B variant into a snapshot and write r1_batch-compatible jobs.

    The snapshot is never overwritten: the caller passes a new directory per
    run. Every job carries the compiled prompt, the six-dimension spec hash and
    the workflow/style hashes so a generated image can be traced back.
    """
    from .aesthetics import compile_prompt
    from .style_presets import load_style_presets

    snapshot_dir = snapshot_dir if snapshot_dir.is_absolute() else (root / snapshot_dir)
    if snapshot_dir.exists() and any(snapshot_dir.iterdir()):
        raise ProductionError(f"snapshot dir already exists and is not empty: {snapshot_dir}")
    (snapshot_dir / "params").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "aesthetic").mkdir(parents=True, exist_ok=True)
    (snapshot_dir.parent / "images").mkdir(parents=True, exist_ok=True)

    preset = load_style_presets(root).get(plan.style_id)
    workflow_path = root / workflow
    workflow_text = workflow_path.read_text(encoding="utf-8")
    negative_supported = "{{negative_prompt}}" in workflow_text
    jobs = []
    prompt_records = []
    for index, shot_set in enumerate(plan.shots, start=1):
        variant = plan.variant(shot_set.shot_id, variant_id)
        compiled = compile_prompt(shot_set, variant, preset, negative_supported=negative_supported)
        seed = seed_base + index
        params = {
            "positive_prompt": compiled.prompt,
            "negative_prompt": compiled.negative_prompt,
            "seed": seed,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "filename_prefix": f"aesthetic/{preset.id}/{shot_set.shot_id}_{variant_id}",
        }
        params_path = snapshot_dir / "params" / f"{shot_set.shot_id}_{variant_id}.json"
        params_path.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        prompt_path = snapshot_dir / "prompts" / f"{shot_set.shot_id}_{variant_id}.json"
        prompt_path.write_text(
            json.dumps(compiled.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        from .aesthetics import design_for_quality

        design_path = snapshot_dir / "aesthetic" / f"{shot_set.shot_id}_{variant_id}.json"
        design_path.write_text(
            json.dumps(design_for_quality(shot_set, variant_id), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        prompt_records.append(compiled.model_dump())
        jobs.append(
            {
                "id": f"{shot_set.shot_id}_{variant_id}",
                "workflow": workflow,
                "params": _rel(params_path, root),
                "out": _rel(snapshot_dir.parent / "images" / shot_set.shot_id / variant_id, root),
                "aesthetic": _rel(design_path, root),
                "prompt_record": _rel(prompt_path, root),
            }
        )

    jobs_path = snapshot_dir / f"jobs_{variant_id}.json"
    jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path = snapshot_dir / "aesthetic_plan.json"
    plan_path.write_text(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    style_config = root / "config" / "styles.yaml"
    provenance = {
        "style_id": preset.id,
        "variant_id": variant_id,
        "style_config": _rel(style_config, root),
        "style_config_sha256": _sha256(style_config),
        "workflow": workflow,
        "workflow_sha256": _sha256(workflow_path),
        "plan_sha256": _sha256(plan_path),
        "negative_supported": negative_supported,
        "negative_note": (
            "workflow 引用了 {{negative_prompt}}"
            if negative_supported
            else "当前 FLUX.2 工作流将负向条件 ConditioningZeroOut 且 CFG=1.0；负向提示词仅记录，不作为控制"
        ),
        "generation": {"seed_base": seed_base, "width": width, "height": height,
                       "steps": steps, "cfg": cfg},
        "prompts": prompt_records,
    }
    (snapshot_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "snapshot": _rel(snapshot_dir, root),
        "jobs": _rel(jobs_path, root),
        "jobs_count": len(jobs),
        "variant": variant_id,
        "negative_supported": negative_supported,
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


def _audio_line_timing(audio_manifest: Path, default_gap_ms: int) -> dict[int, tuple[float, int]]:
    """Per-line (speech seconds, trailing pause ms), using r3_build's pause rule."""
    data = json.loads(audio_manifest.read_text(encoding="utf-8"))
    timing: dict[int, tuple[float, int]] = {}
    for line in data.get("lines") or []:
        index = int(line["index"])
        timing[index] = (
            float(line["duration_seconds"]),
            int(line.get("pause_after_ms", default_gap_ms)),
        )
    return timing


def _aligned_duration(shot: Any, timing: dict[int, tuple[float, int]], leading_ms: int, *, first: bool) -> float:
    """Duration that lands the shot boundary exactly on the next line's speech start.

    r3_build places speech at ``leading_ms + sum(previous speech + pause)``. The
    first shot must therefore absorb the leading silence so shot 2 starts on
    speech 2, and every shot ends after its last line's trailing pause.
    """
    total = leading_ms / 1000.0 if first else 0.0
    for line_id in _field(shot, "line_ids") or []:
        try:
            index = int(str(line_id).rsplit("_", 1)[-1])
        except ValueError as exc:
            raise ProductionError(f"{_field(shot, 'shot_id')}: 非法的 line_id {line_id!r}") from exc
        if index not in timing:
            raise ProductionError(
                f"{_field(shot, 'shot_id')}: audio_manifest 中没有 line {index}（{line_id}）"
            )
        speech, pause = timing[index]
        total += speech + pause / 1000.0
    if total <= 0:
        raise ProductionError(f"{_field(shot, 'shot_id')}: 对齐后时长为 0")
    return round(total, 3)


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise ProductionError(f"无法读取时长：{path}: {proc.stderr[-400:]}")
    try:
        return round(float(json.loads(proc.stdout)["format"]["duration"]), 3)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ProductionError(f"无法读取时长：{path}") from exc


def _load_regions(path: Path | None) -> dict[str, dict[str, Any]]:
    """Load authored regions and layers for each shot.

    Two formats share one file and one parser:

    * legacy: ``"shot_001": [layer, ...]`` — masks only, no semantic regions;
    * current: ``"shot_001": {"regions": [...], "layers": [...]}``.

    The legacy form is kept so existing experiment files still load, but it is
    recorded as ``legacy`` in the plan metadata. New production fixtures should
    use the semantic form; the renderer refuses a layer that targets a locked
    region and auto-subtracts locked regions from every layer that touches them.
    """
    if path is None:
        return {}
    if not path.is_file():
        raise ProductionError(f"缺少 local motion 区域文件：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("shots") if isinstance(data, dict) and "shots" in data else data
    if not isinstance(raw, dict):
        raise ProductionError("motion regions 必须是 {shot_id: [layer, ...]} 或 "
                              "{shot_id: {regions, layers}}")
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        shot_id = str(key)
        if value is None:
            out[shot_id] = {"regions": [], "layers": [], "model": "legacy"}
            continue
        if isinstance(value, list):
            out[shot_id] = {"regions": [], "layers": list(value), "model": "legacy"}
            continue
        if not isinstance(value, dict):
            raise ProductionError(f"{shot_id}: 区域条目必须是列表或对象")
        unknown = set(value) - {"regions", "layers", "local_motion", "note"}
        if unknown:
            raise ProductionError(f"{shot_id}: 未知字段 {sorted(unknown)}")
        if "layers" in value and "local_motion" in value:
            raise ProductionError(f"{shot_id}: layers 与 local_motion 只能二选一")
        layers = value.get("layers", value.get("local_motion", [])) or []
        out[shot_id] = {
            "regions": list(value.get("regions") or []),
            "layers": list(layers),
            "model": "semantic",
        }
    return out


def build_motion_plan(
    script: Any,
    *,
    root: Path,
    episode_root: Path,
    images_dir: Path,
    audio_manifest: Path,
    out_path: Path,
    preset: Any,
    regions_path: Path | None = None,
    align_audio: bool = False,
    leading_ms: int = 0,
    gap_ms: int = 800,
    tail_seconds: float = 0.0,
    transitions: bool = True,
) -> dict[str, Any]:
    """Turn the ProductionScript into a deterministic motion plan.

    Camera text stays a hint; the style preset supplies exact policy. Local
    motion is only added where an authored region exists — there is no
    segmentation model, and no region is invented here.
    """
    from .motion.spec import LocalMotionSpec, MotionPlan, RegionSpec, ShotSpec, TransitionSpec

    if not audio_manifest.is_file():
        raise ProductionError(f"缺少 audio_manifest.json: {audio_manifest}")
    audio = json.loads(audio_manifest.read_text(encoding="utf-8"))
    if not audio.get("lines"):
        raise ProductionError("audio_manifest.json 没有 lines")
    timing = _audio_line_timing(audio_manifest, gap_ms) if align_audio else {}
    regions = _load_regions(regions_path)

    shots = []
    known_ids = set()
    for position, shot in enumerate(_shots(script), start=1):
        shot_id = _field(shot, "shot_id")
        known_ids.add(shot_id)
        image = _find_image(images_dir / shot_id)
        if image is None:
            raise ProductionError(f"{shot_id}: 没有生成图片（{images_dir / shot_id}）")
        duration = (
            _aligned_duration(shot, timing, leading_ms, first=(position == 1))
            if align_audio
            else float(_field(shot, "duration_seconds"))
        )
        transition = None
        if position > 1 and transitions:
            policy = preset.motion.transition
            transition = TransitionSpec(
                type=policy.type,
                duration_s=policy.duration_s,
                feather=policy.feather,
                direction=policy.direction,
                seed=policy.seed,
            )
        entry = regions.get(shot_id, {"regions": [], "layers": [], "model": "none"})
        from pydantic import ValidationError

        try:
            region_specs = [RegionSpec.model_validate(item) for item in entry["regions"]]
            local_motion = [LocalMotionSpec.model_validate(item) for item in entry["layers"]]
        except ValidationError as exc:
            raise ProductionError(f"{shot_id}: 区域/图层校验失败：{exc}") from exc
        static_candidates = [
            episode_root / "work" / "static" / shot_id / "static_quality.json",
            episode_root / "static" / shot_id / "static_quality.json",
        ]
        static_path = next((path for path in static_candidates if path.is_file()), None)
        if static_path is not None:
            state = json.loads(static_path.read_text(encoding="utf-8")).get("overall_status")
            if state == "FAIL":
                raise ProductionError(f"{shot_id}: 静态质量门 FAIL，先修图再做动态")
            if state not in ("PASS_STATIC", "PARTIAL"):
                raise ProductionError(f"{shot_id}: 静态质量门尚未就绪（{state}）")
        shots.append(
            ShotSpec(
                id=shot_id,
                source=_rel(image, root),
                duration_seconds=round(duration, 3),
                motion=str(_field(shot, "motion") or ""),
                local_motion=local_motion,
                regions=region_specs,
                transition_in=transition,
                static_quality=_rel(static_path, root) if static_path is not None else None,
                text={
                    "line_ids": ",".join(_field(shot, "line_ids") or []),
                    "visual_prompt": str(_field(shot, "visual_prompt") or "")[:400],
                },
            )
        )
    unknown = sorted(set(regions) - known_ids)
    if unknown:
        raise ProductionError(f"motion regions 引用了不存在的镜头：{unknown}")
    # A transition may not eat most of either neighbour. The cap is style policy
    # (``transition.max_fraction``), not a hidden constant in the renderer.
    for index in range(1, len(shots)):
        transition = shots[index].transition_in
        if transition is None:
            continue
        shortest = min(shots[index - 1].duration_seconds, shots[index].duration_seconds)
        cap = max(0.3, round(shortest * preset.motion.transition.max_fraction, 3))
        if transition.duration_s > cap:
            shots[index] = shots[index].model_copy(
                update={"transition_in": transition.model_copy(update={"duration_s": cap})}
            )
    if tail_seconds:
        if tail_seconds < 0:
            raise ProductionError("tail_seconds must be >= 0")
        last = shots[-1]
        shots[-1] = last.model_copy(
            update={"duration_seconds": round(last.duration_seconds + tail_seconds, 3)}
        )

    plan = MotionPlan(style_id=preset.id, shots=shots)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    style_config = root / "config" / "styles.yaml"
    meta = {
        "style_id": preset.id,
        "style_config": _rel(style_config, root),
        "style_config_sha256": _sha256(style_config),
        "audio_manifest": _rel(audio_manifest, root),
        "align_audio": align_audio,
        "leading_ms": leading_ms,
        "gap_ms": gap_ms,
        "tail_seconds": tail_seconds,
        "transitions": transitions,
        "total_seconds": plan.total_seconds,
        "regions_file": _rel(regions_path, root) if regions_path else None,
        "regions_model": {shot_id: item["model"] for shot_id, item in regions.items()},
    }
    (out_path.parent / "motion_plan.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "plan": _rel(out_path, root),
        "shots": len(shots),
        "total_seconds": plan.total_seconds,
        "transitions": sum(1 for shot in shots if shot.transition_in is not None),
    }


def build_segments(
    script: Any,
    *,
    root: Path,
    episode_root: Path,
    images_dir: Path,
    audio_manifest: Path,
    out_path: Path,
    clips_dir: Path | None = None,
    sequence: Path | None = None,
    align_audio: bool = False,
    leading_ms: int = 0,
    gap_ms: int = 800,
    tail_seconds: float = 0.0,
) -> dict[str, Any]:
    """Map shots to R3 segments.json; every shot must have a real clip or image.

    ``clips_dir`` switches shots to pre-rendered video segments (``<shot_id>.mp4``);
    every shot must then have a clip. ``sequence`` replaces the per-shot list with
    one already assembled motion sequence whose length must cover the narration.
    ``align_audio`` replaces the planned shot duration with the exact audio timing
    of its bound lines, so cuts land on speech boundaries instead of drifting.
    """
    if not audio_manifest.is_file():
        raise ProductionError(f"缺少 audio_manifest.json: {audio_manifest}")
    audio = json.loads(audio_manifest.read_text(encoding="utf-8"))
    if not audio.get("lines"):
        raise ProductionError("audio_manifest.json 没有 lines")
    if sequence is not None:
        if tail_seconds:
            raise ProductionError("序列模式下 tail_seconds 必须写进 motion plan")
        if clips_dir is not None:
            raise ProductionError("sequence 与 clips_dir 只能二选一")
        if not sequence.is_file():
            raise ProductionError(f"缺少动态序列：{sequence}")
        duration = _probe_duration(sequence)
        audio_seconds = leading_ms / 1000.0 + sum(
            float(line["duration_seconds"]) + int(line.get("pause_after_ms", gap_ms)) / 1000.0
            for line in audio["lines"]
        )
        if audio_seconds > duration + 0.1:
            raise ProductionError(
                f"动态序列 {duration:.3f}s 短于旁白 {audio_seconds:.3f}s；"
                "先修 plan 或音频，不能靠 r3 拉长冻结画面"
            )
        segments = [
            {
                "id": "sequence",
                "type": "video",
                "source": _rel(sequence, root),
                "duration": duration,
                "audio_seconds": round(audio_seconds, 3),
                "shots": [
                    {"id": _field(shot, "shot_id"),
                     "line_ids": _field(shot, "line_ids"),
                     "planned_duration": _field(shot, "duration_seconds")}
                    for shot in _shots(script)
                ],
                "sha256": _sha256(sequence),
            }
        ]
    else:
        timing = _audio_line_timing(audio_manifest, gap_ms) if align_audio else {}
        segments = []
        for position, shot in enumerate(_shots(script), start=1):
            shot_id = _field(shot, "shot_id")
            clip = (clips_dir / f"{shot_id}.mp4") if clips_dir is not None else None
            if clip is not None:
                if not clip.is_file():
                    raise ProductionError(f"{shot_id}: 没有生成动态片段（{clip}）")
                kind, source = "video", clip
            else:
                image = _find_image(images_dir / shot_id)
                if image is None:
                    raise ProductionError(f"{shot_id}: 没有生成图片（{images_dir / shot_id}）")
                kind, source = "image", image
            duration = _field(shot, "duration_seconds")
            if align_audio:
                duration = _aligned_duration(shot, timing, leading_ms, first=(position == 1))
            segments.append(
                {
                    "id": shot_id,
                    "type": kind,
                    "source": _rel(source, root),
                    "duration": duration,
                    "planned_duration": _field(shot, "duration_seconds"),
                    "motion": _field(shot, "motion"),
                    "line_ids": _field(shot, "line_ids"),
                    "visual_prompt": _field(shot, "visual_prompt"),
                    "sha256": _sha256(source),
                }
            )
        if tail_seconds:
            if tail_seconds < 0:
                raise ProductionError("tail_seconds must be >= 0")
            segments[-1]["duration"] = round(float(segments[-1]["duration"]) + tail_seconds, 3)
            segments[-1]["tail_seconds"] = tail_seconds
    payload = {
        "generated_at": _field(script, "generated_at"),
        "script_sha256": _sha256(episode_root / "production_script.json"),
        "audio_manifest": _rel(audio_manifest, root),
        "sequence_mode": sequence is not None,
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
    parser.add_argument("--clips", default=None, help="directory of pre-rendered <shot_id>.mp4 video segments")
    parser.add_argument("--sequence", default=None, help="assembled motion sequence (single video segment)")
    parser.add_argument("--motion-plan", action="store_true", help="write a motion plan instead of segments.json")
    parser.add_argument("--style", default=None, help="style preset id for --motion-plan")
    parser.add_argument("--regions", default=None, help="authored local-motion regions JSON")
    parser.add_argument("--no-transition", action="store_true", help="do not add the style's default transitions")
    parser.add_argument("--align-audio", action="store_true", help="derive shot durations from audio_manifest timing")
    parser.add_argument("--leading-ms", type=int, default=0, help="leading silence absorbed by the first shot")
    parser.add_argument("--gap-ms", type=int, default=800, help="trailing pause when a line has no pause_after_ms")
    parser.add_argument("--tail-seconds", type=float, default=0.0, help="hold the last shot this long after the last line")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = root / script_path

    def _path(value: str | None) -> Path | None:
        if value is None:
            return None
        path = Path(value)
        return path if path.is_absolute() else root / path

    try:
        from .script_engine import ProductionScript

        script = ProductionScript.model_validate(json.loads(script_path.read_text(encoding="utf-8")))
        if args.motion_plan:
            from .style_presets import load_style_presets

            registry = load_style_presets(root)
            style_id = args.style or script.style_id
            if style_id not in registry.ids():
                raise ProductionError(
                    f"无法从 script.style_id={style_id!r} 解析视觉预设；"
                    f"--style 必须是 {registry.ids()} 之一"
                )
            result = build_motion_plan(
                script,
                root=root,
                episode_root=script_path.parent,
                images_dir=_path(args.images),
                audio_manifest=_path(args.audio),
                out_path=_path(args.out),
                preset=registry.get(style_id),
                regions_path=_path(args.regions),
                align_audio=args.align_audio,
                leading_ms=args.leading_ms,
                gap_ms=args.gap_ms,
                tail_seconds=args.tail_seconds,
                transitions=not args.no_transition,
            )
        else:
            result = build_segments(
                script,
                root=root,
                episode_root=script_path.parent,
                images_dir=_path(args.images),
                audio_manifest=_path(args.audio),
                out_path=_path(args.out),
                clips_dir=_path(args.clips),
                sequence=_path(args.sequence),
                align_audio=args.align_audio,
                leading_ms=args.leading_ms,
                gap_ms=args.gap_ms,
                tail_seconds=args.tail_seconds,
            )
    except (ProductionError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
