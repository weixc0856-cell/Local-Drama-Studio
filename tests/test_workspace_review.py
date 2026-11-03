from __future__ import annotations

import asyncio
import json

import pytest

from conftest import make_video_episode


def _run_review(workspace, decision: str) -> dict:
    runner = workspace.tasks.TaskRunner(workspace.store)
    created = make_video_episode(workspace)

    async def scenario() -> dict:
        task = runner.create(
            decision,
            {"episode_id": created["episode"]["id"], "note": "人工看片结论"},
        )
        for _ in range(200):
            current = workspace.store.get_task(task["id"])
            if current["status"] not in ("PENDING", "RUNNING"):
                return current
            await asyncio.sleep(0.01)
        raise AssertionError("review task did not finish")

    return asyncio.run(scenario()), created


def test_review_accept_writes_and_reads(workspace) -> None:
    task, created = _run_review(workspace, "review.accept")
    assert task["status"] == "SUCCEEDED"
    path = (
        workspace.root / "projects" / created["episode"]["project_id"]
        / "episodes" / created["episode"]["id"] / "human_review.json"
    )
    assert path.is_file()
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["decision"] == "accept"

    view = workspace.discovery.analyze_episode(workspace.store, created["episode"])
    review = {s["id"]: s for s in view["steps"]}["review"]
    assert review["status"] == "PASS_VERIFIED"
    assert "通过" in review["detail"]


def test_review_reject_is_recorded(workspace) -> None:
    task, created = _run_review(workspace, "review.reject")
    assert task["status"] == "SUCCEEDED"
    view = workspace.discovery.analyze_episode(workspace.store, created["episode"])
    review = {s["id"]: s for s in view["steps"]}["review"]
    assert review["status"] == "FAILED"
    assert "拒绝" in review["detail"]


def test_review_requires_artifact_root(workspace) -> None:
    project = workspace.store.create_project({"name": "空项目"})
    episode = workspace.store.create_episode(
        {"project_id": project["id"], "number": 1, "title": "无产物", "track": "video"}
    )
    runner = workspace.tasks.TaskRunner(workspace.store)
    task = runner.create("review.accept", {"episode_id": episode["id"]})
    assert task["status"] == "BLOCKED"
    assert "产物目录" in task["error"]


def test_cancel_before_execution_prevents_launch(workspace) -> None:
    runner = workspace.tasks.TaskRunner(workspace.store)
    workspace.store.insert_task(
        {
            "id": "task_cancel",
            "kind": "doctor.run",
            "lock_key": "doctor",
            "status": "PENDING",
            "params": {},
            "result": {},
            "log_path": None,
            "created_at": workspace.tasks.now_iso(),
        }
    )

    async def scenario() -> dict:
        await runner.cancel("task_cancel")
        await runner._execute(
            "task_cancel",
            workspace.tasks.TASK_KINDS["doctor.run"],
            workspace.tasks.EmptyParams(),
        )
        return workspace.store.get_task("task_cancel")

    task = asyncio.run(scenario())
    assert task["status"] == "CANCELLED"
    assert not (workspace.tasks.LOG_DIR / "task_cancel.log").exists()
