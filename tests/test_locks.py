from __future__ import annotations

import json
import os

import pytest

from drama_studio.locks import FileLock, LockHeld


def test_lock_is_exclusive_and_releases(tmp_path) -> None:
    path = tmp_path / "locks" / "gpu.lock"
    first = FileLock(path, name="gpu").acquire()
    try:
        with pytest.raises(LockHeld):
            FileLock(path, name="gpu").acquire()
    finally:
        first.release()
    assert not path.exists()
    with FileLock(path, name="gpu"):
        assert path.is_file()
    assert not path.exists()


def test_stale_lock_is_reclaimed(tmp_path) -> None:
    path = tmp_path / "gpu.lock"
    path.write_text(
        json.dumps({"pid": 999999, "name": "gpu", "created_at": 0}), encoding="utf-8"
    )
    with FileLock(path, name="gpu"):
        assert path.is_file()
    assert not path.exists()


def test_current_process_lock_is_not_reclaimed(tmp_path) -> None:
    path = tmp_path / "gpu.lock"
    path.write_text(
        json.dumps({"pid": os.getpid(), "name": "gpu", "created_at": 0}), encoding="utf-8"
    )
    with pytest.raises(LockHeld):
        FileLock(path, name="gpu").acquire()
