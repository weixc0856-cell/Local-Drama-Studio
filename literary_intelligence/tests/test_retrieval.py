from __future__ import annotations

from literary_intelligence.harness.retrieval import RetrievalIndex
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.tests.conftest import CORPUS, SOURCE_ID, TARGET_LOCATOR, WORK


def test_fts5_three_char_and_two_char_fallback() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    index = RetrievalIndex()
    try:
        index.build(registry)
        three = index.search("依山尽")
        two = index.search("依山")
        assert any(hit.locator == TARGET_LOCATOR for hit in three)
        assert any(hit.locator == TARGET_LOCATOR for hit in two)
        assert all(hit.source_id == SOURCE_ID for hit in three + two)
    finally:
        index.close()


def test_work_and_edition_filter() -> None:
    registry = load_source_registry(CORPUS / "source_registry.json")
    index = RetrievalIndex()
    try:
        index.build(registry)
        assert index.search("依山尽", work=WORK)
        assert not index.search("依山尽", work="不存在的作品")
        assert index.search("依山尽", edition=registry.get(SOURCE_ID).record.edition)
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
