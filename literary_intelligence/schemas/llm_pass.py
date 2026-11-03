from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .claim import Claim

PassName = Literal["text_analyst", "literary_analyst", "researcher", "skeptic", "editor"]
CoverageStatus = Literal["target", "not_analyzable", "not_applicable"]
SkepticVerdict = Literal["findings", "no_material_risk", "no_candidates", "not_reviewed"]
ResearchStatus = Literal["new_source", "no_source_found", "not_run"]
RiskCategory = Literal[
    "unsupported_interpretation",
    "overinterpretation",
    "semantic_error",
    "rhetorical_error",
    "context_mismatch",
    "historical_claim_without_source",
    "wording_overstates_certainty",
]
Severity = Literal["low", "medium", "high"]


class RiskFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_claim_id: str = Field(min_length=1)
    risk_category: RiskCategory
    severity: Severity
    finding: str = Field(min_length=1)
    evidence_or_reason: str = Field(min_length=1)
    suggested_revision: str = Field(min_length=1)
    verdict: Literal["risk", "no_material_risk"] = "risk"


class LLMPassOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass_name: PassName
    claims: list[Claim] = Field(default_factory=list)
    notes: str = ""
    draft_text: str = ""
    is_mock: bool = False
    raw_response: str = ""
    coverage: CoverageStatus = "not_applicable"
    coverage_reason: str = ""
    research_status: ResearchStatus = "not_run"
    skeptic_verdict: SkepticVerdict = "not_reviewed"
    reviewed_claim_ids: list[str] = Field(default_factory=list)
    reviewed_dimensions: list[str] = Field(default_factory=list)
    skeptic_findings: list[RiskFinding] = Field(default_factory=list)
