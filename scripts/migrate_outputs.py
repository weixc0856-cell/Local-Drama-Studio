r"""Move generated artifacts out of the repository into DRAMA_OUTPUT_ROOT.

Repo keeps code, config, docs, tests and small text manifests. This script
relocates the artifacts that were historically written inside the checkout:

    projects/                     -> <output>/projects/
    experiments/                  -> <output>/experiments/
    logs/                         -> <output>/logs/
    literary_intelligence/runs/   -> <output>/literary_intelligence/runs/
    assets/{keyframes,vertical,visual_style}/ -> <output>/assets/...
    config/style_packs/*/*/reference_board/candidates/ -> <output>/style_boards/*/*/
    debug.log                     -> <output>/logs/debug.log

Inputs stay in the repo: assets/audio (licensed/downloaded audio), assets/fonts,
workflows, config declarations and every tracked manifest.

Usage:  .venv\Scripts\python.exe scripts\migrate_outputs.py [--apply]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from drama_studio.paths import output_root, repo_root

MOVE_TREES = (
    ("projects", "projects"),
    ("experiments", "experiments"),
    ("logs", "logs"),
    ("literary_intelligence/runs", "literary_intelligence/runs"),
    ("assets/keyframes", "assets/keyframes"),
    ("assets/vertical", "assets/vertical"),
    ("assets/visual_style", "assets/visual_style"),
)

MOVE_FILES = (("debug.log", "logs/debug.log"),)


def plan() -> list[tuple[Path, Path]]:
    repo, out = repo_root(), output_root()
    pairs: list[tuple[Path, Path]] = []
    for src_rel, dst_rel in MOVE_TREES:
        src = repo / src_rel
        if src.is_dir():
            for child in sorted(src.iterdir()):
                pairs.append((child, out / dst_rel / child.name))
    for src_rel, dst_rel in MOVE_FILES:
        src = repo / src_rel
        if src.is_file():
            pairs.append((src, out / dst_rel))
    for board in sorted((repo / "config" / "style_packs").glob("*/*/reference_board/candidates")):
        group = board.parents[2].name
        name = board.parents[1].name
        pairs.append((board, out / "style_boards" / group / name / "candidates"))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually move (default: dry run)")
    args = parser.parse_args()
    pairs = plan()
    total = 0
    for src, dst in pairs:
        if not src.exists():
            continue  # already moved by an earlier run
        if dst.exists():
            if src.is_file() and dst.is_file():
                dst.unlink()  # logs are recreated; the repo copy is the latest
            else:
                raise SystemExit(f"target exists, refusing to merge: {dst}")
        size = sum(p.stat().st_size for p in src.rglob("*") if p.is_file()) if src.is_dir() else src.stat().st_size
        total += size
        print(f"{'MOVE' if args.apply else 'would move'} {src} -> {dst}  ({size / 1e6:.1f} MB)")
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and src.is_file():
                dst.unlink()
            try:
                shutil.move(str(src), str(dst))
            except PermissionError as exc:
                print(f"  skipped (locked by another process): {src} ({exc})")
    print(f"{len(pairs)} entries, {total / 1e9:.2f} GB")
    if not args.apply:
        print("dry run; pass --apply to move")


if __name__ == "__main__":
    main()
