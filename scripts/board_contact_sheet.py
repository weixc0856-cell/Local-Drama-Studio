"""Compose the latest reference-board candidates into one contact sheet.

    .venv\\Scripts\\python.exe scripts/board_contact_sheet.py --style oriental.modern_chinese

Each candidate directory (`candidates/01`, `02`, ...) contributes its newest PNG,
so re-renders do not mix versions. Output defaults to the board's own
candidates/contact_sheet.png; pass --out for another location.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from drama_studio.config import find_project_root
from drama_studio.domain.style import get_pack, packs_root


def latest_images(candidates: Path, limit: int) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    for directory in sorted(candidates.iterdir()):
        if not directory.is_dir() or not directory.name.isdigit():
            continue
        images = sorted(directory.glob("*.png"), key=lambda path: path.stat().st_mtime)
        if images:
            items.append((directory.name, images[-1]))
    return items[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--width", type=int, default=288)
    args = parser.parse_args()

    root = find_project_root()
    pack = get_pack(root, args.style)
    candidates = packs_root(root) / pack.identity.group / args.style.split(".")[1] / "reference_board" / "candidates"
    images = latest_images(candidates, limit=args.columns * 3)
    if not images:
        raise SystemExit(f"no candidate images under {candidates}")

    thumbs = []
    for label, path in images:
        image = Image.open(path).convert("RGB")
        height = round(image.height * args.width / image.width)
        image = image.resize((args.width, height), Image.LANCZOS)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 34, 22), fill=(0, 0, 0))
        draw.text((7, 4), label, fill=(255, 255, 255))
        thumbs.append(image)

    columns = min(args.columns, len(thumbs))
    rows = (len(thumbs) + columns - 1) // columns
    cell_h = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (columns * args.width, rows * cell_h), (247, 246, 242))
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % columns) * args.width, (index // columns) * cell_h))

    out = args.out or (candidates / "contact_sheet.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"{out} ({len(thumbs)} images)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
