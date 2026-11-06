"""Generate candidate reference-board images for one style pack (not approved).

The board is a human-reviewed asset: this script only produces candidates and a
manifest marked PENDING_REVIEW. Images stay local (ignored by Git).

    .venv\\Scripts\\python.exe scripts\\gen_reference_board.py --style oriental.ink_wash --limit 12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from drama_studio.config import find_project_root
from drama_studio.style_engine import compile_image_prompt, get_pack, packs_root

SUBJECTS = [
    "distant mountain ranges above a wide river",
    "a lone fishing boat on a calm river at dawn",
    "a misty valley with layered peaks",
    "an old pine growing from a cliff rock",
    "a waterfall descending between dark rocks",
    "a full moon over still water and reeds",
    "a wooden pavilion in light rain",
    "an empty riverbank with reeds and stones",
    "lotus leaves floating on a quiet pond",
    "bamboo grove in thin mist",
    "snow-covered peaks under pale sky",
    "spring riverbank with sparse blossom branches",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--seed-base", type=int, default=5100)
    args = parser.parse_args()

    root = find_project_root()
    pack = get_pack(root, args.style)
    directory = packs_root(root) / pack.identity.group / args.style.split(".")[1] / "reference_board"
    candidates = directory / "candidates"
    params_dir = candidates / "params"
    params_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for index, subject in enumerate(SUBJECTS[: args.limit], start=1):
        prompt = compile_image_prompt(
            pack, subject=subject, layers={}, camera_move="static",
            extra_note="reference board sample, no characters",
        )
        params = {
            "positive_prompt": prompt,
            "seed": args.seed_base + index,
            "width": 576,
            "height": 1024,
            "steps": 16,
            "cfg": 1.0,
            "filename_prefix": f"refboard/{pack.identity.group}_{pack.identity.id.split('.')[1]}/{index:02d}",
        }
        path = params_dir / f"{index:02d}.json"
        path.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jobs.append({
            "id": f"{index:02d}",
            "workflow": "workflows/flux3_t2i_api.json",
            "params": str(path.relative_to(root)).replace("\\", "/"),
            "out": str((candidates / f"{index:02d}").relative_to(root)).replace("\\", "/"),
        })

    (candidates / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps({
        "style": pack.identity.id,
        "status": "PENDING_REVIEW",
        "subjects": SUBJECTS[: args.limit],
        "note": "Candidates only. Approve/reject each sample by hand; images are local and not in Git.",
        "license": "generated locally with FLUX.3; reference images are not redistributed",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": str(candidates / "jobs.json"), "count": len(jobs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
