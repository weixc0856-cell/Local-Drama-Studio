"""Resolve the newest generated asset for a shot."""

from __future__ import annotations

from pathlib import Path


def latest_output(directory: Path, shot_id: str, suffix: str = ".png") -> Path | None:
    """ComfyUI increments the filename counter; always take the newest match."""
    if not directory.is_dir():
        return None
    matches = [p for p in directory.glob(f"{shot_id}_*{suffix}") if p.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda p: (p.stat().st_mtime, p.name))
