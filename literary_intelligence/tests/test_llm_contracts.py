from __future__ import annotations

from copy import deepcopy

import pytest

from literary_intelligence.harness.evidence_validator import validate_claim
from literary_intelligence.harness.llm_client import MockLLMClient
from literary_intelligence.harness.pipeline import RoleContractError, run_mock_pipeline, run_pipeline
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.llm_pass import LLMPassOutput
from literary_intelligence.tests.conftest import CORPUS
from literary_intelligence.tests.test_evidence_validator import base_claim

FIXTURE = CORPUS.parent / "mock_llm.json"


def registry():
    return load_source_registry(CORPUS / "source_registry.json")


def test_mock_pipeline_five_passes() -> None:
    result = run_mock_pipeline(registry(), FIXTURE)
    assert [o.pass_name for o in result.outputs] == [
        "text_analyst", "literary_analyst", "researcher", "skeptic", "editor"
    ]
    assert all(o.is_mock for o in result.outputs)
    assert "mock_literary_001" in result.validations
    assert result.validations["mock_literary_001"].ok
    assert result.outputs[1].claims[0].review_status == "unreviewed"
    assert result.outputs[2].research_status == "no_source_found"
    assert result.outputs[3].reviewed_claim_ids == ["mock_literary_001"]


def test_counterexample_a_unknown_source() -> None:
    data = deepcopy(base_claim())
    data["source_refs"] = ["src_fake_999"]
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert "UNKNOWN_SOURCE" in result.codes


def test_counterexample_b_fake_quote() -> None:
    data = deepcopy(base_claim())
    data["quote"] = "伪造的引文"
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert "QUOTE_NOT_FOUND" in result.codes


def test_counterexample_c_unsourced_history() -> None:
    data = deepcopy(base_claim())
    data["claim_type"] = "historical_fact"
    data["source_refs"] = []
    data["quote"] = ""
    data["source_quote"] = ""
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert "MISSING_SOURCE" in result.codes


def test_counterexample_d_creative_mislabeled_as_history() -> None:
    data = deepcopy(base_claim())
    data["claim_type"] = "historical_fact"
    data["source_refs"] = []
    data["quote"] = ""
    data["source_quote"] = ""
    data["statement"] = "我认为这个意象象征自由（创作性想法）"
    result = validate_claim(Claim.model_validate(data), registry())
    assert not result.ok
    assert "MISSING_SOURCE" in result.codes


class SelfApprovingClient:
    def complete(self, pass_name, context):
        if pass_name != "text_analyst":
            return LLMPassOutput(pass_name=pass_name, is_mock=True)
        data = deepcopy(base_claim())
        data["review_status"] = "approved"
        return LLMPassOutput(pass_name="text_analyst", claims=[Claim.model_validate(data)], is_mock=True)


def test_counterexample_e_pipeline_rejects_self_approval() -> None:
    with pytest.raises(RoleContractError, match="LLM_SELF_APPROVAL"):
        run_pipeline(registry(), SelfApprovingClient())


def test_mock_client_returns_fixture() -> None:
    client = MockLLMClient(FIXTURE)
    output = client.complete("text_analyst", {})
    assert output.is_mock is True
    assert output.pass_name == "text_analyst"


def test_parse_json_after_think_and_fence() -> None:
    from literary_intelligence.harness.llm_client import parse_json_response
    text = "<think>hidden</think>\n```json\n{\"ok\": true}\n```"
    assert parse_json_response(text) == {"ok": True}
    text2 = "<think>hidden</think>\n{\"ok\": false}"
    assert parse_json_response(text2) == {"ok": False}


class ResearcherViolationClient:
    def complete(self, pass_name, context):
        if pass_name == "text_analyst":
            return LLMPassOutput(
                pass_name="text_analyst",
                claims=[Claim.model_validate(base_claim())],
                coverage="target",
            )
        if pass_name == "researcher":
            return LLMPassOutput(
                pass_name="researcher",
                claims=[Claim.model_validate({**base_claim(), "claim_id": "bad_researcher"})],
                research_status="new_source",
            )
        return LLMPassOutput(pass_name=pass_name)


def test_pipeline_fails_fast_on_researcher_violation() -> None:
    with pytest.raises(RoleContractError, match="RESEARCHER_ORIGINAL_TEXT"):
        run_pipeline(registry(), ResearcherViolationClient())
