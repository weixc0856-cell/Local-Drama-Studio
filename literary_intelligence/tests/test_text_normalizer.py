from __future__ import annotations

from literary_intelligence.harness.text_normalizer import load_mapping, normalize_text
from literary_intelligence.tests.conftest import CORPUS


def test_normalization_keeps_raw_and_records_mapping() -> None:
    mapping = load_mapping(CORPUS / "normalization_map.json")
    raw = "翩若驚鴻　婉若游龍"
    result = normalize_text(raw, mapping)
    assert result.original == raw
    assert result.normalized == "翩若惊鸿　婉若游龙"
    assert result.used_mappings["驚"] == "惊"
    assert result.used_mappings["龍"] == "龙"


def test_normalization_is_nfc() -> None:
    # A decomposed Latin sequence is normalized without touching the source.
    raw = "é"
    result = normalize_text(raw, {})
    assert result.normalized == "é"
    assert result.original == raw
