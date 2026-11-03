r"""Fetch and verify the configured local font assets.

The OTF binaries (~58 MiB) are not stored in Git. This script reconstructs
them deterministically from the official Adobe GitHub releases recorded in
``assets/fonts/font_manifest.json`` and verifies both the archive SHA-256 and
each extracted OTF SHA-256.

    .venv\Scripts\python.exe scripts\fetch_fonts.py --check
    .venv\Scripts\python.exe scripts\fetch_fonts.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "fonts" / "font_manifest.json"
CACHE = ROOT / "logs" / "font_download"
USER_AGENT = "Local-Drama-Studio-font-fetch/1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing font manifest: {MANIFEST}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("fonts"):
        raise SystemExit(f"invalid font manifest: {MANIFEST}")
    return data


def expected_files(font: dict) -> list[dict]:
    return list(font.get("selected_weights") or [])


def missing_or_bad(font: dict) -> list[str]:
    problems: list[str] = []
    for item in expected_files(font):
        path = (ROOT / item["file"]).resolve()
        if not path.is_file():
            problems.append(f"missing {item['file']}")
        elif sha256(path) != item["sha256"]:
            problems.append(f"sha256 mismatch {item['file']}")
    return problems


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    print(f"download {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as fh:
        shutil.copyfileobj(response, fh)
    tmp.replace(target)


def extract(font: dict, archive: Path) -> None:
    wanted = {Path(item["file"]).name: item for item in expected_files(font)}
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        for basename, item in wanted.items():
            matches = [name for name in names if Path(name).name == basename]
            if not matches:
                raise SystemExit(f"{basename} not found in {archive.name}")
            target = (ROOT / item["file"]).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(matches[0]) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            actual = sha256(target)
            if actual != item["sha256"]:
                raise SystemExit(
                    f"sha256 mismatch after extraction: {target} expected {item['sha256']} got {actual}"
                )
            print(f"  wrote {item['file']}")
        license_names = [name for name in names if Path(name).name.upper() == "LICENSE.TXT"]
        if license_names:
            license_target = (ROOT / font["selected_weights"][0]["file"]).resolve().parent / "LICENSE.txt"
            if not license_target.is_file():
                with zf.open(license_names[0]) as src, license_target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                print(f"  wrote {license_target.relative_to(ROOT)}")


def ensure_font(font: dict, *, force: bool = False) -> None:
    problems = missing_or_bad(font)
    if not problems and not force:
        print(f"{font['asset_id']}: ok ({len(expected_files(font))} weights)")
        return
    if problems:
        print(f"{font['asset_id']}: {'; '.join(problems)}")
    archive_meta = font.get("archive") or {}
    url = archive_meta.get("url")
    if not url:
        raise SystemExit(f"{font['asset_id']}: manifest has no archive.url")
    archive = CACHE / archive_meta["file"]
    if force or not archive.is_file() or sha256(archive) != archive_meta.get("sha256"):
        if archive.is_file() and archive_meta.get("sha256") and sha256(archive) != archive_meta["sha256"]:
            archive.unlink()
        download(url, archive)
    actual = sha256(archive)
    expected = archive_meta.get("sha256")
    if expected and actual != expected:
        raise SystemExit(f"archive sha256 mismatch: {archive} expected {expected} got {actual}")
    extract(font, archive)
    remaining = missing_or_bad(font)
    if remaining:
        raise SystemExit(f"{font['asset_id']}: still incomplete: {'; '.join(remaining)}")
    print(f"{font['asset_id']}: ready")


def main() -> int:
    global ROOT, MANIFEST, CACHE
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report status without downloading")
    parser.add_argument("--force", action="store_true", help="re-download and re-extract")
    parser.add_argument("--root", type=Path, default=ROOT, help="project root (default: this repository)")
    args = parser.parse_args()

    ROOT = args.root.resolve()
    MANIFEST = ROOT / "assets" / "fonts" / "font_manifest.json"
    CACHE = ROOT / "logs" / "font_download"

    manifest = load_manifest()
    problems = 0
    for font in manifest["fonts"]:
        if args.check:
            issues = missing_or_bad(font)
            if issues:
                problems += 1
                print(f"{font['asset_id']}: {'; '.join(issues)}")
            else:
                print(f"{font['asset_id']}: ok")
            continue
        ensure_font(font, force=args.force)
    return 1 if args.check and problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
