from __future__ import annotations

import hashlib

from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.tests.conftest import CORPUS


def test_source_hashes_and_segments() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    source = registry.get("src_luoshen_wikisource_7908816")
    assert hashlib.sha256(source.original_text.encode("utf-8")).hexdigest() == source.record.content_sha256
    assert hashlib.sha256(source.normalized_text.encode("utf-8")).hexdigest() == source.record.normalized_sha256
    assert source.has_locator("洛神賦/其形也/第2句")
    assert "翩若驚鴻　婉若游龍" in source.original_text
    assert "翩若惊鸿　婉若游龙" in source.normalized_text


def test_source_locator_lookup() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    source = registry.get("src_luoshen_wikisource_7908816")
    assert source.segment_text("洛神賦/其形也/第2句") is not None
    assert source.segment_text("不存在/第99句") is None
