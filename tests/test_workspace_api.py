from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import make_video_episode


@pytest.fixture()
def client(workspace, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(workspace.api, "_store", workspace.store)
    monkeypatch.setattr(workspace.api, "_runner", workspace.tasks.TaskRunner(workspace.store))
    return TestClient(workspace.api.app)


def test_health_and_overview(client: TestClient) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    created = client.post("/api/projects", json={"name": "测试项目"}).json()
    assert created["name"] == "测试项目"

    overview = client.get("/api/overview").json()
    assert overview["stats"]["projects"] == 1
    assert overview["stats"]["episodes"] == 0
    assert isinstance(overview["recent_tasks"], list)


def test_episode_endpoints(client: TestClient, workspace) -> None:
    created = make_video_episode(workspace)
    episode_id = created["episode"]["id"]
    for path in (
        f"/api/episodes/{episode_id}",
        f"/api/episodes/{episode_id}/content",
        f"/api/episodes/{episode_id}/storyboard",
        f"/api/episodes/{episode_id}/audio",
        f"/api/episodes/{episode_id}/assets",
        f"/api/episodes/{episode_id}/output",
        f"/api/episodes/{episode_id}/workflow",
    ):
        response = client.get(path)
        assert response.status_code == 200, path

    detail = client.get(f"/api/episodes/{episode_id}").json()
    assert detail["progress"]["percent"] == 100
    assert detail["review"]["status"] == "NOT_RUN"

    storyboard = client.get(f"/api/episodes/{episode_id}/storyboard").json()
    assert len(storyboard["segments"]) == 2
    assert storyboard["segments"][0]["source_exists"] is True


def test_missing_episode_returns_404(client: TestClient) -> None:
    response = client.get("/api/episodes/does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_media_range_and_traversal(client: TestClient, workspace) -> None:
    sample = workspace.root / "assets" / "sample.json"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text('{"ok": true}', encoding="utf-8")

    full = client.get("/api/media/assets/sample.json")
    assert full.status_code == 200
    ranged = client.get("/api/media/assets/sample.json", headers={"Range": "bytes=0-9"})
    assert ranged.status_code == 206
    assert ranged.headers["content-range"].startswith("bytes 0-9/")
    assert len(ranged.content) == 10

    traversal = client.get("/api/media/..%2F..%2Fetc%2Fpasswd")
    assert traversal.status_code == 403


def test_task_kinds_registry_is_restricted(client: TestClient) -> None:
    kinds = {k["key"]: k for k in client.get("/api/tasks/kinds").json()["kinds"]}
    assert "build.rebuild" in kinds
    assert "doctor.run" in kinds
    assert kinds["tts.synthesize"]["enabled"] is True
    assert kinds["tts.synthesize"]["blocked_reason"] is None
    assert "tts_mode" in kinds["tts.synthesize"]["params_schema"]["properties"]
    assert "voice_cast" in kinds["tts.synthesize"]["params_schema"]["properties"]
    assert "episode_id" in kinds["comfy.batch"]["params_schema"]["properties"]
    assert "audio_timeline" in kinds["build.rebuild"]["params_schema"]["properties"]
    assert "audio_timeline" in kinds["audio.qa"]["params_schema"]["properties"]
    assert kinds["static.check"]["enabled"] is True
    assert "shot_id" in kinds["static.check"]["params_schema"]["properties"]
    assert kinds["story.check"]["enabled"] is True
    assert "characters" in kinds["story.check"]["params_schema"]["properties"]
    assert "shots" in kinds["story.check"]["params_schema"]["properties"]
    assert kinds["package.build"]["enabled"] is True
    assert kinds["script.generate"]["enabled"] is True
    assert kinds["segments.build"]["enabled"] is True
    assert kinds["motion.plan"]["enabled"] is True
    assert kinds["motion.render"]["enabled"] is True
    assert kinds["audio.qa"]["enabled"] is True
    assert kinds["aesthetic.plan"]["enabled"] is True
    assert kinds["aesthetic.compare"]["enabled"] is True
    assert kinds["aesthetic.review"]["enabled"] is True
    assert kinds["quality.check"]["enabled"] is True
    assert kinds["review.accept"]["enabled"] is True
    assert kinds["review.reject"]["enabled"] is True
    assert "shell" not in kinds


def test_blocked_task_is_recorded_with_reason(client: TestClient) -> None:
    project = client.post("/api/projects", json={"name": "阻塞测试"}).json()
    episode = client.post(
        "/api/episodes",
        json={"project_id": project["id"], "number": 1, "title": "无素材", "track": "video"},
    ).json()
    task = client.post(
        "/api/tasks", json={"kind": "build.rebuild", "params": {"episode_id": episode["id"]}}
    ).json()
    assert task["status"] == "BLOCKED"
    assert "前置条件不满足" in task["error"]


def test_invalid_task_kind_rejected(client: TestClient) -> None:
    response = client.post("/api/tasks", json={"kind": "shell.exec", "params": {}})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_kind"


def test_extra_params_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/tasks", json={"kind": "doctor.run", "params": {"nope": 1}}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_params"


def test_style_revision_endpoint_versions_the_episode(client: TestClient) -> None:
    project = client.post("/api/projects", json={"name": "风格版本项目"}).json()
    ink = client.post("/api/styles", json={
        "name": "水墨", "preset_id": "ink_wash", "visual_language": "水墨"
    }).json()
    court = client.post("/api/styles", json={
        "name": "青绿", "preset_id": "court_green_fine_line", "visual_language": "工笔"
    }).json()
    episode = client.post("/api/episodes", json={
        "project_id": project["id"], "number": 1, "title": "风格版本期",
        "track": "video", "style_id": ink["id"],
    }).json()
    assert episode["style_snapshot"]["_style_lock"]["revision"] == 1

    updated = client.patch(f"/api/episodes/{episode['id']}", json={"style_id": court["id"]}).json()
    lock = updated["style_snapshot"]["_style_lock"]
    assert lock["style_id"] == court["id"]
    assert lock["preset_id"] == "court_green_fine_line"
    assert lock["revision"] == 2
    assert lock["history"][0]["style_id"] == ink["id"]


def test_workflow_exposes_real_package_static_aesthetic_motion_nodes(
        client: TestClient, workspace) -> None:
    created = make_video_episode(workspace)
    episode_id = created["episode"]["id"]
    data = client.get(f"/api/episodes/{episode_id}/workflow").json()
    nodes = {n["id"]: n for n in data["nodes"]}
    assert {"source", "package", "script", "storyboard", "static",
            "aesthetic", "images", "videos", "motion", "voice", "compose"} <= set(nodes)
    assert nodes["package"]["task_kind"] == "package.build"
    assert nodes["script"]["task_kind"] == "script.generate"
    assert nodes["static"]["task_kind"] == "static.check"
    assert nodes["aesthetic"]["task_kind"] == "aesthetic.plan"
    assert nodes["motion"]["task_kind"] == "motion.plan"
    assert "尚未参数化" not in (nodes["voice"].get("task_reason") or "")
