from __future__ import annotations

import json

from conftest import make_video_episode


def test_video_episode_state_comes_from_real_files(workspace) -> None:
    created = make_video_episode(workspace)
    view = workspace.discovery.analyze_episode(workspace.store, created["episode"])

    steps = {s["id"]: s for s in view["steps"]}
    assert steps["source"]["status"] == "PASS_VERIFIED"
    assert steps["storyboard"]["status"] == "PASS_VERIFIED"
    assert steps["images"]["detail"].startswith("1/1")
    assert steps["videos"]["detail"].startswith("1/1")
    assert steps["voice"]["status"] == "PASS_VERIFIED"
    assert steps["compose"]["status"] == "PASS_VERIFIED"
    assert steps["output"]["status"] == "PASS_VERIFIED"

    # No human review is recorded, so it must not be VERIFIED.
    assert steps["review"]["status"] == "NOT_RUN"
    assert view["status"] == "completed"
    assert view["progress"]["percent"] == 100
    assert view["final"]["sha_ok"] is True
    probe = view["final"]["probe"]
    video = next(s for s in probe["streams"] if s["type"] == "video")
    assert (video["width"], video["height"]) == (64, 64)


def test_current_manifest_is_marked_current(workspace) -> None:
    created = make_video_episode(workspace)
    view = workspace.discovery.analyze_episode(workspace.store, created["episode"])
    assert all(b["manifest_version"] == "current" for b in view["builds"])


def test_legacy_manifest_is_flagged(workspace) -> None:
    created = make_video_episode(workspace)
    episode = created["episode"]
    art = workspace.root / "artifacts" / "ep1"
    legacy = {
        "total_seconds": 0.3,
        "outputs": {"final": "artifacts/ep1/final.mp4", "final_sha256": None},
    }
    (art / "renders").mkdir(parents=True, exist_ok=True)
    (art / "renders" / "build_manifest.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    view = workspace.discovery.analyze_episode(workspace.store, episode)
    legacy_builds = [b for b in view["builds"] if b["manifest_version"] == "legacy"]
    assert len(legacy_builds) == 1
    assert legacy_builds[0]["font"] is None


def test_literary_episode_without_analysis_is_not_run(workspace) -> None:
    project = workspace.store.create_project({"name": "测试项目"})
    corpus = workspace.root / "corpus"
    corpus.mkdir()
    (corpus / "source_registry.json").write_text(
        json.dumps({"sources": [{"source_id": "src_test"}]}), encoding="utf-8"
    )
    episode = workspace.store.create_episode(
        {
            "project_id": project["id"],
            "number": 1,
            "title": "测试文学期",
            "track": "literary",
            "artifact_root": "corpus",
        }
    )
    view = workspace.discovery.analyze_episode(workspace.store, workspace.store.get_episode(episode["id"]))
    steps = {s["id"]: s for s in view["steps"]}
    assert view["kind"] == "literary"
    assert steps["analysis"]["status"] == "NOT_RUN"
    assert steps["script"]["status"] == "NOT_RUN"
    assert view["progress"]["percent"] < 100


def test_missing_artifact_root_never_invents_progress(workspace) -> None:
    project = workspace.store.create_project({"name": "空项目"})
    episode = workspace.store.create_episode(
        {"project_id": project["id"], "number": 1, "title": "无产物", "track": "video"}
    )
    view = workspace.discovery.analyze_episode(workspace.store, episode)
    assert view["artifact_root_exists"] is False
    assert view["status_label"] == "产物目录缺失"
    assert view["progress"]["percent"] == 0
    assert all(s["status"] == "NOT_RUN" for s in view["steps"])


def test_workflow_nodes_reference_real_paths(workspace) -> None:
    created = make_video_episode(workspace)
    view = workspace.discovery.analyze_episode(workspace.store, created["episode"])
    nodes = {n["id"]: n for n in view["workflow"]["nodes"]}
    assert set(nodes) >= {"source", "storyboard", "images", "voice", "compose", "output"}
    assert all(i["exists"] for i in nodes["source"]["outputs"])
    assert nodes["compose"]["task_kind"] == "build.rebuild"


def test_quality_fail_blocks_compose(workspace) -> None:
    import json

    created = make_video_episode(workspace)
    episode = created["episode"]
    build_dir = (
        workspace.root / "projects" / episode["project_id"] / "episodes" / episode["id"]
        / "renders" / "build-test"
    )
    (build_dir / "quality_report.json").write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
    view = workspace.discovery.analyze_episode(workspace.store, episode)
    steps = {s["id"]: s for s in view["steps"]}
    assert steps["compose"]["status"] == "FAILED"
    assert "质量检查" in steps["compose"]["detail"]
