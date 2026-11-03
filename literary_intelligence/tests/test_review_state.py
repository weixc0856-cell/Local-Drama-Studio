from __future__ import annotations

from copy import deepcopy

import pytest

from literary_intelligence.harness.evidence_validator import validate_claim
from literary_intelligence.harness.review_state import ReviewError, apply_review
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.review import Review
from literary_intelligence.tests.conftest import CORPUS
from literary_intelligence.tests.test_evidence_validator import base_claim


def review(decision: str = "approved", reviewer_type: str = "human") -> Review:
    return Review.model_validate({
        "review_id": "review_001",
        "claim_id": "test_001",
        "reviewer": "human-editor",
        "reviewer_type": reviewer_type,
        "decision": decision,
        "reason": "manual check",
        "timestamp": "2026-11-03T00:00:00Z",
        "evidence_checked": ["source_registry.json", "original_text.txt"],
    })


def test_human_approval_requires_valid_evidence() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    claim = Claim.model_validate(base_claim())
    validation = validate_claim(claim, registry)
    approved = apply_review(claim, review("approved", "human"), validation)
    assert approved.review_status == "approved"


def test_llm_review_rejected() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    claim = Claim.model_validate(base_claim())
    validation = validate_claim(claim, registry)
    with pytest.raises(ReviewError, match="LLM-generated"):
        apply_review(claim, review("approved", "llm"), validation)


def test_rejected_cannot_go_directly_to_approved() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    claim = Claim.model_validate(base_claim()).model_copy(update={"review_status": "rejected"})
    validation = validate_claim(claim, registry)
    with pytest.raises(ReviewError, match="invalid transition"):
        apply_review(claim, review("approved", "human"), validation)


def test_invalid_evidence_cannot_be_approved() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    data = deepcopy(base_claim())
    data["quote"] = "不存在的引文"
    claim = Claim.model_validate(data)
    validation = validate_claim(claim, registry)
    with pytest.raises(ReviewError, match="valid evidence"):
        apply_review(claim, review("approved", "human"), validation)
