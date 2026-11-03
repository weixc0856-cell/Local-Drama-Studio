from __future__ import annotations

from literary_intelligence.harness.text_normalizer import load_mapping, normalize_text
from literary_intelligence.tests.conftest import CORPUS


def test_normalization_keeps_raw_and_records_mapping() -> None:
    mapping = load_mapping(CORPUS / "normalization_map.json")
    raw = "白日依山盡\n長風過野原"
    result = normalize_text(raw, mapping)
    assert result.original == raw
    assert result.normalized == "白日依山尽\n长风过野原"
    assert result.used_mappings["盡"] == "尽"
    assert result.used_mappings["風"] == "风"


def test_normalization_is_nfc() -> None:
    # A decomposed Latin sequence is normalized without touching the source.
    raw = "é"
    result = normalize_text(raw, {})
    assert result.normalized == "é"
    assert result.original == raw
