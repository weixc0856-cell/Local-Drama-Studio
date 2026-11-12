"""Film workspace tasks are registered and path-scoped."""

from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.workspace import tasks
from drama_studio.workspace.tasks import TASK_KINDS


def test_all_film_task_kinds_are_registered() -> None:
    expected = {
        "film.keyframes", "film.wan", "film.timeline", "film.voice", "film.static",
        "film.clips", "film.motion", "film.assemble", "film.status", "film.qc",
    }
    assert expected <= set(TASK_KINDS)
    for key in expected:
        assert TASK_KINDS[key].params_model.model_json_schema()["type"] == "object"


def test_film_project_path_traversal_is_refused(tmp_path: Path) -> None:
    class Store:
        root = tmp_path

    params = tasks.FilmProjectParams(project_id="../escape")
    with pytest.raises(tasks.TaskError):
        tasks._film_dir(params, Store())


def test_film_argv_uses_the_film_cli(tmp_path: Path) -> None:
    params = tasks.FilmAssembleParams(project_id="p1", bgm_id="bgm_x")
    argv = tasks._film_argv(
        "assemble", params, ["--bgm-id", params.bgm_id])
    assert argv[1:4] == ["-m", "drama_studio", "film"]
    assert argv[4] == "assemble"
    assert "--project" in argv and "p1" in argv
