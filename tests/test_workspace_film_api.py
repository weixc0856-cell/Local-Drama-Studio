from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from drama_studio.workspace import api, film_api


def _shot(shot_id: str, prev: str | None, nxt: str | None) -> dict:
    return {
        "shot_id": shot_id,
        "scene_id": "SC01",
        "narration_ids": ["N001"] if shot_id == "S01" else ["N002"],
        "duration_seconds": 6.0,
        "shot_size": "ws",
        "camera": {"move": "static", "angle": "eye", "lens_mm": 35, "dof": "deep"},
        "layers": {"foreground": "reeds", "midground": "river", "background": "mountains"},
        "motion": {"primary": "water_drift", "secondary": []},
        "continuity": {
            "previous_shot": prev,
            "next_shot": nxt,
            "lighting": "dawn",
            "environment": "river_valley",
            "character_state": "none",
            "motion_direction": "static",
        },
        "generation": {"image_model": "flux3", "video_model": "wan2.2_ti2v_5b", "status": "planned"},
    }


def make_film_project(root: Path, project_id: str = "demo_film") -> Path:
    directory = root / "projects" / project_id
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(json.dumps({
        "project_id": project_id,
        "title": "测试短片",
        "aspect_ratio": "9:16",
        "target_duration_seconds": 12,
        "visual": {"style_id": "oriental.ink_wash", "style_version": "1.0.0"},
    }, ensure_ascii=False), encoding="utf-8")
    (directory / "narration.json").write_text(json.dumps({
        "project_id": project_id,
        "segments": [
            {"id": "N001", "text": "白日依山尽"},
            {"id": "N002", "text": "黄河入海流"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (directory / "storyboard.json").write_text(json.dumps({
        "project_id": project_id,
        "shots": [_shot("S01", None, "S02"), _shot("S02", "S01", None)],
    }, ensure_ascii=False), encoding="utf-8")
    return directory


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(film_api, "_root", lambda: tmp_path)
    return TestClient(api.app)


def test_lists_projects_from_disk(client: TestClient, tmp_path: Path) -> None:
    make_film_project(tmp_path)
    (tmp_path / "projects" / "empty_dir").mkdir()

    payload = client.get("/api/film/projects").json()
    assert [item["project_id"] for item in payload["projects"]] == ["demo_film"]
    project = payload["projects"][0]
    assert project["shots"] == 2
    assert project["narration"] == 2
    assert project["stages"]["keyframes"] == "0/2"
    assert project["stages"]["voice"] == "0/2"
    assert project["cover"] is None
    assert project["style_id"] == "oriental.ink_wash"


def test_project_detail_returns_storyboard_and_validation(client: TestClient, tmp_path: Path) -> None:
    make_film_project(tmp_path)
    detail = client.get("/api/film/projects/demo_film").json()
    assert detail["meta"]["title"] == "测试短片"
    assert [shot["shot_id"] for shot in detail["storyboard"]["shots"]] == ["S01", "S02"]
    assert len(detail["narration"]["segments"]) == 2
    assert detail["assets"]["S01"] == {"keyframe": None, "clip": None, "kind": None, "frames": 0}
    # No visual_bible.yaml in this fixture: validation reports it, the endpoint still answers.
    assert detail["validation"]["ok"] is False
    assert any(issue["code"] == "bible_missing" for issue in detail["validation"]["issues"])


def test_detail_404_for_unknown_project(client: TestClient) -> None:
    assert client.get("/api/film/projects/nope").status_code == 404


def test_patch_shot_writes_validated_storyboard(client: TestClient, tmp_path: Path) -> None:
    directory = make_film_project(tmp_path)
    response = client.patch("/api/film/projects/demo_film/storyboard/S01", json={
        "duration_seconds": 7.5,
        "camera_move": "crane",
        "lens_mm": 50,
        "motion_primary": "camera_descent",
        "secondary": ["cloud_drift", "water_ripple"],
        "keyframe_note": "painted moon upper right",
    })
    assert response.status_code == 200, response.text
    shot = response.json()["shot"]
    assert shot["duration_seconds"] == 7.5
    assert shot["camera"]["move"] == "crane"
    assert shot["camera"]["lens_mm"] == 50
    assert shot["motion"]["secondary"] == ["cloud_drift", "water_ripple"]
    assert shot["continuity"]["next_shot"] == "S02"

    written = json.loads((directory / "storyboard.json").read_text(encoding="utf-8"))
    assert written["shots"][0]["duration_seconds"] == 7.5
    assert written["shots"][1]["duration_seconds"] == 6.0


def test_patch_rejects_invalid_shot_without_writing(client: TestClient, tmp_path: Path) -> None:
    directory = make_film_project(tmp_path)
    before = (directory / "storyboard.json").read_text(encoding="utf-8")

    too_long = client.patch("/api/film/projects/demo_film/storyboard/S01", json={"duration_seconds": 40})
    assert too_long.status_code == 422
    assert (directory / "storyboard.json").read_text(encoding="utf-8") == before

    unknown_field = client.patch("/api/film/projects/demo_film/storyboard/S01", json={"nope": 1})
    assert unknown_field.status_code == 422

    missing_shot = client.patch("/api/film/projects/demo_film/storyboard/S09", json={"duration_seconds": 5})
    assert missing_shot.status_code == 404


def test_project_id_cannot_escape_projects_dir(client: TestClient, tmp_path: Path) -> None:
    make_film_project(tmp_path)
    for encoded in ("%2e%2e", "..%2f.."):
        response = client.get(f"/api/film/projects/{encoded}")
        assert response.status_code == 404, encoded
    response = client.patch("/api/film/projects/%2e%2e/storyboard/S01", json={"duration_seconds": 5})
    assert response.status_code == 404


def test_style_pack_endpoint_reads_registry() -> None:
    client = TestClient(api.app)
    payload = client.get("/api/film/styles/packs").json()
    packs = payload["packs"]
    assert len(packs) >= 12
    ids = {pack["id"] for pack in packs}
    assert "oriental.ink_wash" in ids
    assert "oriental.modern_chinese" in ids
    detail = client.get("/api/film/styles/packs/oriental.ink_wash").json()
    assert detail["pack"]["identity"]["id"] == "oriental.ink_wash"
    assert client.get("/api/film/styles/packs/nope.style").status_code == 404


def test_status_endpoint_derives_from_files(client: TestClient, tmp_path: Path) -> None:
    make_film_project(tmp_path)
    response = client.get("/api/film/projects/demo_film/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo_film"
    assert payload["overall"] == "planned"
    assert payload["counts"]["keyframes"] == 0
