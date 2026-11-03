from __future__ import annotations

from copy import deepcopy

import pytest

from literary_intelligence.harness.evidence_validator import validate_claim
from literary_intelligence.harness.pipeline import (
    RoleContractError,
    TargetCoverage,
    build_context,
    check_editor,
    check_researcher,
    check_skeptic,
    check_text_analyst,
)
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.llm_pass import LLMPassOutput, RiskFinding
from literary_intelligence.tests.conftest import CORPUS
from literary_intelligence.tests.test_evidence_validator import base_claim

TARGET = "洛神賦/其形也/第2句"


def registry():
    return load_source_registry(CORPUS / "source_registry.json")


def target() -> dict:
    return build_context(registry())["target"]


def output(pass_name: str, claims: list[Claim] | None = None, **kwargs) -> LLMPassOutput:
    return LLMPassOutput.model_validate({
        "pass_name": pass_name,
        "claims": [c.model_dump() for c in (claims or [])],
        **kwargs,
    })


def claim(locator: str = TARGET, scope: str = "target", claim_id: str = "test_claim",
          claim_type: str = "interpretation") -> Claim:
    data = deepcopy(base_claim())
    data.update({
        "claim_id": claim_id,
        "locator": locator,
        "scope": scope,
        "claim_type": claim_type,
    })
    return Claim.model_validate(data)


def test_target_coverage_success() -> None:
    result = check_text_analyst(
        output("text_analyst", [claim()], coverage="target"),
        target(),
    )
    assert result.ok
    assert result.target_claim_ids == ("test_claim",)
    assert not result.not_analyzable


def test_target_coverage_failure() -> None:
    adjacent = claim(locator="洛神賦/其形也/第3句", scope="contextual", claim_id="adjacent")
    with pytest.raises(RoleContractError, match="TARGET_NOT_COVERED"):
        check_text_analyst(output("text_analyst", [adjacent], coverage="target"), target())


def test_adjacent_cannot_masquerade_as_target() -> None:
    adjacent = claim(locator="洛神賦/其形也/第3句", scope="target", claim_id="adjacent")
    with pytest.raises(RoleContractError, match="CONTEXTUAL_CLAIM_SCOPE_REQUIRED"):
        check_text_analyst(output("text_analyst", [adjacent], coverage="target"), target())


def test_explicit_not_analyzable_allowed() -> None:
    result = check_text_analyst(
        output("text_analyst", [], coverage="not_analyzable", coverage_reason="无法分析"),
        target(),
    )
    assert result.not_analyzable
    assert result.ok


def test_researcher_original_text_rejected() -> None:
    with pytest.raises(RoleContractError, match="RESEARCHER_ORIGINAL_TEXT"):
        check_researcher(output("researcher", [claim(claim_type="original_text")]), [])


def test_researcher_duplicate_claim_rejected() -> None:
    existing = Claim.model_validate({
        **deepcopy(base_claim()),
        "claim_id": "luoshen_interp_001",
    })
    duplicate = claim(claim_id="new_duplicate")
    duplicate = duplicate.model_copy(update={
        "source_quote": existing.source_quote,
        "locator": existing.locator,
    })
    with pytest.raises(RoleContractError, match="RESEARCHER_DUPLICATE_CLAIM"):
        check_researcher(output("researcher", [duplicate]), [existing])


def test_researcher_valid_sourced_fact_allowed() -> None:
    fact = claim(claim_id="new_fact", claim_type="historical_fact")
    validation = validate_claim(fact, registry())
    assert validation.ok
    check_researcher(output("researcher", [fact]), [])


def test_researcher_unsourced_fact_rejected() -> None:
    fact = deepcopy(base_claim())
    fact.update({
        "claim_id": "unsourced_fact",
        "claim_type": "historical_fact",
        "source_refs": [],
        "quote": "",
        "source_quote": "",
    })
    with pytest.raises(RoleContractError, match="RESEARCHER_UNSOURCED_FACT"):
        check_researcher(output("researcher", [Claim.model_validate(fact)]), [])


def test_skeptic_structured_finding_allowed() -> None:
    finding = RiskFinding(
        target_claim_id="luoshen_interp_002",
        risk_category="overinterpretation",
        severity="medium",
        finding="将象征意义写成确定事实",
        evidence_or_reason="原文没有提供该象征的直接依据",
        suggested_revision="改为待验证的解释",
        verdict="risk",
    )
    review = output("skeptic", [], skeptic_verdict="findings", skeptic_findings=[finding])
    check_skeptic(review)
    assert review.claims == []


def test_skeptic_no_material_risk_allowed() -> None:
    review = output(
        "skeptic", [], skeptic_verdict="no_material_risk",
        reviewed_dimensions=["原文准确性", "词义分析", "修辞分析"],
    )
    check_skeptic(review)


def test_skeptic_without_verdict_rejected() -> None:
    with pytest.raises(RoleContractError, match="SKEPTIC_NOT_REVIEWED"):
        check_skeptic(output("skeptic", []))


def test_skeptic_cannot_return_claims() -> None:
    with pytest.raises(RoleContractError, match="SKEPTIC_CLAIMS_NOT_ALLOWED"):
        check_skeptic(output("skeptic", [claim()], skeptic_verdict="no_material_risk",
                             reviewed_dimensions=["原文准确性"]))


def test_editor_without_approval_must_be_empty() -> None:
    with pytest.raises(RoleContractError, match="EDITOR_DRAFT_WITHOUT_APPROVAL"):
        check_editor(output("editor", [], draft_text="不该出现"), [])


def test_editor_empty_without_approval_allowed() -> None:
    check_editor(output("editor", [], draft_text=""), [])
