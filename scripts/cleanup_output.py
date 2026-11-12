r"""Clean temporary files inside the output root (never the repository).

Safe defaults: browser-profile caches captured during UI review, empty log
files, old workspace DB backups, and OS/Python caches. Project renders,
experiments, style boards, audio and archives are never touched.

    .venv\Scripts\python.exe scripts\cleanup_output.py            # dry run
    .venv\Scripts\python.exe scripts\cleanup_output.py --apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from drama_studio.paths import output_root

# Directories that are caches, not evidence. Relative to the output root.
TEMP_DIR_GLOBS = (
    "logs/review/edge-profile",
    "logs/review/prof_*",
    "**/__pycache__",
)

# Files that carry no information once the run is over.
TEMP_FILE_GLOBS = (
    "logs/workspace.db.bak-*",
    "**/*.tmp",
    "**/*.part",
    "**/*.partial",
    "**/*.crdownload",
    "**/Thumbs.db",
    "**/desktop.ini",
    "**/.DS_Store",
)

# Empty logs are failed-run leftovers; keep the active ComfyUI log path.
EMPTY_LOG_GLOBS = ("logs/**/*.log", "logs/*.log")
KEEP_EMPTY = {"logs/comfyui.log"}


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def collect(root: Path) -> list[tuple[Path, int, str]]:
    found: dict[Path, tuple[int, str]] = {}
    for pattern in TEMP_DIR_GLOBS:
        for path in root.glob(pattern):
            if path.is_dir():
                found[path.resolve()] = (size_of(path), "temp directory")
    for pattern in TEMP_FILE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                found[path.resolve()] = (path.stat().st_size, "temp file")
    for pattern in EMPTY_LOG_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file() or path.stat().st_size:
                continue
            rel = path.resolve().relative_to(root.resolve()).as_posix()
            if rel in KEEP_EMPTY:
                continue
            found[path.resolve()] = (0, "empty log")
    return sorted(((p, s, why) for p, (s, why) in found.items()), key=lambda item: -item[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="delete (default: dry run)")
    args = parser.parse_args()

    root = output_root()
    if not root.is_dir():
        raise SystemExit(f"output root does not exist: {root}")

    items = collect(root)
    total = sum(size for _, size, _ in items)
    for path, size, why in items:
        rel = path.relative_to(root).as_posix()
        print(f"{'delete' if args.apply else 'would delete'} {rel}  ({size / 1e6:.1f} MB, {why})")
        if args.apply:
            if not path.exists():
                continue  # removed together with a parent directory
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    print(f"{len(items)} entries, {total / 1e6:.1f} MB")
    if not args.apply:
        print("dry run; pass --apply to delete")


if __name__ == "__main__":
    main()
