from __future__ import annotations

from copy import deepcopy

from literary_intelligence.harness.evidence_validator import (
    INVALID_LOCATOR,
    MISSING_QUOTE,
    MISSING_SOURCE,
    QUOTE_NOT_FOUND,
    SOURCE_QUOTE_NOT_FOUND,
    UNKNOWN_SOURCE,
    validate_claim,
)
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.claim import Claim
from literary_intelligence.tests.conftest import CORPUS

SOURCE = "src_luoshen_wikisource_7908816"


def base_claim() -> dict:
    return {
        "claim_id": "test_001",
        "work": "洛神賦",
        "author": "曹植",
        "edition": "昭明文選（四部叢刊本）卷19 / 曹子建集（四部叢刊本）卷3",
        "source_refs": [SOURCE],
        "locator": "洛神賦/其形也/第2句",
        "quote": "翩若惊鸿　婉若游龙",
        "source_quote": "翩若驚鴻　婉若游龍",
        "display_quote": "翩若惊鸿，婉若游龙。",
        "claim_type": "original_text",
        "statement": "原文",
        "confidence": "high",
        "review_status": "unreviewed",
        "notes": "",
    }


def registry():
    return load_source_registry(CORPUS / "source_registry.json")


def test_valid_claim() -> None:
    result = validate_claim(Claim.model_validate(base_claim()), registry())
    assert result.ok, result.issues


def test_unknown_source_rejected() -> None:
    data = deepcopy(base_claim())
    data["source_refs"] = ["src_does_not_exist"]
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert UNKNOWN_SOURCE in result.codes


def test_quote_mismatch_rejected() -> None:
    data = deepcopy(base_claim())
    data["quote"] = "不存在的引文"
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert QUOTE_NOT_FOUND in result.codes


def test_source_quote_mismatch_rejected() -> None:
    data = deepcopy(base_claim())
    data["source_quote"] = "不存在的原文"
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert SOURCE_QUOTE_NOT_FOUND in result.codes


def test_invalid_locator_rejected() -> None:
    data = deepcopy(base_claim())
    data["locator"] = "洛神賦/不存在/第99句"
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert INVALID_LOCATOR in result.codes


def test_historical_fact_without_source_rejected() -> None:
    data = deepcopy(base_claim())
    data["claim_id"] = "history_without_source"
    data["claim_type"] = "historical_fact"
    data["source_refs"] = []
    data["quote"] = ""
    data["source_quote"] = ""
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert MISSING_SOURCE in result.codes


def test_creative_does_not_require_source() -> None:
    data = deepcopy(base_claim())
    data["claim_id"] = "creative_001"
    data["claim_type"] = "creative"
    data["source_refs"] = []
    data["quote"] = ""
    data["source_quote"] = ""
    result = validate_claim(Claim.model_validate(data), registry())
    assert result.ok, result.issues


def test_original_text_without_quote_rejected() -> None:
    data = deepcopy(base_claim())
    data["quote"] = ""
    data["source_quote"] = ""
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert MISSING_QUOTE in result.codes
