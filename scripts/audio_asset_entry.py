"""Build a manifest entry for a local audio file.

Computes the SHA-256 and the exact duration via ffprobe, then prints a JSON
object that can be pasted into ``assets/audio/manifest.json``. It never edits
the manifest itself: the registry is the single source of truth and an entry
must be reviewed before it becomes ``APPROVED``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STYLES = ("ink_wash", "court_green_fine_line", "shinkai_scenery", "ghibli_scenery")
PLATFORMS = ("wikimedia_commons", "youtube_studio", "freesound", "keynata",
             "incompetech", "local_curated")
KINDS = ("bgm", "ambience", "sfx")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration_ms(path: Path) -> int:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe not found; install FFmpeg or add it to PATH")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(f"ffprobe failed: {proc.stderr[-800:]}")
    try:
        seconds = float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read duration: {path}") from exc
    return int(round(seconds * 1000))


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_entry(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"file not found: {path}")
    asset_id = args.asset_id or _derive_id(path, args.type, args.source_platform)
    style = args.style
    tags = [t for t in (style, args.type, *args.tag) if t]
    return {
        "asset_id": asset_id,
        "name": args.name or path.stem.replace("_", " ").title(),
        "artist": args.artist,
        "source_platform": args.source_platform,
        "source_url": args.source_url,
        "style": style,
        "type": args.type,
        "path": _relative(path, Path(args.root)),
        "sha256": sha256(path),
        "duration_ms": duration_ms(path),
        "license": args.license,
        "commercial_allowed": args.commercial_allowed,
        "attribution_required": args.attribution_required,
        "attribution_text": args.attribution_text,
        "status": args.status,
        "default_gain_db": args.gain_db,
        "tags": tags,
    }


def _derive_id(path: Path, kind: str, platform: str) -> str:
    stem = path.stem.lower().replace(" ", "_").replace("-", "_")
    prefix = "amb" if kind == "ambience" else kind
    code = "".join(part[0] for part in platform.split("_"))[:3]
    return f"{prefix}_{code}_{stem}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--root", default=str(ROOT), help="project root for relative paths")
    parser.add_argument("--asset-id", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--artist", default="Unknown")
    parser.add_argument("--style", choices=STYLES, default="shinkai_scenery")
    parser.add_argument("--source-platform", choices=PLATFORMS, default="local_curated")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--license", default="UNVERIFIED")
    parser.add_argument("--commercial-allowed", dest="commercial_allowed",
                        action="store_true", default=True)
    parser.add_argument("--no-commercial", dest="commercial_allowed", action="store_false")
    parser.add_argument("--attribution-required", action="store_true", default=False)
    parser.add_argument("--attribution-text", default="")
    parser.add_argument("--status", choices=("APPROVED", "PENDING", "REJECTED"), default="PENDING")
    parser.add_argument("--gain-db", type=float, default=-16.0)
    parser.add_argument("--type", choices=KINDS, default="bgm")
    parser.add_argument("--tag", action="append", default=[], help="extra tag; repeatable")
    args = parser.parse_args()

    if args.attribution_required and not args.attribution_text:
        raise SystemExit("--attribution-required needs --attribution-text")
    if args.status == "APPROVED" and args.license == "UNVERIFIED":
        raise SystemExit("an APPROVED entry needs a verified --license")

    print(json.dumps(build_entry(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
