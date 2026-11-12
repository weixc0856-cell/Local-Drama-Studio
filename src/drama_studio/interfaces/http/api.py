"""FastAPI application for the local production workspace."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, ConfigDict, Field

from drama_studio import __version__
from drama_studio.workspace import discovery, envprobe, media
from drama_studio.infrastructure.storage.store import WorkspaceStore, get_store
from drama_studio.application.operations.tasks import TASK_KINDS, TaskConflict, TaskError, TaskRunner

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

_store: WorkspaceStore = get_store()
_runner = TaskRunner(_store)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    recovered = _store.recover_stale_tasks()
    if recovered:
        print(f"[workspace] marked {recovered} stale RUNNING task(s) as interrupted")
    yield


app = FastAPI(
    title="Local Drama Studio — Production Workspace",
    version=__version__,
    lifespan=_lifespan,
)

from drama_studio.interfaces.http.film_api import router as _film_router

app.include_router(_film_router)


# ---------------------------------------------------------------- models


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(Strict):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    positioning: str = ""
    default_style_id: str | None = None
    default_voice: str = ""
    aspect_ratio: str = "9:16"
    target_platforms: list[str] = Field(default_factory=list)


class ProjectUpdate(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    positioning: str | None = None
    default_style_id: str | None = None
    default_voice: str | None = None
    aspect_ratio: str | None = None
    target_platforms: list[str] | None = None


class EpisodeCreate(Strict):
    project_id: str
    number: int = Field(ge=1, le=9999)
    title: str = Field(min_length=1, max_length=160)
    track: str = Field(default="video", pattern="^(video|literary)$")
    artifact_root: str | None = None
    style_id: str | None = None
    notes: str = ""


class EpisodeUpdate(Strict):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    artifact_root: str | None = None
    style_id: str | None = None
    notes: str | None = None


class StylePayload(Strict):
    name: str = Field(min_length=1, max_length=120)
    preset_id: str | None = Field(default=None, max_length=80)
    description: str = ""
    visual_language: str = ""
    color_palette: dict[str, str] = Field(default_factory=dict)
    lighting: str = ""
    camera_language: str = ""
    composition: str = ""
    character_design: str = ""
    environment_design: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    reference_assets: list[str] = Field(default_factory=list)
    aspect_ratio: str = "9:16"
    applicable_content_types: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)


class StyleUpdate(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    preset_id: str | None = Field(default=None, max_length=80)
    description: str | None = None
    visual_language: str | None = None
    color_palette: dict[str, str] | None = None
    lighting: str | None = None
    camera_language: str | None = None
    composition: str | None = None
    character_design: str | None = None
    environment_design: str | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    reference_assets: list[str] | None = None
    aspect_ratio: str | None = None
    applicable_content_types: list[str] | None = None
    source_files: list[str] | None = None


class TaskCreate(Strict):
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    episode_id: str | None = None


# ---------------------------------------------------------------- errors


@app.exception_handler(TaskError)
async def _task_error(request: Request, exc: TaskError) -> JSONResponse:
    status = 409 if isinstance(exc, TaskConflict) else 400
    if exc.code in ("unknown_episode", "unknown_kind", "not_found"):
        status = 404
    return JSONResponse(
        status_code=status,
        content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
    )


@app.exception_handler(media.MediaError)
async def _media_error(request: Request, exc: media.MediaError) -> JSONResponse:
    status = 416 if isinstance(exc, media.RangeNotSatisfiable) else (
        404 if exc.code == "not_found" else 403
    )
    if isinstance(exc, media.RangeNotSatisfiable):
        return JSONResponse(status_code=416, content={"error": {"code": exc.code, "message": exc.message}})
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(ValueError)
async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {"code": "invalid", "message": str(exc)}})


# ---------------------------------------------------------------- helpers


def _episode_or_404(episode_id: str) -> dict[str, Any]:
    episode = _store.get_episode(episode_id)
    if not episode:
        raise TaskError("not_found", f"期数不存在：{episode_id}")
    return episode


async def _analyze(episode_id: str) -> dict[str, Any]:
    episode = _episode_or_404(episode_id)
    return await asyncio.to_thread(discovery.analyze_episode, _store, episode)


def _episode_summary(view: dict[str, Any]) -> dict[str, Any]:
    storyboard = view.get("storyboard") or {}
    thumb = None
    for seg in storyboard.get("segments") or []:
        if seg.get("type") == "image" and seg.get("source_exists"):
            thumb = seg["source"]
            break
    if not thumb and view.get("final"):
        thumb = view["final"].get("path")
    return {
        "id": view["id"],
        "project_id": view["project_id"],
        "project": view.get("project"),
        "number": view.get("number"),
        "title": view.get("title"),
        "track": view.get("track"),
        "status": view.get("status"),
        "status_label": view.get("status_label"),
        "progress": view.get("progress"),
        "style": (view.get("style") or {}).get("name") if view.get("style") else None,
        "updated_at": view.get("updated_at"),
        "final": view.get("final"),
        "thumb": thumb,
        "artifact_root": view.get("artifact_root"),
        "artifact_root_exists": view.get("artifact_root_exists"),
        "review": view.get("review"),
    }


def _count_videos() -> int:
    """Generated video assets and finished renders, not intermediate segments."""
    patterns = (
        "assets/**/*.mp4",
        "experiments/*/runs/*/*.mp4",
        "experiments/*/renders/final_*.mp4",
        "projects/*/episodes/*/renders/*/final_*.mp4",
    )
    seen: set[str] = set()
    for pattern in patterns:
        for path in discovery.ROOT.glob(pattern):
            if path.is_file():
                seen.add(str(path))
    return len(seen)


def _count_renders() -> int:
    patterns = ("experiments/*/renders/build_manifest.json", "projects/*/episodes/*/renders/*/build_manifest.json")
    return sum(1 for pattern in patterns for _ in discovery.ROOT.glob(pattern))


# ---------------------------------------------------------------- read API


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "root": str(discovery.ROOT)}


@app.get("/api/overview")
async def overview() -> dict[str, Any]:
    projects = _store.list_projects()
    episode_rows = _store.list_episodes()
    views = await asyncio.to_thread(
        lambda: [discovery.analyze_episode(_store, ep) for ep in episode_rows]
    )
    summaries = [_episode_summary(v) for v in views]
    summaries.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
    env = await asyncio.to_thread(envprobe.probe)
    stats = {
        "projects": len(projects),
        "episodes": len(summaries),
        "completed": sum(1 for s in summaries if s["status"] == "completed"),
        "producing": sum(1 for s in summaries if s["status"] == "producing"),
        "failed_tasks": _store.count_tasks("FAILED"),
        "pending_tasks": _store.count_tasks("PENDING"),
        "running_tasks": _store.count_tasks("RUNNING"),
        "videos": _count_videos(),
        "renders": _count_renders(),
    }
    return {
        "stats": stats,
        "recent_episodes": summaries[:6],
        "recent_tasks": _store.list_tasks(limit=8),
        "env": env,
        "episodes": summaries,
    }


@app.get("/api/projects")
async def list_projects() -> dict[str, Any]:
    projects = _store.list_projects()
    rows = _store.list_episodes()
    views = await asyncio.to_thread(
        lambda: [discovery.analyze_episode(_store, ep) for ep in rows]
    )
    by_project: dict[str, list[dict[str, Any]]] = {}
    for view in views:
        by_project.setdefault(view["project_id"], []).append(view)
    for project in projects:
        items = by_project.get(project["id"], [])
        project["episodes_total"] = len(items)
        project["episodes_completed"] = sum(1 for v in items if v["status"] == "completed")
        project["updated_at"] = max(
            [p.get("updated_at") or "" for p in [project, *items]] or [project.get("updated_at") or ""]
        )
    return {"projects": projects}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    project = await asyncio.to_thread(_store.get_project, project_id)
    if not project:
        raise TaskError("not_found", f"项目不存在：{project_id}")
    views = await asyncio.to_thread(
        lambda: [discovery.analyze_episode(_store, ep) for ep in project.get("episodes") or []]
    )
    project["episodes"] = [_episode_summary(v) for v in views]
    return project


@app.get("/api/episodes")
async def list_episodes(
    project_id: str | None = None, status: str | None = None
) -> dict[str, Any]:
    rows = _store.list_episodes(project_id)
    views = await asyncio.to_thread(
        lambda: [discovery.analyze_episode(_store, ep) for ep in rows]
    )
    summaries = [_episode_summary(v) for v in views]
    if status:
        summaries = [s for s in summaries if s["status"] == status]
    summaries.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
    return {"episodes": summaries}


@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    view.pop("storyboard", None)
    view.pop("audio", None)
    view.pop("content", None)
    return view


@app.get("/api/episodes/{episode_id}/content")
async def episode_content(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    return {
        "episode_id": episode_id,
        "kind": view["kind"],
        "status": view["status"],
        "content": view.get("content"),
        "review": view.get("review"),
        "notes": view.get("notes"),
    }


@app.get("/api/episodes/{episode_id}/storyboard")
async def episode_storyboard(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    return {"episode_id": episode_id, "status": view["status"], **(view.get("storyboard") or {})}


@app.get("/api/episodes/{episode_id}/audio")
async def episode_audio(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    return {"episode_id": episode_id, "status": view["status"], **(view.get("audio") or {})}


@app.get("/api/episodes/{episode_id}/assets")
async def episode_assets(episode_id: str) -> dict[str, Any]:
    episode = _episode_or_404(episode_id)
    items = await asyncio.to_thread(discovery.episode_assets, episode)
    return {"episode_id": episode_id, "items": items}


@app.get("/api/episodes/{episode_id}/output")
async def episode_output(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    return {
        "episode_id": episode_id,
        "builds": view.get("builds") or [],
        "latest": view.get("latest_build"),
        "final": view.get("final"),
        "status": view["status"],
        "note": "历史构建 manifest 若缺少 content_type/timeline/font 字段，说明它来自旧版 r3_build.py。",
    }


@app.get("/api/episodes/{episode_id}/workflow")
async def episode_workflow(episode_id: str) -> dict[str, Any]:
    view = await _analyze(episode_id)
    workflow = view.get("workflow") or {"nodes": [], "edges": []}
    last_by_kind: dict[str, dict[str, Any]] = {}
    for task in view.get("tasks") or []:
        last_by_kind.setdefault(task["kind"], task)
    for node in workflow["nodes"]:
        if node.get("task_kind"):
            node["last_task"] = last_by_kind.get(node["task_kind"])
            kind = TASK_KINDS.get(node["task_kind"])
            node["task_enabled"] = bool(kind and kind.enabled)
            node["task_blocked_reason"] = None if (kind and kind.enabled) else (
                (kind.blocked_reason if kind else node.get("task_reason"))
            )
    return {"episode_id": episode_id, "status": view["status"], **workflow}


@app.get("/api/workflow")
async def workflow(episode_id: str | None = None) -> dict[str, Any]:
    if not episode_id:
        rows = _store.list_episodes()
        if not rows:
            return {"episode_id": None, "nodes": [], "edges": []}
        episode_id = rows[0]["id"]
    return await episode_workflow(episode_id)


@app.get("/api/styles")
async def list_styles() -> dict[str, Any]:
    return {"styles": _store.list_styles()}


@app.get("/api/styles/{style_id}")
async def get_style(style_id: str) -> dict[str, Any]:
    style = _store.get_style(style_id)
    if not style:
        raise TaskError("not_found", f"风格不存在：{style_id}")
    return style


@app.get("/api/tasks")
async def list_tasks(
    status: str | None = None, episode_id: str | None = None, kind: str | None = None
) -> dict[str, Any]:
    return {"tasks": _store.list_tasks(status=status, episode_id=episode_id, kind=kind)}


@app.get("/api/tasks/kinds")
async def task_kinds() -> dict[str, Any]:
    return {"kinds": _runner.kinds()}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = _store.get_task(task_id)
    if not task:
        raise TaskError("not_found", f"任务不存在：{task_id}")
    return task


@app.get("/api/tasks/{task_id}/log")
async def task_log(task_id: str, offset: int = Query(default=0, ge=0)) -> dict[str, Any]:
    return _runner.read_log(task_id, offset)


@app.get("/api/assets")
async def assets(
    include_temporary: bool = False,
    limit: int = Query(default=800, ge=1, le=4000),
) -> dict[str, Any]:
    return await asyncio.to_thread(discovery.scan_assets, _store, include_temporary, limit)


@app.get("/api/env")
async def env(force: bool = False) -> dict[str, Any]:
    return await asyncio.to_thread(envprobe.probe, force)


# ---------------------------------------------------------------- write API


@app.post("/api/projects")
async def create_project(payload: ProjectCreate) -> dict[str, Any]:
    return await asyncio.to_thread(_store.create_project, payload.model_dump())


@app.patch("/api/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate) -> dict[str, Any]:
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    project = await asyncio.to_thread(_store.update_project, project_id, data)
    if not project:
        raise TaskError("not_found", f"项目不存在：{project_id}")
    return project


@app.post("/api/episodes")
async def create_episode(payload: EpisodeCreate) -> dict[str, Any]:
    return await asyncio.to_thread(_store.create_episode, payload.model_dump())


@app.patch("/api/episodes/{episode_id}")
async def update_episode(episode_id: str, payload: EpisodeUpdate) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    episode = await asyncio.to_thread(_store.update_episode, episode_id, data)
    if not episode:
        raise TaskError("not_found", f"期数不存在：{episode_id}")
    return episode


@app.post("/api/styles")
async def create_style(payload: StylePayload) -> dict[str, Any]:
    return await asyncio.to_thread(_store.create_style, payload.model_dump())


@app.patch("/api/styles/{style_id}")
async def update_style(style_id: str, payload: StyleUpdate) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    style = await asyncio.to_thread(_store.update_style, style_id, data)
    if not style:
        raise TaskError("not_found", f"风格不存在：{style_id}")
    return style


@app.post("/api/tasks")
async def create_task(payload: TaskCreate) -> dict[str, Any]:
    return _runner.create(payload.kind, payload.params, payload.project_id, payload.episode_id)


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, Any]:
    return await _runner.cancel(task_id)


# ---------------------------------------------------------------- media


@app.get("/api/media/{path:path}")
async def serve_media(path: str, request: Request):
    target = media.safe_path(path)
    size = target.stat().st_size
    range_header = request.headers.get("range")
    common = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=60",
        "Content-Type": media.content_type(target),
    }
    if not range_header:
        return StreamingResponse(
            media.iter_file(target, 0, size - 1),
            media_type=media.content_type(target),
            headers={**common, "Content-Length": str(size)},
        )
    start, end = media.parse_range(range_header, size)
    length = end - start + 1
    return StreamingResponse(
        media.iter_file(target, start, end),
        status_code=206,
        media_type=media.content_type(target),
        headers={
            **common,
            "Content-Length": str(length),
            "Content-Range": f"bytes {start}-{end}/{size}",
        },
    )


@app.get("/api/thumb/{path:path}")
async def serve_thumb(path: str, width: int = Query(default=480, ge=80, le=960)):
    target = await asyncio.to_thread(media.thumbnail, path, width)
    return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=600"})


# ---------------------------------------------------------------- SPA


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )
