"""Cross-process file locks for local production scripts.

The workspace has a SQLite single-flight index for tasks it launches. Scripts
that can be executed directly need the same protection so two processes never
drive the same GPU tenant at once.

The lock is a small JSON file created with ``O_EXCL``. A lock whose PID is no
longer alive is treated as stale and reclaimed once.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class LockError(RuntimeError):
    pass


class LockHeld(LockError):
    pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class FileLock:
    """A PID-aware exclusive lock file.

    ``stale_after_seconds`` is a second safety net for PID reuse or a crashed
    process on a platform where liveness cannot be checked.
    """

    def __init__(
        self,
        path: Path,
        *,
        name: str = "lock",
        stale_after_seconds: float = 12 * 60 * 60,
    ) -> None:
        self.path = Path(path)
        self.name = name
        self.stale_after_seconds = stale_after_seconds
        self._acquired = False

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _stale(self, data: dict) -> bool:
        if not data:
            # A lock created but not yet written is only stale after a grace period.
            try:
                return (time.time() - self.path.stat().st_mtime) > 5
            except OSError:
                return False
        try:
            pid = int(data.get("pid") or 0)
            created = float(data.get("created_at") or 0)
        except (TypeError, ValueError):
            return True
        if pid and not _pid_alive(pid):
            return True
        return bool(created) and (time.time() - created) > self.stale_after_seconds

    def acquire(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"pid": os.getpid(), "name": self.name, "created_at": time.time()},
            ensure_ascii=False,
        ).encode("utf-8")
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                data = self._read()
                if attempt == 0 and self._stale(data):
                    try:
                        self.path.unlink()
                    except OSError:
                        pass
                    continue
                holder = data.get("pid", "?")
                raise LockHeld(
                    f"{self.name} lock is held by pid {holder}: {self.path}"
                ) from None
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
            self._acquired = True
            return self
        raise LockHeld(f"could not acquire {self.name} lock: {self.path}")

    def release(self) -> None:
        if not self._acquired:
            return
        self._acquired = False
        try:
            if self._read().get("pid") == os.getpid():
                self.path.unlink()
        except OSError:
            pass

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, *exc: object) -> None:
        self.release()


@contextmanager
def file_lock(path: Path, *, name: str = "lock") -> Iterator[FileLock]:
    lock = FileLock(path, name=name)
    with lock:
        yield lock
