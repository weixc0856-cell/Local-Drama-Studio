from __future__ import annotations

from literary_intelligence.harness.retrieval import RetrievalIndex
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.tests.conftest import CORPUS


def test_fts5_three_char_and_two_char_fallback() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    index = RetrievalIndex()
    try:
        index.build(registry)
        three = index.search("若惊鸿")
        two = index.search("惊鸿")
        assert any(hit.locator == "洛神賦/其形也/第2句" for hit in three)
        assert any(hit.locator == "洛神賦/其形也/第2句" for hit in two)
        assert all(hit.source_id == "src_luoshen_wikisource_7908816" for hit in three + two)
    finally:
        index.close()


def test_work_and_edition_filter() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    index = RetrievalIndex()
    try:
        index.build(registry)
        assert index.search("若惊鸿", work="洛神賦")
        assert not index.search("若惊鸿", work="不存在的作品")
        assert index.search("若惊鸿", edition=registry.get("src_luoshen_wikisource_7908816").record.edition)
    finally:
        index.close()


def test_empty_query_returns_empty() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    index = RetrievalIndex()
    try:
        index.build(registry)
        assert index.search("   ") == []
    finally:
        index.close()
