r"""Fail when the checkout looks like an artifact store.

The remote repository tracks the development pipeline only (code, config,
docs, tests, workflows and small text manifests). Generated media lives in
DRAMA_OUTPUT_ROOT. This guard runs in CI and locally:

    .venv\Scripts\python.exe scripts/check_repo_hygiene.py

Rules:
1. No tracked media/model binaries (png/jpg/mp4/wav/mp3/otf/gguf/...).
2. No tracked file larger than MAX_BYTES.
3. The output root must not resolve inside the checkout.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from drama_studio.paths import output_root, repo_root

MEDIA_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".wav", ".mp3", ".m4a", ".flac", ".ogg",
    ".mp4", ".mov", ".webm", ".avi", ".mkv",
    ".otf", ".ttf", ".woff", ".woff2",
    ".gguf", ".safetensors", ".ckpt", ".pth", ".onnx", ".zip", ".7z",
}
MAX_BYTES = 512 * 1024


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True, capture_output=True,
    ).stdout
    return [root / name.decode("utf-8") for name in out.split(b"\x00") if name]


def main() -> int:
    root = repo_root()
    problems: list[str] = []

    for path in tracked_files(root):
        if path.suffix.lower() in MEDIA_SUFFIXES:
            problems.append(f"tracked media file: {path.relative_to(root)}")
        if path.is_file() and path.stat().st_size > MAX_BYTES:
            problems.append(f"tracked file over {MAX_BYTES // 1024} KiB: "
                            f"{path.relative_to(root)} ({path.stat().st_size // 1024} KiB)")

    try:
        output_root().relative_to(root.resolve())
        problems.append(f"output root is inside the checkout: {output_root()}")
    except ValueError:
        pass

    if problems:
        print("repo hygiene failed:")
        for item in problems:
            print(" -", item)
        return 1
    print(f"repo hygiene ok: {len(tracked_files(root))} tracked files, "
          f"output root {output_root()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
