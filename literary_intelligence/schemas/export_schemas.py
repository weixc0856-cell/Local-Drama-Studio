from __future__ import annotations

import json
from pathlib import Path

from .claim import Claim
from .llm_pass import LLMPassOutput
from .review import Review
from .source import SourceRecord


SCHEMAS = {
    "source.schema.json": SourceRecord,
    "claim.schema.json": Claim,
    "review.schema.json": Review,
    "llm_pass.schema.json": LLMPassOutput,
}


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in SCHEMAS.items():
        path = out_dir / name
        path.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="literary_intelligence/schemas/json")
    args = parser.parse_args()
    for path in export_schemas(Path(args.out)):
        print(path)
