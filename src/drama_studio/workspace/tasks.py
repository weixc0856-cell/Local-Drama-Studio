"""Restricted task registry and runner.

The UI can only start the fixed entries in :data:`TASK_KINDS`. Every entry
calls an existing, already-verified project script with validated arguments.
There is no generic shell, no arbitrary path and no second service port.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..config import find_project_root, load_settings
from ..style_lock import (
    StyleLockError, assert_style_request, locked_preset_id, locked_style_id,
)
from .store import WorkspaceStore, now_iso

ROOT = find_project_root()
LOG_DIR = ROOT / "logs" / "workspace" / "tasks"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
BLOCKED = "BLOCKED"


class TaskError(Exception):
    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class TaskConflict(TaskError):
    pass


class EmptyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BuildParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    content_type: str | None = Field(default=None, pattern="^(poetry|narration|mixed)$")
    leading_ms: int | None = Field(default=None, ge=0, le=5000)
    audio_timeline: str | None = Field(default=None, max_length=400)
    audio_assets: str | None = Field(default=None, max_length=400)


class ReviewParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=1000)


class ComfyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: str = Field(min_length=1, max_length=400)
    episode_id: str | None = Field(default=None, max_length=120)
    only: str | None = Field(default=None, max_length=200)
    force: bool = False
    timeout: int = Field(default=1800, ge=60, le=21600)
    confirm: bool = False


class LIParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus: str = Field(min_length=1, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    max_tokens: int = Field(default=1600, ge=256, le=8000)
    timeout: float = Field(default=900.0, ge=30, le=3600)
    confirm: bool = False


class PackageParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    corpus: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    run: str | None = Field(default=None, max_length=300)


class ScriptParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    package: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    speaker: str | None = Field(default=None, max_length=80)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    voice_profile: str | None = Field(default=None, max_length=80)
    max_tokens: int = Field(default=2000, ge=256, le=8000)
    timeout: float = Field(default=900.0, ge=30, le=3600)
    image_width: int = Field(default=576, ge=256, le=2048)
    image_height: int = Field(default=1024, ge=256, le=2048)
    reuse: bool = False
    confirm: bool = False


class VideoJobsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=400)
    keyframes: str | None = Field(default=None, max_length=400)
    out: str | None = Field(default=None, max_length=400)
    only: str | None = Field(default=None, max_length=200)
    frames: int = Field(default=73, ge=9, le=257)
    width: int = Field(default=576, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)


class SegmentsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=300)
    images: str | None = Field(default=None, max_length=300)
    audio: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    clips_dir: str | None = Field(default=None, max_length=300)
    allow_partial_clips: bool = False
    sequence: str | None = Field(default=None, max_length=300)
    align_audio: bool = False
    leading_ms: int = Field(default=0, ge=0, le=5000)
    gap_ms: int = Field(default=800, ge=0, le=5000)
    tail_seconds: float = Field(default=0.0, ge=0.0, le=10.0)


class QualityParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    manifest: str | None = Field(default=None, max_length=400)
    motion_manifest: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def _one_manifest(self) -> "QualityParams":
        if self.manifest and self.motion_manifest:
            raise ValueError("manifest 与 motion_manifest 只能二选一")
        return self


class TTSParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    speaker: str | None = Field(default=None, max_length=80)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    mode: str | None = Field(default=None, max_length=40)
    tts_mode: Literal["sft", "zero_shot"] | None = Field(default=None)
    voice_profile: str | None = Field(default=None, max_length=80)
    voices: str | None = Field(default=None, max_length=400)
    voice_cast: str | None = Field(default=None, max_length=400)
    allow_unapproved_voices: bool = False
    base_url: str | None = Field(default=None, max_length=300)
    force: bool = False
    timeout: float = Field(default=300.0, ge=30, le=3600)
    confirm: bool = False


class MotionPlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=300)
    images: str | None = Field(default=None, max_length=300)
    audio: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    style: str | None = Field(default=None, max_length=80, description="style preset id")
    regions: str | None = Field(default=None, max_length=300)
    align_audio: bool = True
    leading_ms: int = Field(default=0, ge=0, le=5000)
    gap_ms: int = Field(default=800, ge=0, le=5000)
    tail_seconds: float = Field(default=0.0, ge=0.0, le=10.0)
    transitions: bool = True
    skip_static_gate: bool = False


class StaticCheckParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    shot_id: str = Field(pattern=r"^shot_\d{3}$")
    style: str | None = Field(default=None, max_length=80)
    image: str | None = Field(default=None, max_length=400)
    manual: str | None = Field(default=None, max_length=400)
    aesthetic: str | None = Field(default=None, max_length=400)
    out: str | None = Field(default=None, max_length=400)


class StyleConsistencyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    style: str | None = Field(default=None, max_length=80)
    review: str | None = Field(default=None, max_length=400)
    out: str | None = Field(default=None, max_length=400)


class StoryCheckParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=400)
    characters: str | None = Field(default=None, max_length=400)
    shots: str | None = Field(default=None, max_length=400)
    voices: str | None = Field(default=None, max_length=400)
    allow_unapproved_voices: bool = False
    out: str | None = Field(default=None, max_length=400)


class AudioQAParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    manifest: str | None = Field(default=None, max_length=400)
    timeline: str | None = Field(default=None, max_length=400)
    audio_timeline: str | None = Field(default=None, max_length=400)
    audio_assets: str | None = Field(default=None, max_length=400)


class AestheticPlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=300)
    style: str | None = Field(default=None, max_length=80)
    designs: str | None = Field(default=None, max_length=300)
    axes: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    snapshot_root: str | None = Field(default=None, max_length=300)
    seed_base: int = Field(default=8100, ge=0, le=999999)
    width: int = Field(default=576, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    steps: int = Field(default=4, ge=1, le=50)
    cfg: float = Field(default=1.0, ge=0.0, le=20.0)


class AestheticCompareParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    plan: str | None = Field(default=None, max_length=300)
    images: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)


class AestheticReviewParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    report: str | None = Field(default=None, max_length=300)
    decision: Literal["PASS", "REVISE", "REJECT"]
    note: str = Field(default="", max_length=1000)
    shot_id: str | None = Field(default=None, max_length=40)
    variant: Literal["A", "B"] | None = None


class MotionRenderParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    plan: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)
    sequence: bool = True
    quality: bool = True
    confirm: bool = False


class ServiceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False


@dataclass(frozen=True)
class TaskKind:
    key: str
    label: str
    description: str
    cost: str
    safety: str
    params_model: type[BaseModel]
    lock_key: Callable[[BaseModel], str]
    build_argv: Callable[[BaseModel, str], list[str]]
    handler: Callable[[BaseModel, str, WorkspaceStore], dict[str, Any]] | None = None
    prerequisites: Callable[[BaseModel, WorkspaceStore], list[str]] = field(
        default=lambda params, store: []
    )
    after_success: Callable[[BaseModel, str, WorkspaceStore], dict[str, Any]] | None = None
    danger: bool = False
    enabled: bool = True
    blocked_reason: str | None = None

    def spec(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "cost": self.cost,
            "safety": self.safety,
            "danger": self.danger,
            "enabled": self.enabled,
            "blocked_reason": self.blocked_reason,
            "params_schema": self.params_model.model_json_schema(),
        }


def _locked_style(episode: dict[str, Any] | None, requested: str | None = None) -> str | None:
    try:
        return assert_style_request(episode, requested)
    except StyleLockError as exc:
        raise TaskError("style_locked", str(exc)) from exc


def _resolve_under(raw: str, allowed: tuple[str, ...], *, must_exist: bool = True) -> Path:
    path = (ROOT / raw).resolve()
    if not any(path == (ROOT / name).resolve() or path.is_relative_to((ROOT / name).resolve()) for name in allowed):
        raise TaskError("forbidden_path", f"路径必须位于 {', '.join(allowed)} 之下")
    if must_exist and not path.exists():
        raise TaskError("not_found", f"路径不存在：{raw}")
    return path


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------- handlers


def _build_episode_dir(episode_id: str, store: WorkspaceStore) -> tuple[Path, str]:
    episode = store.get_episode(episode_id)
    if not episode:
        raise TaskError("unknown_episode", f"期数不存在：{episode_id}")
    if episode.get("track") != "video":
        raise TaskError("unsupported_track", "只有 video 期数可以执行合成任务")
    art_root = episode.get("artifact_root")
    if not art_root:
        raise TaskError("no_artifact_root", "该期未绑定产物目录")
    return ROOT / art_root, episode_id


def _build_prereqs(params: BuildParams, store: WorkspaceStore) -> list[str]:
    missing: list[str] = []
    try:
        art_root, _ = _build_episode_dir(params.episode_id, store)
    except TaskError as exc:
        return [exc.message]
    segments = art_root / "segments.json"
    audio = art_root / "audio_manifest.json"
    if not segments.is_file():
        missing.append(f"缺少 {_rel(segments)}")
    if not audio.is_file():
        missing.append(f"缺少 {_rel(audio)}")
    if segments.is_file():
        try:
            data = json.loads(segments.read_text(encoding="utf-8"))
            for seg in data if isinstance(data, list) else []:
                source = seg.get("source")
                if source and not (ROOT / source).is_file():
                    missing.append(f"分段 {seg.get('id')} 的素材不存在：{source}")
        except (OSError, json.JSONDecodeError) as exc:
            missing.append(f"segments.json 无法解析：{exc}")
    if audio.is_file():
        try:
            data = json.loads(audio.read_text(encoding="utf-8"))
            for line in data.get("lines", []) if isinstance(data, dict) else []:
                if line.get("file") and not (ROOT / line["file"]).is_file():
                    missing.append(f"音频行 {line.get('index')} 不存在：{line['file']}")
        except (OSError, json.JSONDecodeError) as exc:
            missing.append(f"audio_manifest.json 无法解析：{exc}")
    if params.audio_timeline:
        path = (ROOT / params.audio_timeline).resolve()
        if not path.is_file():
            missing.append(f"缺少 audio_timeline：{params.audio_timeline}")
    if params.audio_assets:
        path = (ROOT / params.audio_assets).resolve()
        if not path.is_file():
            missing.append(f"缺少 audio_assets：{params.audio_assets}")
    return missing


def _build_argv(params: BuildParams, task_id: str) -> list[str]:
    _, episode_id = _build_episode_dir(params.episode_id, _STORE_REF[0])
    episode = _STORE_REF[0].get_episode(episode_id) or {}
    art_root = ROOT / str(episode["artifact_root"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "projects" / str(episode["project_id"]) / "episodes" / episode_id / "renders" / f"build-{stamp}"
    if out_dir.exists():
        raise TaskError("output_exists", f"构建目录已存在，拒绝覆盖：{_rel(out_dir)}")
    argv = [
        sys.executable,
        "scripts/r3_build.py",
        "--segments",
        _rel(art_root / "segments.json"),
        "--audio",
        _rel(art_root / "audio_manifest.json"),
        "--out",
        _rel(out_dir),
    ]
    if params.content_type:
        argv += ["--content-type", params.content_type]
    if params.leading_ms is not None:
        argv += ["--leading-ms", str(params.leading_ms)]
    if params.audio_timeline:
        argv += ["--audio-timeline", params.audio_timeline]
    if params.audio_assets:
        argv += ["--audio-assets", params.audio_assets]
    return argv


def _sha_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_after(params: BuildParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    episode = store.get_episode(params.episode_id) or {}
    # The newest workspace build directory is the one just produced.
    base = ROOT / "projects" / str(episode.get("project_id")) / "episodes" / params.episode_id / "renders"
    candidates = sorted(base.glob("build-*/build_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise TaskError("missing_manifest", "构建命令成功，但没有找到 build_manifest.json")
    manifest_path = candidates[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = manifest.get("outputs") or {}
    final_rel = outputs.get("final")
    if not final_rel:
        raise TaskError("missing_output", "manifest 中没有 final 输出")
    final_path = ROOT / final_rel
    if not final_path.is_file():
        raise TaskError("missing_output", f"manifest 记录的成片不存在：{final_rel}")
    actual = _sha_file(final_path)
    if outputs.get("final_sha256") and actual != outputs["final_sha256"]:
        raise TaskError("hash_mismatch", "成片哈希与 manifest 不一致")
    store.touch_episode(params.episode_id)
    return {
        "build_dir": _rel(manifest_path.parent),
        "manifest": _rel(manifest_path),
        "final": final_rel,
        "final_sha256": actual,
        "total_seconds": manifest.get("total_seconds"),
        "font": (manifest.get("font") or {}).get("postscript_name"),
        "decode_returncode": manifest.get("decode_returncode"),
    }


def _comfy_prereqs(params: ComfyParams, store: WorkspaceStore) -> list[str]:
    missing: list[str] = []
    try:
        _resolve_under(params.jobs, ("experiments", "projects"))
    except TaskError as exc:
        return [exc.message]
    if params.episode_id:
        episode = store.get_episode(params.episode_id)
        if not episode:
            return [f"期数不存在：{params.episode_id}"]
        try:
            base = _episode_root(params.episode_id, store)
        except TaskError as exc:
            return [exc.message]
        locked = locked_style_id(episode)
        script = next((p for p in (base / "work" / "production_script.json",
                                   base / "production_script.json") if p.is_file()), None)
        if script is not None and locked:
            try:
                script_style = json.loads(script.read_text(encoding="utf-8")).get("style_id")
            except (OSError, json.JSONDecodeError):
                script_style = None
            if script_style and script_style != locked:
                missing.append(
                    f"production_script style_id={script_style!r} 与期数锁 {locked!r} 不一致")
    if not _port_open("127.0.0.1", 8188):
        missing.append("ComfyUI 8188 未监听；先用 service.comfy.start 启动")
    return missing


def _comfy_after(params: ComfyParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    jobs_path = _resolve_under(params.jobs, ("experiments", "projects"))
    manifest_path = jobs_path.parent / f"{jobs_path.stem}_manifest.json"
    if manifest_path.is_file():
        return {"manifest": _rel(manifest_path), "summary": json.loads(manifest_path.read_text(encoding="utf-8")).get("counts")}
    return {"manifest": None}


def _li_prereqs(params: LIParams, store: WorkspaceStore) -> list[str]:
    try:
        corpus = _resolve_under(params.corpus, ("literary_intelligence",))
    except TaskError as exc:
        return [exc.message]
    missing = []
    for name in ("source_registry.json", "claims.json"):
        if not (corpus / name).is_file():
            missing.append(f"缺少 {_rel(corpus / name)}")
    return missing


def _li_argv(params: LIParams, task_id: str) -> list[str]:
    corpus = _resolve_under(params.corpus, ("literary_intelligence",))
    if params.out:
        out = _resolve_under(params.out, ("literary_intelligence",), must_exist=False)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out = ROOT / "literary_intelligence" / "runs" / f"workspace-{stamp}-{task_id[-6:]}"
    if out.exists() and any(out.iterdir()):
        raise TaskError("output_exists", f"输出目录非空，拒绝覆盖：{_rel(out)}")
    return [
        sys.executable,
        "-m",
        "literary_intelligence.run_li15",
        "--corpus",
        _rel(corpus),
        "--out",
        _rel(out),
        "--max-tokens",
        str(params.max_tokens),
        "--timeout",
        str(params.timeout),
    ]


def _li_after(params: LIParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    if params.out:
        runs = [ROOT / params.out]
    else:
        runs = sorted(
            (ROOT / "literary_intelligence" / "runs").glob("workspace-*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    for run in runs:
        manifest = run / "real_pipeline.json"
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return {
                "run_dir": _rel(run),
                "all_evidence_valid": data.get("all_evidence_valid"),
                "human_review": data.get("human_review"),
                "passes": [
                    {"pass_name": p.get("pass_name"), "status": p.get("status")}
                    for p in data.get("passes") or []
                ],
            }
    return {}


def _doctor_after(params: EmptyParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    task = store.get_task(task_id) or {}
    path = ROOT / (task.get("log_path") or "")
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    start = text.find("{")
    while start != -1:
        try:
            data = json.loads(text[start:])
            return {"summary": data.get("summary"), "report": data.get("report")}
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    return {}


def _service_argv(params: ServiceParams, task_id: str) -> list[str]:
    if not params.confirm:
        raise TaskError("confirmation_required", "服务启停需要 confirm=true")
    raise TaskError("not_implemented", "service argv is bound per kind")


def _review_dir(params: ReviewParams, store: WorkspaceStore) -> Path:
    episode = store.get_episode(params.episode_id)
    if not episode:
        raise TaskError("unknown_episode", f"期数不存在：{params.episode_id}")
    art_root = episode.get("artifact_root")
    if not art_root:
        raise TaskError("no_artifact_root", "该期未绑定产物目录")
    base = (store.root / art_root).resolve()
    try:
        base.relative_to(store.root.resolve())
    except ValueError as exc:
        raise TaskError("forbidden_path", "产物目录必须位于项目根目录内") from exc
    if not base.is_dir():
        raise TaskError("not_found", f"产物目录不存在：{art_root}")
    return store.root / "projects" / str(episode["project_id"]) / "episodes" / params.episode_id


def _review_target(params: ReviewParams, store: WorkspaceStore) -> Path:
    return _review_dir(params, store) / "human_review.json"


def _review_prereqs(params: ReviewParams, store: WorkspaceStore) -> list[str]:
    try:
        _review_target(params, store)
    except TaskError as exc:
        return [exc.message]
    return []


def _review_handler(decision: str) -> Callable[[BaseModel, str, WorkspaceStore], dict[str, Any]]:
    def handler(params: BaseModel, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
        assert isinstance(params, ReviewParams)
        target = _review_target(params, store)
        target.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "episode_id": params.episode_id,
            "decision": decision,
            "note": params.note,
            "task_id": task_id,
            "created_at": now_iso(),
        }
        path = target
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        try:
            rel_path = path.relative_to(store.root).as_posix()
        except ValueError:
            rel_path = str(path)
        return {"review": rel_path, "decision": decision}

    return handler


def _tts_paths(params: TTSParams, store: WorkspaceStore) -> tuple[Path, Path, Path, Path]:
    episode = store.get_episode(params.episode_id)
    if not episode:
        raise TaskError("unknown_episode", f"期数不存在：{params.episode_id}")
    art_root = episode.get("artifact_root")
    if not art_root:
        raise TaskError("no_artifact_root", "该期未绑定产物目录")
    base = (store.root / art_root).resolve()
    try:
        base.relative_to(store.root.resolve())
    except ValueError as exc:
        raise TaskError("forbidden_path", "产物目录必须位于项目根目录内") from exc
    if not base.is_dir():
        raise TaskError("not_found", f"产物目录不存在：{art_root}")
    narration = base / "narration.json"
    if not narration.is_file():
        raise TaskError("not_found", f"缺少 {_rel(narration)}")
    return narration, base / "audio", base / "audio_manifest.json", base


def _tts_prereqs(params: TTSParams, store: WorkspaceStore) -> list[str]:
    try:
        _tts_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    return []


def _tts_argv(params: TTSParams, task_id: str) -> list[str]:
    narration, out_dir, manifest, _ = _tts_paths(params, _STORE_REF[0])
    argv = [
        sys.executable,
        "scripts/r3_tts.py",
        "--narration", _rel(narration),
        "--out", _rel(out_dir),
        "--manifest", _rel(manifest),
        "--timeout", str(params.timeout),
    ]
    if params.speaker:
        argv += ["--speaker", params.speaker]
    if params.speed is not None:
        argv += ["--speed", str(params.speed)]
    if params.mode:
        argv += ["--mode", params.mode]
    if params.tts_mode:
        argv += ["--tts-mode", params.tts_mode]
    if params.voice_profile:
        argv += ["--voice-profile", params.voice_profile]
    if params.voices:
        argv += ["--voices", _rel((_STORE_REF[0].root / params.voices).resolve())]
    if params.voice_cast:
        argv += ["--voice-cast", _rel((_STORE_REF[0].root / params.voice_cast).resolve())]
    if params.allow_unapproved_voices:
        argv += ["--allow-unapproved-voices"]
    if params.base_url:
        argv += ["--base-url", params.base_url]
    if params.force:
        argv += ["--force"]
    return argv


def _tts_after(params: TTSParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, manifest_path, _ = _tts_paths(params, store)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for line in data.get("lines") or []:
        path = (store.root / line["file"]).resolve()
        if not path.is_file() or _sha_file(path) != line.get("sha256"):
            raise TaskError("tts_manifest_mismatch", f"音频哈希不一致：{line.get('file')}")
    return {
        "manifest": _rel(manifest_path),
        "tts_mode": data.get("tts_mode"),
        "model_class": data.get("model_class"),
        "model_dir": data.get("model_dir"),
        "speaker": data.get("speaker"),
        "speaker_id": data.get("speaker_id"),
        "voice_cast": data.get("voice_cast"),
        "lines": len(data.get("lines") or []),
        "total_seconds": round(sum(float(x.get("duration_seconds") or 0) for x in data.get("lines") or []), 3),
    }


def _style_consistency_paths(
    params: StyleConsistencyParams, store: WorkspaceStore
) -> tuple[str, list[tuple[str, Path]], Path | None, Path]:
    base = _episode_root(params.episode_id, store)
    episode = store.get_episode(params.episode_id) or {}
    style = _locked_style(episode, params.style)
    if not style:
        raise TaskError("no_style", "该期未绑定风格或未映射 preset_id")
    images_root = base / "assets" / "images"
    shots: list[tuple[str, Path]] = []
    if images_root.is_dir():
        for directory in sorted(images_root.iterdir()):
            if not directory.is_dir():
                continue
            files = sorted(p for p in directory.glob("*")
                           if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
            if files:
                shots.append((directory.name, files[0]))
    review = (store.root / params.review).resolve() if params.review else None
    out = (store.root / params.out).resolve() if params.out else base / "style_consistency_report.json"
    return style, shots, review, out


def _style_consistency_prereqs(params: StyleConsistencyParams, store: WorkspaceStore) -> list[str]:
    try:
        _, shots, review, _ = _style_consistency_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    if len(shots) < 2:
        missing.append("至少需要 2 个镜头的静态图（assets/images/<shot_id>/）")
    if review is not None and not review.is_file():
        missing.append(f"缺少人工审片 JSON：{_rel(review)}")
    return missing


def _style_consistency_argv(params: StyleConsistencyParams, task_id: str) -> list[str]:
    style, shots, review, out = _style_consistency_paths(params, _STORE_REF[0])
    argv = [sys.executable, "-m", "drama_studio.style_consistency", "--style", style, "--out", _rel(out)]
    for shot_id, path in shots:
        argv += ["--shot", f"{shot_id}={_rel(path)}"]
    if review is not None:
        argv += ["--review", _rel(review)]
    return argv


def _style_consistency_after(
    params: StyleConsistencyParams, task_id: str, store: WorkspaceStore
) -> dict[str, Any]:
    _, _, _, out = _style_consistency_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {
        "report": _rel(out),
        "style_id": data.get("style_id"),
        "technical_status": data.get("technical_status"),
        "aesthetic_status": data.get("aesthetic_status"),
        "overall_status": data.get("overall_status"),
        "shots": data.get("shot_count"),
        "flags": data.get("flags") or [],
    }


def _static_paths(
    params: StaticCheckParams, store: WorkspaceStore
) -> tuple[Path, str, Path, Path | None, Path | None]:
    base = _episode_root(params.episode_id, store)
    image = (store.root / params.image).resolve() if params.image else None
    if image is None:
        directory = base / "assets" / "images" / params.shot_id
        candidates = sorted(p for p in directory.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")) if directory.is_dir() else []
        if not candidates:
            raise TaskError("not_found", f"缺少 {_rel(directory)} 下的静态图")
        image = candidates[0]
    episode = store.get_episode(params.episode_id) or {}
    style = _locked_style(episode, params.style) or (episode.get("style_snapshot") or {}).get("id")
    if not style:
        raise TaskError("no_style", "该期未绑定风格；static.check 需要 style")
    out = (store.root / params.out).resolve() if params.out else base / "work" / "static" / params.shot_id / "static_quality.json"
    manual = (store.root / params.manual).resolve() if params.manual else None
    aesthetic = (store.root / params.aesthetic).resolve() if params.aesthetic else None
    return image, str(style), out, manual, aesthetic


def _static_prereqs(params: StaticCheckParams, store: WorkspaceStore) -> list[str]:
    try:
        image, _, _, manual, aesthetic = _static_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = [] if image.is_file() else [f"缺少 {_rel(image)}"]
    if manual is not None and not manual.is_file():
        missing.append(f"缺少 {_rel(manual)}")
    if aesthetic is not None and not aesthetic.is_file():
        missing.append(f"缺少 {_rel(aesthetic)}")
    return missing


def _static_argv(params: StaticCheckParams, task_id: str) -> list[str]:
    image, style, out, manual, aesthetic = _static_paths(params, _STORE_REF[0])
    argv = [
        sys.executable, "scripts/static_quality.py",
        "--image", _rel(image), "--style", style, "--out", _rel(out),
    ]
    if manual is not None:
        argv += ["--manual", _rel(manual)]
    if aesthetic is not None:
        argv += ["--aesthetic", _rel(aesthetic)]
    return argv


def _static_after(params: StaticCheckParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, out, _, _ = _static_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {
        "report": _rel(out),
        "shot_id": params.shot_id,
        "overall_status": data.get("overall_status"),
        "objective_passed": data.get("objective_passed"),
        "aesthetic_status": data.get("aesthetic_status"),
    }


def _story_paths(
    params: StoryCheckParams, store: WorkspaceStore
) -> tuple[Path, Path, Path, Path | None, Path]:
    base = _episode_root(params.episode_id, store)
    script = (store.root / params.script).resolve() if params.script else base / "production_script.json"
    characters = ((store.root / params.characters).resolve()
                  if params.characters else base / "character_bible.yaml")
    shots = (store.root / params.shots).resolve() if params.shots else base / "shot_bible.yaml"
    voices = (store.root / params.voices).resolve() if params.voices else None
    out = (store.root / params.out).resolve() if params.out else base / "story_bible_report.json"
    return script, characters, shots, voices, out


def _story_prereqs(params: StoryCheckParams, store: WorkspaceStore) -> list[str]:
    try:
        script, characters, shots, voices, _ = _story_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    for label, path in (("production_script", script),
                        ("character_bible", characters),
                        ("shot_bible", shots)):
        if not path.is_file():
            missing.append(f"缺少 {_rel(path)}")
    if voices is not None and not voices.is_file():
        missing.append(f"缺少 voice library {_rel(voices)}")
    return missing


def _story_argv(params: StoryCheckParams, task_id: str) -> list[str]:
    script, characters, shots, voices, out = _story_paths(params, _STORE_REF[0])
    argv = [
        sys.executable, "-m", "drama_studio.bible",
        "--script", _rel(script),
        "--characters", _rel(characters),
        "--shots", _rel(shots),
        "--out", _rel(out),
    ]
    if voices is not None:
        argv += ["--voices", _rel(voices)]
    if params.allow_unapproved_voices:
        argv += ["--allow-unapproved-voices"]
    return argv


def _story_after(params: StoryCheckParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, _, _, out = _story_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    if data.get("status") != "PASS":
        raise TaskError("story_check_failed", "故事圣经检查未通过；见报告")
    return {
        "report": _rel(out),
        "status": data.get("status"),
        "characters": data.get("characters"),
        "shots": data.get("shots"),
        "voice_check": data.get("voice_check", {}).get("status"),
        "errors": data.get("errors") or [],
        "warnings": data.get("warnings") or [],
        "same_face_guarantee": False,
    }


def _episode_root(episode_id: str, store: WorkspaceStore) -> Path:
    episode = store.get_episode(episode_id)
    if not episode:
        raise TaskError("unknown_episode", f"期数不存在：{episode_id}")
    art_root = episode.get("artifact_root")
    if not art_root:
        raise TaskError("no_artifact_root", "该期未绑定产物目录")
    base = (store.root / art_root).resolve()
    try:
        base.relative_to(store.root.resolve())
    except ValueError as exc:
        raise TaskError("forbidden_path", "产物目录必须位于项目根目录内") from exc
    if not base.is_dir():
        raise TaskError("not_found", f"产物目录不存在：{art_root}")
    return base


def _package_paths(params: PackageParams, store: WorkspaceStore) -> tuple[Path, Path]:
    base = _episode_root(params.episode_id, store)
    corpus = (store.root / params.corpus).resolve() if params.corpus else (base / "source")
    if not corpus.is_dir():
        corpus = base
    out = (store.root / params.out).resolve() if params.out else base / "content_package.json"
    return corpus, out


def _package_prereqs(params: PackageParams, store: WorkspaceStore) -> list[str]:
    try:
        corpus, _ = _package_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    for name in ("source_registry.json", "claims.json"):
        if not (corpus / name).is_file():
            missing.append(f"缺少 {_rel(corpus / name)}")
    return missing


def _package_argv(params: PackageParams, task_id: str) -> list[str]:
    corpus, out = _package_paths(params, _STORE_REF[0])
    argv = [sys.executable, "-m", "drama_studio.content_package", "--corpus", _rel(corpus), "--out", _rel(out)]
    if params.run:
        argv += ["--run", params.run]
    return argv


def _package_after(params: PackageParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, out = _package_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {
        "package": _rel(out),
        "work": (data.get("work") or {}).get("title"),
        "scenes": len((data.get("video") or {}).get("scene_plan") or []),
        "warnings": len((data.get("provenance") or {}).get("warnings") or []),
    }


def _script_paths(params: ScriptParams, store: WorkspaceStore) -> tuple[Path, Path, Path]:
    base = _episode_root(params.episode_id, store)
    package = (store.root / params.package).resolve() if params.package else base / "content_package.json"
    out = (store.root / params.out).resolve() if params.out else base / "production_script.json"
    return package, out, base / "style_snapshot.json"


def _script_prereqs(params: ScriptParams, store: WorkspaceStore) -> list[str]:
    try:
        package, _, _ = _script_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    if not package.is_file():
        missing.append(f"缺少 {_rel(package)}")
    episode = store.get_episode(params.episode_id) or {}
    if not episode.get("style_snapshot"):
        missing.append("该期未绑定风格；script.generate 需要 style_snapshot")
    return missing


def _script_argv(params: ScriptParams, task_id: str) -> list[str]:
    package, out, style_path = _script_paths(params, _STORE_REF[0])
    episode = _STORE_REF[0].get_episode(params.episode_id) or {}
    style = episode.get("style_snapshot") or {}
    if not style:
        raise TaskError("no_style", "该期未绑定风格")
    style_path.parent.mkdir(parents=True, exist_ok=True)
    style_path.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    settings = load_settings(_STORE_REF[0].root)
    argv = [
        sys.executable, "-m", "drama_studio.script_engine",
        "--package", _rel(package),
        "--style", _rel(style_path),
        "--out", _rel(out),
        "--base-url", settings.llm.base_url,
        "--model", settings.llm.model,
        "--api-key", settings.llm.api_key,
        "--timeout", str(params.timeout),
        "--max-tokens", str(params.max_tokens),
    ]
    if params.speaker:
        argv += ["--speaker", params.speaker]
    if params.speed is not None:
        argv += ["--speed", str(params.speed)]
    if params.voice_profile:
        argv += ["--voice-profile", params.voice_profile]
    if params.reuse:
        argv += ["--reuse"]
    return argv


def _script_after(params: ScriptParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    from ..production import build_jobs

    _, out, style_path = _script_paths(params, store)
    script = json.loads(out.read_text(encoding="utf-8"))
    base = _episode_root(params.episode_id, store)
    result = build_jobs(
        script,
        root=store.root,
        episode_root=base,
        jobs_path=base / "comfy" / "jobs.json",
        width=params.image_width,
        height=params.image_height,
    )
    result.update({"script": _rel(out), "style": _rel(style_path), "shots": len(script.get("shots") or [])})
    return result


def _video_jobs_paths(
    params: VideoJobsParams, store: WorkspaceStore
) -> tuple[Path, Path, Path, Path]:
    base = _episode_root(params.episode_id, store)
    script = (store.root / params.script).resolve() if params.script else base / "production_script.json"
    if not script.is_file():
        script = base / "work" / "production_script.json"
    keyframes = (store.root / params.keyframes).resolve() if params.keyframes else base / "assets" / "images"
    out = (store.root / params.out).resolve() if params.out else base / "comfy" / "jobs_video.json"
    return script, keyframes, out, base


def _video_jobs_prereqs(params: VideoJobsParams, store: WorkspaceStore) -> list[str]:
    try:
        script, keyframes, _, _ = _video_jobs_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = [] if script.is_file() else [f"缺少 {_rel(script)}"]
    if not keyframes.is_dir():
        missing.append(f"缺少关键帧目录 {_rel(keyframes)}")
    return missing


def _video_jobs_argv(params: VideoJobsParams, task_id: str) -> list[str]:
    script, keyframes, out, _ = _video_jobs_paths(params, _STORE_REF[0])
    argv = [
        sys.executable, "scripts/video_jobs.py",
        "--script", _rel(script), "--keyframes", _rel(keyframes), "--out", _rel(out),
        "--frames", str(params.frames), "--width", str(params.width), "--height", str(params.height),
    ]
    if params.only:
        argv += ["--only", params.only]
    return argv


def _video_jobs_after(params: VideoJobsParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, out, _ = _video_jobs_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"jobs": _rel(out), "count": len(data), "frames": params.frames}


def _segments_paths(
params: SegmentsParams, store: WorkspaceStore) -> tuple[Path, Path, Path, Path]:
    base = _episode_root(params.episode_id, store)
    script = (store.root / params.script).resolve() if params.script else base / "production_script.json"
    images = (store.root / params.images).resolve() if params.images else base / "assets" / "images"
    audio = (store.root / params.audio).resolve() if params.audio else base / "audio_manifest.json"
    out = (store.root / params.out).resolve() if params.out else base / "segments.json"
    return script, images, audio, out


def _segments_prereqs(params: SegmentsParams, store: WorkspaceStore) -> list[str]:
    try:
        script, images, audio, _ = _segments_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    if not script.is_file():
        missing.append(f"缺少 {_rel(script)}")
    if not images.is_dir():
        missing.append(f"缺少图片目录 {_rel(images)}")
    if not audio.is_file():
        missing.append(f"缺少 {_rel(audio)}")
    if params.clips_dir:
        clips = (store.root / params.clips_dir).resolve()
        if not clips.is_dir():
            missing.append(f"缺少动态片段目录 {_rel(clips)}")
    if params.sequence:
        sequence = (store.root / params.sequence).resolve()
        if not sequence.is_file():
            missing.append(f"缺少动态序列 {_rel(sequence)}")
    return missing


def _segments_argv(params: SegmentsParams, task_id: str) -> list[str]:
    script, images, audio, out = _segments_paths(params, _STORE_REF[0])
    argv = [
        sys.executable, "-m", "drama_studio.production",
        "--script", _rel(script),
        "--images", _rel(images),
        "--audio", _rel(audio),
        "--out", _rel(out),
    ]
    if params.clips_dir:
        argv += ["--clips", _rel((_STORE_REF[0].root / params.clips_dir).resolve())]
        if params.allow_partial_clips:
            argv += ["--allow-partial-clips"]
    if params.sequence:
        argv += ["--sequence", _rel((_STORE_REF[0].root / params.sequence).resolve())]
    argv += ["--leading-ms", str(params.leading_ms), "--gap-ms", str(params.gap_ms)]
    if params.align_audio:
        argv += ["--align-audio"]
        if params.tail_seconds:
            argv += ["--tail-seconds", str(params.tail_seconds)]
    return argv


def _segments_after(params: SegmentsParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, _, out = _segments_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"segments": _rel(out), "count": len(data)}


def _quality_paths(params: QualityParams, store: WorkspaceStore) -> Path:
    if params.motion_manifest:
        return (store.root / params.motion_manifest).resolve()
    if params.manifest:
        return (store.root / params.manifest).resolve()
    _episode_root(params.episode_id, store)
    episode = store.get_episode(params.episode_id) or {}
    renders = store.root / "projects" / str(episode["project_id"]) / "episodes" / params.episode_id / "renders"
    candidates = sorted(renders.glob("*/build_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise TaskError("not_found", "没有可检查的 build_manifest.json")
    return candidates[0]


def _quality_prereqs(params: QualityParams, store: WorkspaceStore) -> list[str]:
    try:
        path = _quality_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    return [] if path.is_file() else [f"缺少 {_rel(path)}"]


def _quality_argv(params: QualityParams, task_id: str) -> list[str]:
    path = _quality_paths(params, _STORE_REF[0])
    flag = "--motion-manifest" if params.motion_manifest else "--manifest"
    return [sys.executable, "-m", "drama_studio.quality", flag, _rel(path), "--root", "."]


def _quality_after(params: QualityParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    path = _quality_paths(params, store)
    name = "motion_quality_report.json" if params.motion_manifest else "quality_report.json"
    report = path.parent / name
    data = json.loads(report.read_text(encoding="utf-8"))
    return {
        "report": _rel(report),
        "status": data.get("status"),
        "code": data.get("code"),
        "final": (data.get("final") or {}).get("status"),
        "temporal": (data.get("temporal") or {}).get("status"),
    }


def _motion_plan_paths(params: MotionPlanParams, store: WorkspaceStore) -> tuple[Path, Path, Path, Path, Path | None]:
    base = _episode_root(params.episode_id, store)

    def pick(value: str | None, default: Path) -> Path:
        return (store.root / value).resolve() if value else default

    script = pick(params.script, base / "production_script.json")
    images = pick(params.images, base / "assets" / "images")
    audio = pick(params.audio, base / "audio_manifest.json")
    out = pick(params.out, base / "motion_shots.json")
    if params.regions:
        regions: Path | None = (store.root / params.regions).resolve()
    else:
        candidate = base / "motion_regions.json"
        regions = candidate if candidate.is_file() else None
    return script, images, audio, out, regions


def _motion_plan_prereqs(params: MotionPlanParams, store: WorkspaceStore) -> list[str]:
    try:
        script, images, audio, _, regions = _motion_plan_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = []
    if not script.is_file():
        missing.append(f"缺少 {_rel(script)}")
    if not images.is_dir():
        missing.append(f"缺少图片目录 {_rel(images)}")
    if not audio.is_file():
        missing.append(f"缺少 {_rel(audio)}")
    if regions is not None and not regions.is_file():
        missing.append(f"缺少 {_rel(regions)}")
    return missing


def _motion_plan_argv(params: MotionPlanParams, task_id: str) -> list[str]:
    store = _STORE_REF[0]
    script, images, audio, out, regions = _motion_plan_paths(params, store)
    episode = store.get_episode(params.episode_id) or {}
    style = _locked_style(episode, params.style)
    argv = [
        sys.executable, "-m", "drama_studio.production", "--motion-plan",
        "--script", _rel(script), "--images", _rel(images), "--audio", _rel(audio),
        "--out", _rel(out),
    ]
    if style:
        argv += ["--style", style]
    if regions is not None:
        argv += ["--regions", _rel(regions)]
    argv += ["--leading-ms", str(params.leading_ms), "--gap-ms", str(params.gap_ms)]
    if params.align_audio:
        argv += ["--align-audio"]
        if params.tail_seconds:
            argv += ["--tail-seconds", str(params.tail_seconds)]
    if not params.transitions:
        argv += ["--no-transition"]
    if params.skip_static_gate:
        argv += ["--skip-static-gate"]
    return argv


def _motion_plan_after(params: MotionPlanParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, _, out, _ = _motion_plan_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    episode = store.get_episode(params.episode_id)
    locked = locked_preset_id(episode) or locked_style_id(episode)
    if locked and data.get("style_id") != locked:
        raise TaskError("style_locked", f"motion plan style {data.get('style_id')!r} != locked {locked!r}")
    shots = data.get("shots") or []
    return {
        "plan": _rel(out),
        "style_id": data.get("style_id"),
        "shots": len(shots),
        "transitions": sum(1 for shot in shots if shot.get("transition_in")),
        "total_seconds": round(sum(float(shot.get("duration_seconds") or 0) for shot in shots), 3),
    }


def _motion_render_paths(params: MotionRenderParams, store: WorkspaceStore) -> tuple[Path, Path]:
    base = _episode_root(params.episode_id, store)
    plan = (store.root / params.plan).resolve() if params.plan else base / "motion_shots.json"
    out = (store.root / params.out).resolve() if params.out else base / "motion"
    return plan, out


def _motion_render_prereqs(params: MotionRenderParams, store: WorkspaceStore) -> list[str]:
    try:
        plan, _ = _motion_render_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    return [] if plan.is_file() else [f"缺少 {_rel(plan)}"]


def _motion_render_argv(params: MotionRenderParams, task_id: str) -> list[str]:
    plan, out = _motion_render_paths(params, _STORE_REF[0])
    argv = [sys.executable, "scripts/motion_build.py", "--plan", _rel(plan), "--out", _rel(out)]
    if not params.sequence:
        argv += ["--no-sequence"]
    return argv


def _motion_render_after(params: MotionRenderParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, out = _motion_render_paths(params, store)
    builds = sorted(out.glob("build-*"), key=lambda path: path.stat().st_mtime)
    if not builds:
        raise TaskError("not_found", "没有生成 motion build 目录")
    build = builds[-1]
    manifest = build / "motion_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    sequence = data.get("sequence") or None
    result = {
        "build": _rel(build),
        "manifest": _rel(manifest),
        "shots": len(data.get("shots") or []),
        "sequence": sequence.get("relative") if sequence else None,
        "sequence_seconds": sequence.get("measured_seconds") if sequence else None,
        "sequence_status": (sequence.get("video_check") or {}).get("status") if sequence else None,
    }
    if not params.quality:
        result["quality_status"] = "SKIPPED"
        return result
    from ..quality import check_motion_quality

    quality = check_motion_quality(manifest, root=store.root)
    result["quality_report"] = _rel(Path(quality["report"]))
    result["quality_status"] = quality["status"]
    result["quality_code"] = quality["code"]
    if quality["status"] != "PASS":
        raise TaskError(
            "quality_failed",
            f"motion quality {quality['code']}: {_rel(Path(quality['report']))}",
        )
    return result


def _audio_qa_paths(params: AudioQAParams, store: WorkspaceStore) -> tuple[Path, Path | None]:
    base = _episode_root(params.episode_id, store)
    manifest = (store.root / params.manifest).resolve() if params.manifest else base / "audio_manifest.json"
    if params.timeline:
        timeline: Path | None = (store.root / params.timeline).resolve()
    else:
        renders = base.parent / "renders"
        candidates = sorted(renders.glob("*/timeline.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        timeline = candidates[0] if candidates else None
    return manifest, timeline


def _audio_qa_prereqs(params: AudioQAParams, store: WorkspaceStore) -> list[str]:
    if params.audio_timeline:
        path = (store.root / params.audio_timeline).resolve()
        missing = [] if path.is_file() else [f"缺少 {_rel(path)}"]
        if params.audio_assets:
            assets = (store.root / params.audio_assets).resolve()
            if not assets.is_file():
                missing.append(f"缺少 {_rel(assets)}")
        return missing
    try:
        manifest, timeline = _audio_qa_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = [] if manifest.is_file() else [f"缺少 {_rel(manifest)}"]
    if timeline is not None and not timeline.is_file():
        missing.append(f"缺少 {_rel(timeline)}")
    return missing


def _audio_qa_argv(params: AudioQAParams, task_id: str) -> list[str]:
    if params.audio_timeline:
        argv = [sys.executable, "-m", "drama_studio.quality",
                "--audio-timeline", _rel((_STORE_REF[0].root / params.audio_timeline).resolve())]
        if params.audio_assets:
            argv += ["--audio-assets",
                     _rel((_STORE_REF[0].root / params.audio_assets).resolve())]
        return argv
    manifest, timeline = _audio_qa_paths(params, _STORE_REF[0])
    argv = [sys.executable, "-m", "drama_studio.quality", "--audio-manifest", _rel(manifest)]
    if timeline is not None:
        argv += ["--timeline", _rel(timeline)]
    return argv


def _audio_qa_after(params: AudioQAParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    if params.audio_timeline:
        base = (store.root / params.audio_timeline).resolve().parent
        report = base / "audio_timeline_report.json"
    else:
        manifest, _ = _audio_qa_paths(params, store)
        report = manifest.parent / "audio_qa_report.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    if params.audio_timeline:
        return {
            "report": _rel(report),
            "status": data.get("status"),
            "tracks": len(data.get("tracks") or []),
            "duration_ms": data.get("duration_ms"),
        }
    return {
        "report": _rel(report),
        "status": data.get("status"),
        "lines": data.get("summary", {}).get("lines"),
        "failed_lines": data.get("summary", {}).get("failed_lines"),
        "pronunciation_review": (data.get("pronunciation") or {}).get("review_status"),
    }


def _aesthetic_plan_paths(
    params: AestheticPlanParams, store: WorkspaceStore
) -> tuple[Path, Path | None, Path | None, Path, Path]:
    base = _episode_root(params.episode_id, store)
    script = (store.root / params.script).resolve() if params.script else base / "production_script.json"
    if params.designs:
        designs: Path | None = (store.root / params.designs).resolve()
    else:
        candidate = base / "designs.json"
        designs = candidate if candidate.is_file() else None
    if params.axes:
        axes: Path | None = (store.root / params.axes).resolve()
    else:
        candidate = base / "axes.json"
        axes = candidate if candidate.is_file() else None
    out = (store.root / params.out).resolve() if params.out else base / "aesthetic" / "aesthetic_plan.json"
    snapshot_root = (
        (store.root / params.snapshot_root).resolve()
        if params.snapshot_root else base / "aesthetic" / "snapshots"
    )
    return script, designs, axes, out, snapshot_root


def _aesthetic_plan_prereqs(params: AestheticPlanParams, store: WorkspaceStore) -> list[str]:
    try:
        script, designs, axes, _, _ = _aesthetic_plan_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = [] if script.is_file() else [f"缺少 {_rel(script)}"]
    if designs is not None and not designs.is_file():
        missing.append(f"缺少 {_rel(designs)}")
    if axes is not None and not axes.is_file():
        missing.append(f"缺少 {_rel(axes)}")
    return missing


def _aesthetic_plan_argv(params: AestheticPlanParams, task_id: str) -> list[str]:
    store = _STORE_REF[0]
    script, designs, axes, out, snapshot_root = _aesthetic_plan_paths(params, store)
    episode = store.get_episode(params.episode_id) or {}
    style = _locked_style(episode, params.style)
    argv = [
        sys.executable, "scripts/aesthetic_plan.py",
        "--script", _rel(script), "--out", _rel(out),
        "--snapshot-root", _rel(snapshot_root),
        "--seed-base", str(params.seed_base),
        "--width", str(params.width), "--height", str(params.height),
        "--steps", str(params.steps), "--cfg", str(params.cfg),
    ]
    if style:
        argv += ["--style", style]
    if designs is not None:
        argv += ["--designs", _rel(designs)]
    if axes is not None:
        argv += ["--axes", _rel(axes)]
    return argv


def _aesthetic_plan_after(params: AestheticPlanParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, _, out, _ = _aesthetic_plan_paths(params, store)
    manifest_path = out.parent / "aesthetic_plan_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan = json.loads(out.read_text(encoding="utf-8"))
    episode = store.get_episode(params.episode_id)
    locked = locked_preset_id(episode) or locked_style_id(episode)
    if locked and plan.get("style_id") != locked:
        raise TaskError("style_locked", f"aesthetic plan style {plan.get('style_id')!r} != locked {locked!r}")
    return {
        "plan": _rel(out),
        "manifest": _rel(manifest_path),
        "shots": len(data.get("axes") or {}),
        "snapshot_run": data.get("snapshot_run"),
        "jobs": [item.get("jobs") for item in data.get("variants") or []],
    }


def _aesthetic_compare_paths(
    params: AestheticCompareParams, store: WorkspaceStore
) -> tuple[Path, Path, Path]:
    base = _episode_root(params.episode_id, store)
    plan = (store.root / params.plan).resolve() if params.plan else base / "aesthetic" / "aesthetic_plan.json"
    if params.images:
        images = (store.root / params.images).resolve()
    else:
        runs = sorted(
            (base / "aesthetic" / "snapshots").glob("snapshot-*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        images = (runs[0] / "images") if runs else base / "aesthetic" / "snapshots" / "images"
    out = (store.root / params.out).resolve() if params.out else base / "aesthetic" / "compare"
    return plan, images, out


def _aesthetic_compare_prereqs(params: AestheticCompareParams, store: WorkspaceStore) -> list[str]:
    try:
        plan, images, _ = _aesthetic_compare_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    missing = [] if plan.is_file() else [f"缺少 {_rel(plan)}"]
    if not images.is_dir():
        missing.append(f"缺少 A/B 图片根目录 {_rel(images)}")
    return missing


def _aesthetic_compare_argv(params: AestheticCompareParams, task_id: str) -> list[str]:
    plan, images, out = _aesthetic_compare_paths(params, _STORE_REF[0])
    return [
        sys.executable, "scripts/aesthetic_compare.py",
        "--plan", _rel(plan), "--images", _rel(images), "--out", _rel(out),
    ]


def _aesthetic_compare_after(params: AestheticCompareParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, out = _aesthetic_compare_paths(params, store)
    data = json.loads((out / "comparison.json").read_text(encoding="utf-8"))
    return {
        "report": _rel(out / "comparison.json"),
        "contact_sheet": data.get("contact_sheet"),
        "status": data.get("status"),
        "shots": len(data.get("shots") or []),
        "missing": data.get("missing") or [],
    }


def _aesthetic_review_paths(
    params: AestheticReviewParams, store: WorkspaceStore
) -> tuple[Path, Path]:
    base = _episode_root(params.episode_id, store)
    report = (
        (store.root / params.report).resolve() if params.report
        else base / "aesthetic" / "compare" / "comparison.json"
    )
    return report, report.parent


def _aesthetic_review_prereqs(params: AestheticReviewParams, store: WorkspaceStore) -> list[str]:
    try:
        report, _ = _aesthetic_review_paths(params, store)
    except TaskError as exc:
        return [exc.message]
    return [] if report.is_file() else [f"缺少 {_rel(report)}"]


def _aesthetic_review_handler(params: AestheticReviewParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    report, out_dir = _aesthetic_review_paths(params, store)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"aesthetic_review_{stamp}.json"
    if path.exists():
        path = out_dir / f"aesthetic_review_{stamp}_{secrets.token_hex(3)}.json"
    record = {
        "episode_id": params.episode_id,
        "report": _rel(report),
        "decision": params.decision,
        "note": params.note,
        "shot_id": params.shot_id,
        "variant": params.variant,
        "task_id": task_id,
        "created_at": now_iso(),
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"review": _rel(path), "decision": params.decision}


TASK_KINDS: dict[str, TaskKind] = {
    "doctor.run": TaskKind(
        key="doctor.run",
        label="环境诊断",
        description="运行 drama doctor --json --no-report，返回硬件、服务、模型与配置的真实状态。",
        cost="秒级到 2 分钟（XPU 探测可能较慢）",
        safety="只读，不修改任何文件（--no-report 不写报告）",
        params_model=EmptyParams,
        lock_key=lambda params: "doctor",
        build_argv=lambda params, task_id: [sys.executable, "-m", "drama_studio", "doctor", "--json", "--no-report"],
        after_success=_doctor_after,
    ),
    "build.rebuild": TaskKind(
        key="build.rebuild",
        label="合成重建",
        description="用本期真实的 segments.json 与 audio_manifest.json 调用 scripts/r3_build.py，写入新的时间戳目录。",
        cost="约 2 分钟（纯 FFmpeg，无 GPU）",
        safety="只写 projects/<project>/episodes/<episode>/renders/build-<时间>/；拒绝覆盖已有成片",
        params_model=BuildParams,
        lock_key=lambda params: f"build:{params.episode_id}",
        build_argv=_build_argv,
        prerequisites=_build_prereqs,
        after_success=_build_after,
    ),
    "comfy.batch": TaskKind(
        key="comfy.batch",
        label="ComfyUI 批处理",
        description="调用 scripts/r1_batch.py 执行 experiments/ 下已有的 jobs JSON；不自动生成参数。",
        cost="分钟到小时级；Wan 单段约 36 分钟",
        safety="全局 GPU 单飞锁；ComfyUI 必须已在 8188 运行",
        params_model=ComfyParams,
        lock_key=lambda params: "gpu:comfy",
        build_argv=lambda params, task_id: [
            sys.executable,
            "scripts/r1_batch.py",
            "--jobs",
            params.jobs,
            *(["--only", params.only] if params.only else []),
            *(["--force"] if params.force else []),
            "--timeout",
            str(params.timeout),
        ],
        prerequisites=_comfy_prereqs,
        after_success=_comfy_after,
        danger=True,
    ),
    "li.run": TaskKind(
        key="li.run",
        label="文学分析五轮",
        description="调用 literary_intelligence/run_li15.py；脚本自行管理 8080（仅在未启动时拉起，并在结束后只停止自己启动的实例）。",
        cost="真实 30B CPU 推理，数分钟",
        safety="LLM 单飞锁；输出写入新的 runs/workspace-* 目录，不覆盖历史运行",
        params_model=LIParams,
        lock_key=lambda params: "llm:8080",
        build_argv=_li_argv,
        prerequisites=_li_prereqs,
        after_success=_li_after,
        danger=True,
    ),
    "service.comfy.start": TaskKind(
        key="service.comfy.start",
        label="启动 ComfyUI",
        description="调用既有 scripts/start.ps1（8188）。",
        cost="秒到 3 分钟",
        safety="只启动项目既有实例；端口已监听时脚本自行退出",
        params_model=ServiceParams,
        lock_key=lambda params: "service:comfy",
        build_argv=lambda params, task_id: [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", "scripts/start.ps1",
        ],
        prerequisites=lambda params, store: (
            [] if _port_open("127.0.0.1", 8188) else []
        ),
        danger=True,
    ),
    "service.comfy.stop": TaskKind(
        key="service.comfy.stop",
        label="停止 ComfyUI",
        description="调用既有 scripts/stop.ps1。",
        cost="秒级",
        safety="只停止项目自己的 ComfyUI 进程树",
        params_model=ServiceParams,
        lock_key=lambda params: "service:comfy",
        build_argv=lambda params, task_id: [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", "scripts/stop.ps1",
        ],
        danger=True,
    ),
    "package.build": TaskKind(
        key="package.build",
        label="内容包构建",
        description="从已登记语料与 claims 生成严格校验的 ContentPackage（draft）。",
        cost="秒级",
        safety="只写本期 content_package.json；不调用模型、不改证据",
        params_model=PackageParams,
        lock_key=lambda params: f"package:{params.episode_id}",
        build_argv=_package_argv,
        prerequisites=_package_prereqs,
        after_success=_package_after,
    ),
    "script.generate": TaskKind(
        key="script.generate",
        label="文案与分镜生成",
        description="调用本地 LLM，把 ContentPackage + 风格快照转成严格 Schema 的文案和分镜，并生成 ComfyUI jobs。",
        cost="数分钟（CPU LLM）",
        safety="只写本期 production_script/narration/style/jobs；原始输出保留；失败不覆盖旧脚本",
        params_model=ScriptParams,
        lock_key=lambda params: "llm:8080",
        build_argv=_script_argv,
        prerequisites=_script_prereqs,
        after_success=_script_after,
        danger=True,
    ),
    "video.jobs": TaskKind(
        key="video.jobs",
        label="Wan I2V 任务生成",
        description="读取 ProductionScript 的 type=video 镜头与 FLUX 关键帧，生成 r1_batch 兼容的 Wan jobs；不执行生成。",
        cost="秒级",
        safety="只读脚本/关键帧，写本期 comfy/jobs_video.json；缺关键帧直接失败",
        params_model=VideoJobsParams,
        lock_key=lambda params: f"video:{params.episode_id}",
        build_argv=_video_jobs_argv,
        prerequisites=_video_jobs_prereqs,
        after_success=_video_jobs_after,
    ),
    "segments.build": TaskKind(
        key="segments.build",
        label="生产分段适配",
        description="把 production_script、已生成图片和 audio_manifest 映射为 R3 的 segments.json。",
        cost="秒级",
        safety="只写本期 segments.json 与 segments.meta.json；缺图片直接失败",
        params_model=SegmentsParams,
        lock_key=lambda params: f"segments:{params.episode_id}",
        build_argv=_segments_argv,
        prerequisites=_segments_prereqs,
        after_success=_segments_after,
    ),
    "motion.plan": TaskKind(
        key="motion.plan",
        label="动态分镜计划",
        description="按 production_script、音频真时长和风格运动策略生成 motion_shots.json；只写计划，不渲染。",
        cost="秒级",
        safety="只写本期 motion_shots.json 与 motion_plan.meta.json；缺图片/音频直接失败",
        params_model=MotionPlanParams,
        lock_key=lambda params: f"motion:{params.episode_id}",
        build_argv=_motion_plan_argv,
        prerequisites=_motion_plan_prereqs,
        after_success=_motion_plan_after,
    ),
    "motion.render": TaskKind(
        key="motion.render",
        label="动态片段渲染",
        description="用 FFmpeg 确定性合成镜头缓动、局部微动与水墨转场，写入新的 motion/build-<时间>/ 目录。",
        cost="纯 CPU；每镜头约 10-40 秒（含图层生成）",
        safety="只写本期 motion/build-<时间>/；不调用 GPU、不覆盖历史产物",
        params_model=MotionRenderParams,
        lock_key=lambda params: f"motion:{params.episode_id}",
        build_argv=_motion_render_argv,
        prerequisites=_motion_render_prereqs,
        after_success=_motion_render_after,
    ),
    "audio.qa": TaskKind(
        key="audio.qa",
        label="音频质量检查",
        description="逐行检查响度、削波、静音、时长，并在有 timeline.json 时核对字幕与音频时序。",
        cost="秒级到 1 分钟",
        safety="只读音频，写 audio_qa_report.json；发音正确性仍需人工/ASR",
        params_model=AudioQAParams,
        lock_key=lambda params: f"audio:{params.episode_id}",
        build_argv=_audio_qa_argv,
        prerequisites=_audio_qa_prereqs,
        after_success=_audio_qa_after,
    ),
    "aesthetic.plan": TaskKind(
        key="aesthetic.plan",
        label="镜头美学计划",
        description="为每个镜头生成六维美学规格与 A/B 候选，冻结 snapshot 并写出两套 ComfyUI jobs；不生成图片。",
        cost="秒级",
        safety="只写本期 aesthetic/ 与带时间戳 snapshot；不覆盖旧版本；不占用 GPU",
        params_model=AestheticPlanParams,
        lock_key=lambda params: f"aesthetic:{params.episode_id}",
        build_argv=_aesthetic_plan_argv,
        prerequisites=_aesthetic_plan_prereqs,
        after_success=_aesthetic_plan_after,
    ),
    "aesthetic.compare": TaskKind(
        key="aesthetic.compare",
        label="美学 A/B 对照",
        description="比较 A/B 生成图，计算构图/光影/色彩风险指标，生成联系表与人工审核包。",
        cost="秒级到 1 分钟（纯 CPU）",
        safety="只读图片，写 comparison.json / comparison.md / contact_sheet.png",
        params_model=AestheticCompareParams,
        lock_key=lambda params: f"aesthetic:{params.episode_id}",
        build_argv=_aesthetic_compare_argv,
        prerequisites=_aesthetic_compare_prereqs,
        after_success=_aesthetic_compare_after,
    ),
    "aesthetic.review": TaskKind(
        key="aesthetic.review",
        label="美学人工结论",
        description="把人工对 A/B 对照的结论写入新的 aesthetic_review_<时间>.json；不修改图片或旧结论。",
        cost="秒级",
        safety="只新增结论文件，不覆盖历史",
        params_model=AestheticReviewParams,
        lock_key=lambda params: f"aesthetic:{params.episode_id}",
        build_argv=lambda params, task_id: [],
        prerequisites=_aesthetic_review_prereqs,
        handler=_aesthetic_review_handler,
    ),
    "quality.check": TaskKind(
        key="quality.check",
        label="技术质量检查",
        description="独立检查图片空/黑、视频解码/分辨率、音频峰值与成片哈希。",
        cost="秒级到 1 分钟",
        safety="只读产物，写 quality_report.json",
        params_model=QualityParams,
        lock_key=lambda params: f"quality:{params.episode_id}",
        build_argv=_quality_argv,
        prerequisites=_quality_prereqs,
        after_success=_quality_after,
    ),
    "style.consistency": TaskKind(
        key="style.consistency",
        label="跨镜头风格一致性",
        description="对本期所有镜头静态图做调色板贴合、跨镜头 LAB 距离、亮度/饱和度/边缘密度检查；人工审片单独记录。",
        cost="秒级",
        safety="只读静态图，写本期 style_consistency_report.json；技术 OK 仍为 PARTIAL，需人工 APPROVED",
        params_model=StyleConsistencyParams,
        lock_key=lambda params: f"style:{params.episode_id}",
        build_argv=_style_consistency_argv,
        prerequisites=_style_consistency_prereqs,
        after_success=_style_consistency_after,
    ),
    "static.check": TaskKind(
        key="static.check",
        label="静态质量门",
        description="对单个镜头的静态图跑客观指标与人工语义清单，写 work/static/<shot_id>/static_quality.json。",
        cost="秒级",
        safety="只读图片，写本期 work/static/<shot_id>/；PENDING/PARTIAL 不算通过",
        params_model=StaticCheckParams,
        lock_key=lambda params: f"static:{params.episode_id}",
        build_argv=_static_argv,
        prerequisites=_static_prereqs,
        after_success=_static_after,
    ),
    "story.check": TaskKind(
        key="story.check",
        label="故事圣经连续性检查",
        description="校验 Character/Shot Bible 的镜头覆盖、人物引用、风格一致性与声音档案状态；不检查同脸。",
        cost="秒级",
        safety="只读脚本与两份 Bible，写本期 story_bible_report.json；失败不修改产物",
        params_model=StoryCheckParams,
        lock_key=lambda params: f"story:{params.episode_id}",
        build_argv=_story_argv,
        prerequisites=_story_prereqs,
        after_success=_story_after,
    ),
    "tts.synthesize": TaskKind(
        key="tts.synthesize",
        label="配音合成",
        description="按本期 narration.json 逐句调用 CosyVoice，写入本期 audio/ 与 audio_manifest.json。",
        cost="分钟级（CPU）",
        safety="只写本期 audio/ 与 audio_manifest.json；已有有效 manifest 时复用，--force 才重合成",
        params_model=TTSParams,
        lock_key=lambda params: f"tts:{params.episode_id}",
        build_argv=_tts_argv,
        prerequisites=_tts_prereqs,
        after_success=_tts_after,
        danger=True,
    ),
    "review.accept": TaskKind(
        key="review.accept",
        label="人工验收 · 通过",
        description="把本期人工验收结论写为通过（human_review.json）。",
        cost="秒级",
        safety="只写本期产物目录下的 human_review.json，不修改产物",
        params_model=ReviewParams,
        lock_key=lambda params: f"review:{params.episode_id}",
        build_argv=lambda params, task_id: [],
        prerequisites=_review_prereqs,
        handler=_review_handler("accept"),
    ),
    "review.reject": TaskKind(
        key="review.reject",
        label="人工验收 · 拒绝",
        description="把本期人工验收结论写为拒绝（human_review.json）。",
        cost="秒级",
        safety="只写本期产物目录下的 human_review.json，不修改产物",
        params_model=ReviewParams,
        lock_key=lambda params: f"review:{params.episode_id}",
        build_argv=lambda params, task_id: [],
        prerequisites=_review_prereqs,
        handler=_review_handler("reject"),
    ),
}


def _require_confirm(params: BaseModel) -> None:
    if not getattr(params, "confirm", False):
        raise TaskError("confirmation_required", "该操作需要 confirm=true")


_STORE_REF: list[WorkspaceStore] = []


class TaskRunner:
    def __init__(self, store: WorkspaceStore) -> None:
        self.store = store
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._cancelled: set[str] = set()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        _STORE_REF[:] = [store]
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------- public ----------------

    def kinds(self) -> list[dict[str, Any]]:
        return [kind.spec() for kind in TASK_KINDS.values()]

    def create(self, kind_key: str, raw_params: dict[str, Any], project_id: str | None = None,
               episode_id: str | None = None) -> dict[str, Any]:
        kind = TASK_KINDS.get(kind_key)
        if kind is None:
            raise TaskError("unknown_kind", f"未注册的任务类型：{kind_key}")
        if not kind.enabled:
            raise TaskError("blocked_kind", kind.blocked_reason or "该任务当前不可用")
        try:
            params = kind.params_model.model_validate(raw_params or {})
        except ValidationError as exc:
            raise TaskError("invalid_params", "参数校验失败", json.loads(exc.json())) from exc
        if kind.danger:
            _require_confirm(params)

        lock_key = kind.lock_key(params)
        running = self.store.running_lock(lock_key)
        if running:
            raise TaskConflict(
                "task_conflict",
                f"已有同类任务在运行：{running['id']}（{running['kind']}）",
                {"task_id": running["id"]},
            )

        if episode_id is None and isinstance(params, (BuildParams, ReviewParams, TTSParams, PackageParams, ScriptParams, SegmentsParams, QualityParams)):
            episode_id = params.episode_id
        if episode_id and not project_id:
            episode = self.store.get_episode(episode_id)
            if episode:
                project_id = episode.get("project_id")

        task_id = f"task_{datetime.now(timezone.utc):%Y%m%d%H%M%S}_{secrets.token_hex(3)}"
        log_path = LOG_DIR / f"{task_id}.log"
        task = {
            "id": task_id,
            "kind": kind_key,
            "lock_key": lock_key,
            "status": PENDING,
            "project_id": project_id,
            "episode_id": episode_id,
            "params": params.model_dump(),
            "result": {},
            "error": None,
            "exit_code": None,
            "log_path": _rel(log_path),
            "created_at": now_iso(),
            "started_at": None,
            "finished_at": None,
        }

        missing = kind.prerequisites(params, self.store)
        if missing:
            task["status"] = BLOCKED
            task["error"] = "前置条件不满足：" + "；".join(missing)
            task["finished_at"] = now_iso()
            return self.store.insert_task(task)

        self.store.insert_task(task)
        loop = asyncio.get_running_loop()
        self._tasks[task_id] = loop.create_task(self._execute(task_id, kind, params))
        return self.store.get_task(task_id) or task

    async def cancel(self, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id)
        if not task:
            raise TaskError("not_found", "任务不存在")
        if task["status"] not in (PENDING, RUNNING):
            raise TaskError("not_cancellable", "只有 PENDING / RUNNING 任务可以取消")
        self._cancelled.add(task_id)
        proc = self._procs.get(task_id)
        if proc and proc.returncode is None:
            _kill_tree(proc.pid)
        self.store.update_task(
            task_id,
            status=CANCELLED,
            finished_at=now_iso(),
            error="用户取消",
        )
        return self.store.get_task(task_id) or task

    def read_log(self, task_id: str, offset: int = 0, limit: int = 64 * 1024) -> dict[str, Any]:
        task = self.store.get_task(task_id)
        if not task:
            raise TaskError("not_found", "任务不存在")
        path = ROOT / (task.get("log_path") or "")
        if not path.is_file():
            return {"text": "", "next_offset": offset, "eof": task["status"] not in (PENDING, RUNNING)}
        size = path.stat().st_size
        offset = max(0, min(offset, size))
        with path.open("rb") as fh:
            fh.seek(offset)
            chunk = fh.read(limit)
        text = chunk.decode("utf-8", "replace")
        next_offset = offset + len(chunk)
        return {
            "text": text,
            "next_offset": next_offset,
            "eof": next_offset >= size and task["status"] not in (PENDING, RUNNING),
        }

    # ---------------- execution ----------------

    async def _execute(self, task_id: str, kind: TaskKind, params: BaseModel) -> None:
        if task_id in self._cancelled:
            return

        task = self.store.get_task(task_id) or {}
        log_path = ROOT / (task.get("log_path") or f"logs/workspace/tasks/{task_id}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Conditional transition: if cancel() already moved the task to
        # CANCELLED, this returns False and no process is ever launched.
        if not self.store.mark_running(task_id, now_iso()):
            return

        if kind.handler is not None:
            header = (
                f"# task {task_id}\n"
                f"# kind {kind.key}\n"
                f"# started {now_iso()}\n"
                f"# mode in-process\n\n"
            )
            log_path.write_text(header, encoding="utf-8")
            status = SUCCEEDED
            result: dict[str, Any] = {}
            error: str | None = None
            try:
                result = await asyncio.to_thread(kind.handler, params, task_id, self.store)
            except TaskError as exc:
                status = FAILED
                error = exc.message
            except Exception as exc:  # noqa: BLE001 - record instead of losing the task
                status = FAILED
                error = f"{type(exc).__name__}: {exc}"
            if task_id in self._cancelled:
                return
            self.store.update_task(
                task_id,
                status=status,
                exit_code=0 if status == SUCCEEDED else 1,
                result=result,
                error=error,
                finished_at=now_iso(),
            )
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"\n# finished {now_iso()} status={status}\n")
            return

        try:
            argv = kind.build_argv(params, task_id)
        except TaskError as exc:
            self.store.update_task(task_id, status=BLOCKED, error=exc.message, finished_at=now_iso())
            return
        except Exception as exc:  # noqa: BLE001
            self.store.update_task(task_id, status=FAILED, error=f"{type(exc).__name__}: {exc}", finished_at=now_iso())
            return

        if task_id in self._cancelled:
            return

        header = (
            f"# task {task_id}\n"
            f"# kind {kind.key}\n"
            f"# started {now_iso()}\n"
            f"# cwd {ROOT}\n"
            f"# argv {' '.join(argv)}\n\n"
        )
        log_path.write_text(header, encoding="utf-8")

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, ValueError) as exc:
            self.store.update_task(task_id, status=FAILED, error=f"无法启动进程：{exc}", finished_at=now_iso())
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"\n[launcher error] {exc}\n")
            return

        self._procs[task_id] = proc
        if task_id in self._cancelled:
            _kill_tree(proc.pid)
            try:
                await proc.wait()
            finally:
                self._procs.pop(task_id, None)
            return

        try:
            assert proc.stdout is not None
            with log_path.open("a", encoding="utf-8") as fh:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    fh.write(line.decode("utf-8", "replace"))
                    fh.flush()
            exit_code = await proc.wait()
        finally:
            self._procs.pop(task_id, None)

        if task_id in self._cancelled:
            return

        status = SUCCEEDED if exit_code == 0 else FAILED
        result = {"argv": argv, "exit_code": exit_code}
        error = None
        if status == SUCCEEDED and kind.after_success:
            try:
                result.update(kind.after_success(params, task_id, self.store) or {})
            except TaskError as exc:
                status = FAILED
                error = f"后置校验失败：{exc.message}"
            except Exception as exc:  # noqa: BLE001
                status = FAILED
                error = f"后置校验异常：{type(exc).__name__}: {exc}"
        if status == FAILED and not error:
            tail = _tail(log_path, 1200)
            error = f"退出码 {exit_code}" + (f"：{tail}" if tail else "")
        self.store.update_task(
            task_id,
            status=status,
            exit_code=exit_code,
            result=result,
            error=error,
            finished_at=now_iso(),
        )
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n# finished {now_iso()} status={status} exit={exit_code}\n")


def _kill_tree(pid: int) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=20,
                creationflags=CREATE_NO_WINDOW,
            )
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        os.kill(pid, 15)
    except OSError:
        pass


def _tail(path: Path, limit: int) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - limit))
            return fh.read().decode("utf-8", "replace").strip()
    except OSError:
        return ""
