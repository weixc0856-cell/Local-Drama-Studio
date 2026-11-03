from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimType = Literal["original_text", "historical_fact", "interpretation", "creative"]
ReviewStatus = Literal["unreviewed", "approved", "rejected"]
Confidence = Literal["high", "medium", "low"]
ClaimScope = Literal["target", "contextual"]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    work: str = Field(min_length=1)
    author: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    locator: str = Field(min_length=1)
    quote: str = ""
    source_quote: str = ""
    display_quote: str = ""
    claim_type: ClaimType
    statement: str = Field(min_length=1)
    confidence: Confidence
    review_status: ReviewStatus = "unreviewed"
    scope: ClaimScope = "target"
    notes: str = ""


class ClaimFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[Claim]
