r"""Move superseded documentation out of the checkout.

Archived documents stay on this machine under
``<DRAMA_OUTPUT_ROOT>/archive/docs/<date>/`` together with a MANIFEST.json
(name, bytes, sha256, reason). The repository keeps only ``docs/ARCHIVE.md``
as the index.

    .venv\Scripts\python.exe scripts\archive_docs.py [--apply] [--date 2026-11-12]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

from drama_studio.paths import output_root, repo_root

ARCHIVE: dict[str, str] = {
    "ARCHITECTURE.md": "target design superseded by REPO_LAYOUT.md and the implemented layers",
    "TECH_STACK.md": "merged into ENVIRONMENT.md",
    "PRODUCTION_WORKFLOW.md": "merged into PRODUCTION_GUIDE.md",
    "PRODUCTION_PIPELINE_GUIDE.md": "merged into PRODUCTION_GUIDE.md",
    "PRODUCTION_CONFIG_GUIDE.md": "merged into PRODUCTION_GUIDE.md",
    "USER_GUIDE.md": "merged into GUIDE.md",
    "DEVELOPER_GUIDE.md": "merged into GUIDE.md",
    "TROUBLESHOOTING.md": "merged into GUIDE.md",
    "VISUAL_STYLE_SPEC.md": "merged into VISUAL_STYLE.md",
    "VISUAL_STYLE_ENGINE.md": "merged into VISUAL_STYLE.md",
    "STYLE_BOARD_STATUS.md": "merged into VISUAL_STYLE.md",
    "SHINKAI_STYLE_NOTES.md": "merged into VISUAL_STYLE.md",
    "SONG_AESTHETIC_STUDY.md": "merged into VISUAL_STYLE.md",
    "SURREALISM_STYLE_NOTES.md": "merged into VISUAL_STYLE.md",
    "XUANJI_STYLE_NOTES.md": "merged into VISUAL_STYLE.md",
    "NEO_CHINESE_DIRECTION.md": "merged into VISUAL_STYLE.md",
    "AUDIO_ASSET_STRATEGY.md": "merged into AUDIO_AND_LICENSING.md",
    "ASSET_AND_LICENSE_REGISTRY.md": "merged into AUDIO_AND_LICENSING.md",
    "PLATFORM_PUBLISHING_SPEC.md": "merged into PLATFORM_PUBLISHING.md",
    "PLATFORM_COMFORT_ZONE.md": "merged into PLATFORM_PUBLISHING.md",
    "PRODUCTION_CAPABILITY.md": "merged into ROADMAP.md (capability section)",
    "CONTENT_PACKS.md": "merged into CONTENT_SPEC.md (content pack boundary)",
    "REQUIREMENT_TRACEABILITY.md": "historical governance matrix; superseded by PRD status tables",
    "PRD_CHANGELOG.md": "historical changelog; PRD keeps the current state",
    "M0_VISUAL_FAILURE_AUDIT.md": "one-off audit report",
    "MODEL_UPGRADE_POC.md": "historical model upgrade POC; decisions live in DECISIONS.md",
    "ENHANCEMENT_AB_REPORT.md": "one-off A/B report",
    "VIDEO_ENHANCEMENT_PLAN.md": "plan not executed; decisions live in DECISIONS.md/ROADMAP.md",
    "FRONTEND_DESIGN.md": "historical frontend design; UI is implemented",
    "FRONTEND_PLAN.md": "historical frontend plan; UI is implemented",
    "REFERENCE_STUDY.md": "reference-film study notes, study material only",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    source = repo_root() / "docs"
    target = output_root() / "archive" / "docs" / args.date
    moved: list[dict[str, object]] = []
    for name, reason in ARCHIVE.items():
        src = source / name
        if not src.is_file():
            continue
        moved.append({
            "name": name,
            "bytes": src.stat().st_size,
            "sha256": sha256(src),
            "reason": reason,
            "path": str(target / name),
        })
        print(f"{'archive' if args.apply else 'would archive'} {name}  ({reason})")
        if args.apply:
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target / name))

    if args.apply:
        manifest = target / "MANIFEST.json"
        manifest.write_text(json.dumps({
            "archived_on": args.date,
            "note": "Archived documents are local-only and are not part of the remote repository.",
            "files": moved,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(moved)} files archived to {target}")
    else:
        print(f"{len(moved)} files would be archived to {target}")


if __name__ == "__main__":
    main()
