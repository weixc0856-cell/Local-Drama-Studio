from __future__ import annotations

from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.review import Review
from literary_intelligence.schemas.export_schemas import export_schemas
from literary_intelligence.schemas.source import SourceRecord


def test_claim_schema_has_required_fields() -> None:
    schema = Claim.model_json_schema()
    props = schema["properties"]
    for field in ["claim_id", "source_refs", "locator", "quote", "claim_type", "statement", "review_status"]:
        assert field in props
    assert "claim_type" in schema["required"]


def test_source_schema_has_hash_and_license() -> None:
    schema = SourceRecord.model_json_schema()
    assert "content_sha256" in schema["properties"]
    assert "license" in schema["properties"]
    assert "commercial_use" in schema["properties"]


def test_review_schema_requires_reviewer_type() -> None:
    schema = Review.model_json_schema()
    assert "reviewer_type" in schema["properties"]
    assert "reviewer_type" in schema["required"]


def test_export_schemas(tmp_path) -> None:
    written = export_schemas(tmp_path)
    assert {p.name for p in written} == {
        "source.schema.json", "claim.schema.json", "review.schema.json",
        "llm_pass.schema.json", "content_package.schema.json"
    }
    for path in written:
        assert path.is_file()
        assert "properties" in path.read_text(encoding="utf-8")
