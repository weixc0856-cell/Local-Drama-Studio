from __future__ import annotations

from copy import deepcopy

import pytest

from literary_intelligence.harness.script_export import ExportError, export_json, export_markdown
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.claim import Claim
from literary_intelligence.tests.conftest import CORPUS
from literary_intelligence.tests.test_evidence_validator import base_claim


def registry():
    return load_source_registry(CORPUS / "source_registry.json")


def approved(data: dict) -> Claim:
    item = deepcopy(data)
    item["review_status"] = "approved"
    return Claim.model_validate(item)


def test_unreviewed_not_exported() -> None:
    claim = Claim.model_validate(base_claim())
    markdown = export_markdown([claim], registry())
    assert "无 approved claim" in markdown
    assert "翩若" not in markdown
    assert export_json([claim], registry()) == []


def test_approved_claim_exported() -> None:
    claim = approved(base_claim())
    markdown = export_markdown([claim], registry())
    assert "test_001" in markdown
    assert "原文" in markdown
    assert "翩若惊鸿" in markdown


def test_creative_classification_preserved() -> None:
    data = deepcopy(base_claim())
    data["claim_id"] = "creative_001"
    data["claim_type"] = "creative"
    data["source_refs"] = []
    data["quote"] = ""
    data["source_quote"] = ""
    data["display_quote"] = ""
    data["statement"] = "创作性视觉转译"
    claim = approved(data)
    payload = export_json([claim], registry())
    assert payload[0]["claim_type"] == "creative"
    assert payload[0]["claim_id"] == "creative_001"


def test_invalid_approved_claim_blocks_export() -> None:
    data = deepcopy(base_claim())
    data["quote"] = "不存在的引文"
    claim = approved(data)
    with pytest.raises(ExportError):
        export_markdown([claim], registry())
