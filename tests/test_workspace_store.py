from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.infrastructure.storage.store import WorkspaceStore, now_iso


def make_store(tmp_path: Path) -> WorkspaceStore:
    return WorkspaceStore(root=tmp_path, db_path=tmp_path / "workspace.db")


def test_workspace_starts_empty(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    assert store.list_projects() == []
    assert store.list_episodes() == []
    assert store.list_styles() == []


def test_project_episode_style_roundtrip(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    project = store.create_project({"name": "测试系列", "aspect_ratio": "9:16"})
    assert project["name"] == "测试系列"
    assert project["episode_count"] == 0

    style = store.create_style({"name": "测试风格", "aspect_ratio": "9:16"})
    episode = store.create_episode(
        {
            "project_id": project["id"],
            "number": 1,
            "title": "第一期",
            "track": "video",
            "style_id": style["id"],
        }
    )
    assert episode["style_snapshot"]["name"] == "测试风格"

    # Editing the global style must not mutate an existing episode snapshot.
    store.update_style(style["id"], {"name": "改名后的风格"})
    refreshed = store.get_episode(episode["id"])
    assert refreshed is not None
    assert refreshed["style_snapshot"]["name"] == "测试风格"


def test_duplicate_episode_number_rejected(tmp_path: Path) -> None:
    import sqlite3

    store = make_store(tmp_path)
    project = store.create_project({"name": "P"})
    store.create_episode({"project_id": project["id"], "number": 1, "title": "A"})
    with pytest.raises(sqlite3.IntegrityError):
        store.create_episode({"project_id": project["id"], "number": 1, "title": "B"})


def test_only_one_running_task_per_lock(tmp_path: Path) -> None:
    import sqlite3

    store = make_store(tmp_path)
    base = {
        "kind": "build.rebuild",
        "lock_key": "build:ep",
        "status": "RUNNING",
        "params": {},
        "result": {},
        "log_path": None,
        "created_at": now_iso(),
    }
    store.insert_task({**base, "id": "task_a"})
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_task({**base, "id": "task_b"})
    # A finished task on the same lock key is fine.
    store.update_task("task_a", status="SUCCEEDED", finished_at=now_iso())
    store.insert_task({**base, "id": "task_c"})
    assert store.running_lock("build:ep")["id"] == "task_c"


def test_recover_stale_running_tasks(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    base = {
        "kind": "doctor.run",
        "lock_key": "doctor",
        "params": {},
        "result": {},
        "log_path": None,
        "created_at": now_iso(),
    }
    store.insert_task({**base, "id": "task_x", "status": "RUNNING"})
    assert store.recover_stale_tasks() == 1
    task = store.get_task("task_x")
    assert task["status"] == "FAILED"
    assert "中断" in task["error"]


def test_mark_running_only_from_pending(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.insert_task(
        {
            "id": "task_m",
            "kind": "doctor.run",
            "lock_key": "doctor",
            "status": "PENDING",
            "params": {},
            "result": {},
            "log_path": None,
            "created_at": now_iso(),
        }
    )
    assert store.mark_running("task_m", now_iso()) is True
    assert store.mark_running("task_m", now_iso()) is False

    store.insert_task(
        {
            "id": "task_c",
            "kind": "doctor.run",
            "lock_key": "doctor2",
            "status": "CANCELLED",
            "params": {},
            "result": {},
            "log_path": None,
            "created_at": now_iso(),
        }
    )
    assert store.mark_running("task_c", now_iso()) is False
