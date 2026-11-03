from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NormalizationResult:
    original: str
    normalized: str
    used_mappings: dict[str, str]


def load_mapping(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    mapping = data.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"Normalization map must contain a mapping: {path}")
    return {str(k): str(v) for k, v in mapping.items()}


def normalize_text(text: str, mapping: dict[str, str]) -> NormalizationResult:
    """Return NFC-normalized text plus a manually mapped simplified copy.

    The original is not overwritten. Used mappings are recorded so a reviewer
    can see every character-level change.
    """
    nfc = unicodedata.normalize("NFC", text)
    used: dict[str, str] = {}
    out: list[str] = []
    for ch in nfc:
        replacement = mapping.get(ch, ch)
        if replacement != ch:
            used[ch] = replacement
        out.append(replacement)
    return NormalizationResult(original=text, normalized="".join(out), used_mappings=used)
