"""Resolve shot assets with an explicit production type.

The extension is not the type: a FLUX keyframe is a still, a directory of Wan
PNG frames is an image sequence, and a rendered/pre-encoded file is a video.
Mixing these up is what makes a finished film fall back to stills after a Wan
run, so the type is decided from where the asset lives and how many frames it
has.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AssetKind = Literal["image", "image_sequence", "video"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_output(directory: Path, shot_id: str, suffix: str = ".png") -> Path | None:
    """ComfyUI increments the filename counter; always take the newest match."""
    if not directory.is_dir():
        return None
    matches = [p for p in directory.glob(f"{shot_id}_*{suffix}") if p.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda p: (p.stat().st_mtime, p.name))


def sequence_frames(directory: Path, shot_id: str) -> list[Path]:
    if not directory.is_dir():
        return []
    frames = [p for p in directory.glob(f"{shot_id}_*.png") if p.is_file()]
    return sorted(frames, key=lambda p: (p.name,))


@dataclass(frozen=True)
class ShotAsset:
    shot_id: str
    kind: AssetKind
    path: Path | None = None
    frames: tuple[Path, ...] = field(default_factory=tuple)
    sha256: str | None = None
    frame_count: int = 0

    @property
    def exists(self) -> bool:
        return bool(self.path and self.path.is_file()) or bool(self.frames)


def resolve_asset(project_root: Path, shot_id: str, *, allow_sequence: bool = True) -> ShotAsset | None:
    shots_dir = project_root / "shots" / shot_id
    clip = latest_output(shots_dir, shot_id, ".mp4")
    if clip is not None:
        return ShotAsset(shot_id=shot_id, kind="video", path=clip, sha256=sha256_file(clip))
    if allow_sequence:
        frames = sequence_frames(shots_dir, shot_id)
        if len(frames) >= 2:
            digest = hashlib.sha256()
            for frame in frames:
                digest.update(sha256_file(frame).encode("ascii"))
            return ShotAsset(shot_id=shot_id, kind="image_sequence", path=shots_dir,
                             frames=tuple(frames), sha256=digest.hexdigest(),
                             frame_count=len(frames))
    still = latest_output(project_root / "assets" / "keyframes" / shot_id, shot_id, ".png")
    if still is not None:
        return ShotAsset(shot_id=shot_id, kind="image", path=still, sha256=sha256_file(still))
    return None


def resolve_for_encoding(project_root: Path, shot_id: str) -> ShotAsset | None:
    """Prefer a Wan frame run that is newer than an existing encoded clip.

    Without this, the first encoded clip shadows every later Wan run and a
    regenerated shot silently keeps the old motion.
    """
    shots_dir = project_root / "shots" / shot_id
    frames = sequence_frames(shots_dir, shot_id)
    clip = latest_output(shots_dir, shot_id, ".mp4")
    if frames and len(frames) >= 2:
        newest = max(frame.stat().st_mtime for frame in frames)
        if clip is None or newest > clip.stat().st_mtime:
            import hashlib
            digest = hashlib.sha256()
            for frame in frames:
                digest.update(sha256_file(frame).encode("ascii"))
            return ShotAsset(shot_id=shot_id, kind="image_sequence", path=shots_dir,
                             frames=tuple(frames), sha256=digest.hexdigest(),
                             frame_count=len(frames))
    return resolve_asset(project_root, shot_id)


def resolve_all(project_root: Path, shot_ids: list[str]) -> dict[str, ShotAsset]:
    result: dict[str, ShotAsset] = {}
    for shot_id in shot_ids:
        asset = resolve_asset(project_root, shot_id)
        if asset is not None:
            result[shot_id] = asset
    return result
