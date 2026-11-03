from __future__ import annotations

import hashlib

from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.tests.conftest import (
    CORPUS, SOURCE_ID, TARGET_LOCATOR, TARGET_QUOTE, TARGET_SOURCE_QUOTE,
)


def test_source_hashes_and_segments() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    source = registry.get(SOURCE_ID)
    assert hashlib.sha256(source.original_text.encode("utf-8")).hexdigest() == source.record.content_sha256
    assert hashlib.sha256(source.normalized_text.encode("utf-8")).hexdigest() == source.record.normalized_sha256
    assert source.has_locator(TARGET_LOCATOR)
    assert TARGET_SOURCE_QUOTE in source.original_text
    assert TARGET_QUOTE in source.normalized_text


def test_source_locator_lookup() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    source = registry.get(SOURCE_ID)
    assert source.segment_text(TARGET_LOCATOR) is not None
    assert source.segment_text("不存在/第99句") is None
