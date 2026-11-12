from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.domain.style.lock import (
    StyleLockError,
    assert_style_request,
    locked_style_id,
    style_sha256,
)
from drama_studio.infrastructure.storage.store import WorkspaceStore


def _store(tmp_path: Path) -> WorkspaceStore:
    return WorkspaceStore(root=tmp_path, db_path=tmp_path / "workspace.db")


def _style(store: WorkspaceStore, style_id: str, name: str) -> dict:
    return store.create_style({
        "id": style_id,
        "name": name,
        "preset_id": style_id,
        "visual_language": "测试视觉语言",
        "aspect_ratio": "9:16",
    })


def _episode(store: WorkspaceStore, project_id: str, style_id: str) -> dict:
    return store.create_episode({
        "project_id": project_id,
        "number": 1,
        "title": "风格锁定测试",
        "track": "video",
        "artifact_root": "artifacts/ep1",
        "style_id": style_id,
    })


def test_create_episode_locks_style_hash_and_revision(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    snapshot = episode["style_snapshot"]
    lock = snapshot["_style_lock"]
    assert lock["style_id"] == "ink_wash"
    assert lock["preset_id"] == "ink_wash"
    assert lock["revision"] == 1
    assert lock["history"] == []
    assert lock["sha256"] == style_sha256(snapshot)
    assert locked_style_id(episode) == "ink_wash"


def test_same_style_update_does_not_create_a_revision(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    before = episode["style_snapshot"]["_style_lock"]
    updated = store.update_episode(episode["id"], {"style_id": "ink_wash"})
    after = updated["style_snapshot"]["_style_lock"]
    assert after["revision"] == 1
    assert after["history"] == []
    assert after["sha256"] == before["sha256"]


def test_style_change_creates_a_new_revision_and_preserves_history(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    _style(store, "court_green_fine_line", "青绿")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    old_sha = episode["style_snapshot"]["_style_lock"]["sha256"]
    updated = store.update_episode(episode["id"], {"style_id": "court_green_fine_line"})
    lock = updated["style_snapshot"]["_style_lock"]
    assert lock["style_id"] == "court_green_fine_line"
    assert lock["revision"] == 2
    assert len(lock["history"]) == 1
    assert lock["history"][0]["style_id"] == "ink_wash"
    assert lock["history"][0]["sha256"] == old_sha
    assert lock["history"][0]["revision"] == 1


def test_task_style_override_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    _style(store, "court_green_fine_line", "青绿")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    assert assert_style_request(episode, "ink_wash") == "ink_wash"
    with pytest.raises(StyleLockError, match="override forbidden"):
        assert_style_request(episode, "court_green_fine_line")


def test_snapshot_without_lock_gets_one_on_update(tmp_path: Path) -> None:
    store = _store(tmp_path)
    style = store.create_style({"id": "ink_wash", "name": "水墨", "preset_id": "ink_wash"})
    project = store.create_project({"name": "项目"})
    # Simulate a legacy episode row whose snapshot predates the lock.
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO episodes (id, project_id, number, title, track, artifact_root,"
            " style_id, style_snapshot, notes, origin, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ep_legacy", project["id"], 2, "旧期", "video", "artifacts/ep2",
             "ink_wash", '{"id": "ink_wash", "name": "水墨"}', "", "user",
             "2026-11-04T00:00:00+00:00", "2026-11-04T00:00:00+00:00"),
        )
    legacy = store.get_episode("ep_legacy")
    assert legacy["style_snapshot"].get("_style_lock") is None
    updated = store.update_episode("ep_legacy", {"style_id": "ink_wash"})
    lock = updated["style_snapshot"]["_style_lock"]
    assert lock["revision"] == 2  # legacy snapshot is treated as revision 1
    assert lock["history"][0]["style_id"] == "ink_wash"
    assert style["id"] == "ink_wash"


def test_task_helper_surfaces_style_lock_as_task_error(tmp_path: Path) -> None:
    from drama_studio.application.operations.tasks import TaskError, _locked_style

    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    _style(store, "court_green_fine_line", "青绿")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    assert _locked_style(episode) == "ink_wash"
    with pytest.raises(TaskError, match="style override forbidden"):
        _locked_style(episode, "court_green_fine_line")


def test_discovery_exposes_style_lock(tmp_path: Path) -> None:
    from drama_studio.infrastructure.storage.discovery import _style_view

    store = _store(tmp_path)
    _style(store, "ink_wash", "水墨")
    project = store.create_project({"name": "项目"})
    episode = _episode(store, project["id"], "ink_wash")
    view = _style_view(store, episode)
    assert view["revision"] == 1
    assert view["sha256"]
    assert view["override_allowed"] is False
