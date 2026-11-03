from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewerType = Literal["human", "llm"]
ReviewDecision = Literal["approved", "rejected"]


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    reviewer_type: ReviewerType
    decision: ReviewDecision
    reason: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    evidence_checked: list[str] = Field(default_factory=list)
