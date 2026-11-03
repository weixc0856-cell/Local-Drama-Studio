from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .source_registry import SourceRegistry


@dataclass(frozen=True)
class SearchHit:
    source_id: str
    work: str
    edition: str
    locator: str
    raw_text: str
    normalized_text: str


class RetrievalIndex:
    """SQLite FTS5 prototype.

    Chinese queries of 3+ characters use trigram FTS5. Shorter queries use a
    LIKE fallback because trigram tokens cannot match 2 characters.
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("DROP TABLE IF EXISTS documents")
        self.conn.execute("DROP TABLE IF EXISTS documents_fts")
        self.conn.execute(
            "CREATE TABLE documents ("
            "source_id TEXT NOT NULL, work TEXT NOT NULL, edition TEXT NOT NULL, "
            "locator TEXT NOT NULL, raw_text TEXT NOT NULL, normalized_text TEXT NOT NULL)"
        )
        self.conn.execute(
            "CREATE VIRTUAL TABLE documents_fts USING fts5("
            "source_id UNINDEXED, work UNINDEXED, edition UNINDEXED, locator UNINDEXED, "
            "text, raw_text UNINDEXED, normalized_text UNINDEXED, tokenize='trigram')"
        )

    def build(self, registry: SourceRegistry) -> None:
        for source in registry.sources.values():
            for seg in source.segments:
                self.conn.execute(
                    "INSERT INTO documents(source_id, work, edition, locator, raw_text, normalized_text) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        source.record.source_id,
                        source.record.work,
                        source.record.edition,
                        seg["locator"],
                        seg["raw_text"],
                        seg["normalized_text"],
                    ),
                )
                self.conn.execute(
                    "INSERT INTO documents_fts(source_id, work, edition, locator, text, raw_text, normalized_text) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        source.record.source_id,
                        source.record.work,
                        source.record.edition,
                        seg["locator"],
                        seg["normalized_text"],
                        seg["raw_text"],
                        seg["normalized_text"],
                    ),
                )
        self.conn.commit()

    def search(self, query: str, *, work: str | None = None,
               edition: str | None = None) -> list[SearchHit]:
        q = query.strip()
        if not q:
            return []
        filters = []
        params: list[str] = []
        if work is not None:
            filters.append("work = ?")
            params.append(work)
        if edition is not None:
            filters.append("edition = ?")
            params.append(edition)
        where = (" AND " + " AND ".join(filters)) if filters else ""
        if len(q) >= 3:
            sql = (
                "SELECT source_id, work, edition, locator, raw_text, normalized_text "
                "FROM documents_fts WHERE documents_fts MATCH ?" + where
            )
            params = [q, *params]
        else:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql = (
                "SELECT source_id, work, edition, locator, raw_text, normalized_text "
                "FROM documents WHERE normalized_text LIKE ? ESCAPE '\\'" + where
            )
            params = [f"%{escaped}%", *params]
        rows = self.conn.execute(sql, params).fetchall()
        return [SearchHit(*row) for row in rows]

    def close(self) -> None:
        self.conn.close()
