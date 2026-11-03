from __future__ import annotations

import json
from pathlib import Path

from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.review import Review

from .evidence_validator import ValidationResult


class ReviewError(RuntimeError):
    """Raised when a review attempts an invalid state transition or bypass."""


def load_reviews(path: Path) -> list[Review]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ReviewError("reviews.json must contain a list")
    return [Review.model_validate(item) for item in raw]


def apply_review(claim: Claim, review: Review, validation: ValidationResult | None = None) -> Claim:
    if review.claim_id != claim.claim_id:
        raise ReviewError(f"review claim_id {review.claim_id} does not match {claim.claim_id}")
    if review.reviewer_type != "human":
        raise ReviewError("LLM-generated reviews cannot approve or reject claims")
    if claim.review_status != "unreviewed":
        raise ReviewError(
            f"invalid transition: {claim.review_status} -> {review.decision}; "
            "LI-1 only permits unreviewed -> approved|rejected"
        )
    if review.decision == "approved":
        if validation is None:
            raise ReviewError("approval requires a validation result")
        if not validation.ok:
            raise ReviewError(
                "approval requires valid evidence: " + ", ".join(validation.codes)
            )
    return claim.model_copy(update={"review_status": review.decision})
