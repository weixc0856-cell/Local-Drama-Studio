"""Episode-level style lock.

The episode's ``style_snapshot`` is the authoritative visual style for every
downstream artifact. This module adds a small, self-describing lock record
inside that JSON snapshot so a build can be traced to one style id and hash
without a second database table.

Changing a style is a new revision: the previous lock record is appended to
``history`` and the revision increments. Historical build directories and
manifests are never rewritten.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

LOCK_KEY = "_style_lock"


class StyleLockError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def style_payload(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """Snapshot without the lock metadata; this is what the hash covers."""
    data = dict(snapshot or {})
    data.pop(LOCK_KEY, None)
    return data


def style_sha256(snapshot: dict[str, Any] | None) -> str:
    return hashlib.sha256(_canonical(style_payload(snapshot)).encode("utf-8")).hexdigest()


def locked_style_id(episode: dict[str, Any] | None) -> str | None:
    if not episode:
        return None
    lock = (episode.get("style_snapshot") or {}).get(LOCK_KEY) or {}
    return str(lock.get("style_id") or episode.get("style_id") or "").strip() or None


def locked_preset_id(episode: dict[str, Any] | None) -> str | None:
    """The YAML preset id used by motion/aesthetic tasks, if mapped."""
    if not episode:
        return None
    snapshot = episode.get("style_snapshot") or {}
    lock = snapshot.get(LOCK_KEY) or {}
    return str(
        lock.get("preset_id") or snapshot.get("preset_id") or ""
    ).strip() or None


def lock_record(episode: dict[str, Any] | None) -> dict[str, Any]:
    snapshot = (episode or {}).get("style_snapshot") or {}
    lock = snapshot.get(LOCK_KEY) or {}
    if lock:
        return lock
    style_id = (episode or {}).get("style_id") or snapshot.get("id")
    return {
        "style_id": style_id,
        "preset_id": snapshot.get("preset_id"),
        "sha256": style_sha256(snapshot),
        "revision": 1,
        "history": [],
        "locked_at": None,
    }


def attach_lock(
    snapshot: dict[str, Any] | None,
    *,
    style_id: str | None = None,
    preset_id: str | None = None,
    previous: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Return a snapshot with an incremented lock record.

    ``previous`` is the old episode snapshot. If its payload hash equals the
    new payload, the existing lock is preserved rather than rewritten.
    """
    new_snapshot = style_payload(snapshot)
    new_sha = style_sha256(new_snapshot)
    chosen_id = str(style_id or new_snapshot.get("id") or "").strip() or None
    chosen_preset = str(
        preset_id or new_snapshot.get("preset_id") or ""
    ).strip() or None
    old_lock = (previous or {}).get(LOCK_KEY) or {}
    old_sha = old_lock.get("sha256") or style_sha256(previous)
    if (old_lock and old_sha == new_sha and old_lock.get("style_id") == chosen_id
            and old_lock.get("preset_id") == chosen_preset):
        new_snapshot[LOCK_KEY] = old_lock
        return new_snapshot
    old_revision = int(old_lock.get("revision") or (1 if previous else 0))
    history = list(old_lock.get("history") or [])
    if old_lock or previous:
        history.append({
            "style_id": old_lock.get("style_id") or (previous or {}).get("id")
            or (previous or {}).get("style_id"),
            "preset_id": old_lock.get("preset_id") or (previous or {}).get("preset_id"),
            "sha256": old_sha,
            "revision": old_revision or 1,
            "replaced_at": now or _now(),
        })
    new_snapshot[LOCK_KEY] = {
        "style_id": chosen_id,
        "preset_id": chosen_preset,
        "sha256": new_sha,
        "revision": (old_revision + 1) if (old_lock or previous) else 1,
        "history": history,
        "locked_at": now or _now(),
    }
    return new_snapshot


def assert_style_request(episode: dict[str, Any] | None, requested: str | None) -> str | None:
    """Reject a task-level style override that differs from the episode lock.

    Returns the YAML preset id when the episode is mapped, otherwise the
    database style id. Existing unmapped styles remain usable for migration.
    """
    locked = locked_preset_id(episode) or locked_style_id(episode)
    if requested and locked and requested != locked:
        raise StyleLockError(
            f"style override forbidden: episode is locked to {locked!r}, "
            f"task requested {requested!r}; change the episode style revision instead")
    return locked or requested


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
