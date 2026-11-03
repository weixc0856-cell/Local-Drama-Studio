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
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config import find_project_root, load_settings
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


class ReviewParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=1000)


class ComfyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: str = Field(min_length=1, max_length=400)
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
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    max_tokens: int = Field(default=2000, ge=256, le=8000)
    timeout: float = Field(default=900.0, ge=30, le=3600)
    reuse: bool = False
    confirm: bool = False


class SegmentsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    script: str | None = Field(default=None, max_length=300)
    images: str | None = Field(default=None, max_length=300)
    audio: str | None = Field(default=None, max_length=300)
    out: str | None = Field(default=None, max_length=300)


class QualityParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    manifest: str | None = Field(default=None, max_length=400)


class TTSParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(min_length=1, max_length=120)
    speaker: str | None = Field(default=None, max_length=80)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    base_url: str | None = Field(default=None, max_length=300)
    force: bool = False
    timeout: float = Field(default=300.0, ge=30, le=3600)
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
        "speaker": data.get("speaker"),
        "lines": len(data.get("lines") or []),
        "total_seconds": round(sum(float(x.get("duration_seconds") or 0) for x in data.get("lines") or []), 3),
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
        "--speed", str(params.speed),
    ]
    if params.speaker:
        argv += ["--speaker", params.speaker]
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
    )
    result.update({"script": _rel(out), "style": _rel(style_path), "shots": len(script.get("shots") or [])})
    return result


def _segments_paths(params: SegmentsParams, store: WorkspaceStore) -> tuple[Path, Path, Path, Path]:
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
    return missing


def _segments_argv(params: SegmentsParams, task_id: str) -> list[str]:
    script, images, audio, out = _segments_paths(params, _STORE_REF[0])
    return [
        sys.executable, "-m", "drama_studio.production",
        "--script", _rel(script),
        "--images", _rel(images),
        "--audio", _rel(audio),
        "--out", _rel(out),
    ]


def _segments_after(params: SegmentsParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    _, _, _, out = _segments_paths(params, store)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"segments": _rel(out), "count": len(data)}


def _quality_paths(params: QualityParams, store: WorkspaceStore) -> Path:
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
    return [sys.executable, "-m", "drama_studio.quality", "--manifest", _rel(path), "--root", "."]


def _quality_after(params: QualityParams, task_id: str, store: WorkspaceStore) -> dict[str, Any]:
    path = _quality_paths(params, store)
    report = path.parent / "quality_report.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    return {"report": _rel(report), "status": data.get("status"), "final": (data.get("final") or {}).get("status")}


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
