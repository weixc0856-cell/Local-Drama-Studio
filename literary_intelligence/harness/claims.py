from __future__ import annotations

import json
from pathlib import Path

from literary_intelligence.schemas.claim import Claim


class ClaimLoadError(RuntimeError):
    pass


def load_claims(path: Path) -> list[Claim]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("claims")
    if not isinstance(raw, list):
        raise ClaimLoadError("claims.json must be a list or contain a claims list")
    return [Claim.model_validate(item) for item in raw]
