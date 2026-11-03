"""SQLite-backed workspace state.

Only user-created facts live here: projects, episodes, styles and task
records. Production status is never stored; it is derived from files by
:mod:`drama_studio.workspace.discovery`.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..config import find_project_root

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  positioning TEXT NOT NULL DEFAULT '',
  default_style_id TEXT,
  default_voice TEXT NOT NULL DEFAULT '',
  aspect_ratio TEXT NOT NULL DEFAULT '9:16',
  target_platforms TEXT NOT NULL DEFAULT '[]',
  origin TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  number INTEGER NOT NULL,
  title TEXT NOT NULL,
  track TEXT NOT NULL DEFAULT 'video',
  artifact_root TEXT,
  style_id TEXT,
  style_snapshot TEXT NOT NULL DEFAULT '{}',
  notes TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id, number)
);

CREATE TABLE IF NOT EXISTS styles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  visual_language TEXT NOT NULL DEFAULT '',
  color_palette TEXT NOT NULL DEFAULT '{}',
  lighting TEXT NOT NULL DEFAULT '',
  camera_language TEXT NOT NULL DEFAULT '',
  composition TEXT NOT NULL DEFAULT '',
  character_design TEXT NOT NULL DEFAULT '',
  environment_design TEXT NOT NULL DEFAULT '',
  positive_prompt TEXT NOT NULL DEFAULT '',
  negative_prompt TEXT NOT NULL DEFAULT '',
  reference_assets TEXT NOT NULL DEFAULT '[]',
  aspect_ratio TEXT NOT NULL DEFAULT '9:16',
  applicable_content_types TEXT NOT NULL DEFAULT '[]',
  source_files TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  lock_key TEXT NOT NULL,
  status TEXT NOT NULL,
  project_id TEXT,
  episode_id TEXT,
  params TEXT NOT NULL DEFAULT '{}',
  result TEXT NOT NULL DEFAULT '{}',
  error TEXT,
  exit_code INTEGER,
  log_path TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_episode ON tasks(episode_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_running_lock
  ON tasks(lock_key) WHERE status = 'RUNNING';
"""

JSON_FIELDS = {
    "projects": ("target_platforms",),
    "episodes": ("style_snapshot",),
    "styles": (
        "color_palette",
        "reference_assets",
        "applicable_content_types",
        "source_files",
    ),
    "tasks": ("params", "result"),
}

STYLE_FIELDS = (
    "name",
    "description",
    "visual_language",
    "color_palette",
    "lighting",
    "camera_language",
    "composition",
    "character_design",
    "environment_design",
    "positive_prompt",
    "negative_prompt",
    "reference_assets",
    "aspect_ratio",
    "applicable_content_types",
    "source_files",
)

PROJECT_FIELDS = (
    "name",
    "description",
    "positioning",
    "default_style_id",
    "default_voice",
    "aspect_ratio",
    "target_platforms",
)

EPISODE_FIELDS = (
    "project_id",
    "number",
    "title",
    "track",
    "artifact_root",
    "style_id",
    "style_snapshot",
    "notes",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc):%Y%m%d%H%M%S}_{secrets.token_hex(3)}"


def _decode(table: str, row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for field in JSON_FIELDS.get(table, ()):
        raw = data.get(field)
        if isinstance(raw, str):
            try:
                data[field] = json.loads(raw)
            except json.JSONDecodeError:
                data[field] = None
    return data


def _encode(table: str, data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key in JSON_FIELDS.get(table, ()) and not isinstance(value, str):
            out[key] = json.dumps(value, ensure_ascii=False)
        else:
            out[key] = value
    return out


class WorkspaceStore:
    def __init__(self, root: Path | None = None, db_path: Path | None = None) -> None:
        self.root = (root or find_project_root()).resolve()
        self.db_path = (db_path or self.root / "projects" / "workspace.db").resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    # ---------------- projects ----------------

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC, name").fetchall()
            projects = [_decode("projects", r) for r in rows]
            for project in projects:
                assert project is not None
                project["episode_count"] = conn.execute(
                    "SELECT COUNT(*) FROM episodes WHERE project_id = ?", (project["id"],)
                ).fetchone()[0]
                project["style"] = self._style_brief(conn, project.get("default_style_id"))
            return projects

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            project = _decode(
                "projects", conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            )
            if project is None:
                return None
            project["style"] = self._style_brief(conn, project.get("default_style_id"))
            project["episodes"] = [
                _decode("episodes", r)
                for r in conn.execute(
                    "SELECT * FROM episodes WHERE project_id = ? ORDER BY number", (project_id,)
                ).fetchall()
            ]
            project["episode_count"] = len(project["episodes"])
            return project

    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("项目名称不能为空")
        project_id = (data.get("id") or _new_id("proj")).strip()
        ts = now_iso()
        payload = {field: data.get(field, "") for field in PROJECT_FIELDS}
        payload["name"] = name
        if payload.get("target_platforms") in ("", None):
            payload["target_platforms"] = []
        if not payload.get("aspect_ratio"):
            payload["aspect_ratio"] = "9:16"
        payload = _encode("projects", payload)
        with self.connect() as conn:
            conn.execute(
                f"INSERT INTO projects (id, {', '.join(payload)}, origin, created_at, updated_at) "
                f"VALUES (?, {', '.join('?' for _ in payload)}, ?, ?, ?)",
                (project_id, *payload.values(), data.get("origin", "user"), ts, ts),
            )
        return self.get_project(project_id) or {}

    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        payload = {k: v for k, v in data.items() if k in PROJECT_FIELDS}
        if "name" in payload and not str(payload["name"]).strip():
            raise ValueError("项目名称不能为空")
        if not payload:
            return self.get_project(project_id)
        payload = _encode("projects", payload)
        assignments = ", ".join(f"{key} = ?" for key in payload)
        with self.connect() as conn:
            cur = conn.execute(
                f"UPDATE projects SET {assignments}, updated_at = ? WHERE id = ?",
                (*payload.values(), now_iso(), project_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_project(project_id)

    # ---------------- episodes ----------------

    def list_episodes(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM episodes"
        args: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            args = (project_id,)
        query += " ORDER BY project_id, number"
        with self.connect() as conn:
            return [_decode("episodes", r) for r in conn.execute(query, args).fetchall()]

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            episode = _decode(
                "episodes", conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
            )
            if episode is None:
                return None
            project = conn.execute("SELECT id, name FROM projects WHERE id = ?", (episode["project_id"],)).fetchone()
            episode["project"] = dict(project) if project else None
            return episode

    def create_episode(self, data: dict[str, Any]) -> dict[str, Any]:
        project_id = str(data.get("project_id", "")).strip()
        if not project_id or self.get_project(project_id) is None:
            raise ValueError("所属项目不存在")
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("期数标题不能为空")
        try:
            number = int(data.get("number"))
        except (TypeError, ValueError) as exc:
            raise ValueError("期数编号必须是整数") from exc
        track = data.get("track", "video")
        if track not in ("video", "literary"):
            raise ValueError("track 必须是 video 或 literary")
        episode_id = (data.get("id") or _new_id("ep")).strip()
        snapshot = data.get("style_snapshot") or {}
        style_id = data.get("style_id")
        if style_id and not snapshot:
            style = self.get_style(style_id)
            if style is None:
                raise ValueError("风格不存在")
            snapshot = style
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO episodes (id, project_id, number, title, track, artifact_root, style_id,"
                " style_snapshot, notes, origin, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    episode_id,
                    project_id,
                    number,
                    title,
                    track,
                    data.get("artifact_root") or None,
                    style_id or None,
                    json.dumps(snapshot, ensure_ascii=False),
                    data.get("notes", ""),
                    data.get("origin", "user"),
                    ts,
                    ts,
                ),
            )
        return self.get_episode(episode_id) or {}

    def update_episode(self, episode_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        payload = {k: v for k, v in data.items() if k in EPISODE_FIELDS}
        if "style_id" in payload:
            style = self.get_style(payload["style_id"]) if payload["style_id"] else None
            if payload["style_id"] and style is None:
                raise ValueError("风格不存在")
            if style is not None:
                payload["style_snapshot"] = style
        if not payload:
            return self.get_episode(episode_id)
        payload = _encode("episodes", payload)
        assignments = ", ".join(f"{key} = ?" for key in payload)
        with self.connect() as conn:
            cur = conn.execute(
                f"UPDATE episodes SET {assignments}, updated_at = ? WHERE id = ?",
                (*payload.values(), now_iso(), episode_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_episode(episode_id)

    def touch_episode(self, episode_id: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE episodes SET updated_at = ? WHERE id = ?", (now_iso(), episode_id))

    # ---------------- styles ----------------

    def list_styles(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [
                _decode("styles", r)
                for r in conn.execute("SELECT * FROM styles ORDER BY updated_at DESC, name").fetchall()
            ]

    def get_style(self, style_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _decode(
                "styles", conn.execute("SELECT * FROM styles WHERE id = ?", (style_id,)).fetchone()
            )

    def create_style(self, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("风格名称不能为空")
        style_id = (data.get("id") or _new_id("style")).strip()
        payload = {field: data.get(field, "") for field in STYLE_FIELDS}
        payload["name"] = name
        for key in ("color_palette", "reference_assets", "applicable_content_types", "source_files"):
            if payload.get(key) in ("", None):
                payload[key] = {} if key == "color_palette" else []
        if not payload.get("aspect_ratio"):
            payload["aspect_ratio"] = "9:16"
        payload = _encode("styles", payload)
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                f"INSERT INTO styles (id, {', '.join(payload)}, created_at, updated_at) "
                f"VALUES (?, {', '.join('?' for _ in payload)}, ?, ?)",
                (style_id, *payload.values(), ts, ts),
            )
        return self.get_style(style_id) or {}

    def update_style(self, style_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        payload = {k: v for k, v in data.items() if k in STYLE_FIELDS}
        if "name" in payload and not str(payload["name"]).strip():
            raise ValueError("风格名称不能为空")
        if not payload:
            return self.get_style(style_id)
        payload = _encode("styles", payload)
        assignments = ", ".join(f"{key} = ?" for key in payload)
        with self.connect() as conn:
            cur = conn.execute(
                f"UPDATE styles SET {assignments}, updated_at = ? WHERE id = ?",
                (*payload.values(), now_iso(), style_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_style(style_id)

    @staticmethod
    def _style_brief(conn: sqlite3.Connection, style_id: str | None) -> dict[str, Any] | None:
        if not style_id:
            return None
        row = conn.execute("SELECT id, name, aspect_ratio FROM styles WHERE id = ?", (style_id,)).fetchone()
        return dict(row) if row else None

    # ---------------- tasks ----------------

    def insert_task(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = _encode("tasks", task)
        with self.connect() as conn:
            conn.execute(
                f"INSERT INTO tasks (id, {', '.join(payload)}) VALUES (?, {', '.join('?' for _ in payload)})",
                (task["id"], *payload.values()),
            )
        return self.get_task(task["id"]) or task

    def update_task(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        payload = _encode("tasks", fields)
        assignments = ", ".join(f"{key} = ?" for key in payload)
        with self.connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", (*payload.values(), task_id))

    def mark_running(self, task_id: str, started_at: str | None = None) -> bool:
        """Move a PENDING task to RUNNING only if it is still PENDING.

        A cancel between create() and the executor coroutine therefore wins:
        the executor must not launch a process for an already-cancelled task.
        """
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE tasks SET status = 'RUNNING', started_at = ?"
                " WHERE id = ? AND status = 'PENDING'",
                (started_at or now_iso(), task_id),
            )
            return cur.rowcount == 1

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _decode("tasks", conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    def list_tasks(
        self, status: str | None = None, episode_id: str | None = None, kind: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if status:
            clauses.append("status = ?")
            args.append(status)
        if episode_id:
            clauses.append("episode_id = ?")
            args.append(episode_id)
        if kind:
            clauses.append("kind = ?")
            args.append(kind)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM tasks{where} ORDER BY created_at DESC LIMIT ?", (*args, limit)
            ).fetchall()
            return [_decode("tasks", r) for r in rows]

    def running_lock(self, lock_key: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _decode(
                "tasks",
                conn.execute(
                    "SELECT * FROM tasks WHERE lock_key = ? AND status = 'RUNNING'", (lock_key,)
                ).fetchone(),
            )

    def count_tasks(self, status: str) -> int:
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (status,)).fetchone()[0]

    def recover_stale_tasks(self) -> int:
        """Mark tasks left RUNNING by a previous server process as interrupted."""
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE tasks SET status = 'FAILED', finished_at = ?,"
                " error = COALESCE(error, '服务重启时任务仍在运行，已标记为中断')"
                " WHERE status = 'RUNNING'",
                (now_iso(),),
            )
            return cur.rowcount

_store: WorkspaceStore | None = None


def get_store() -> WorkspaceStore:
    global _store
    if _store is None:
        _store = WorkspaceStore()
    return _store
