from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from literary_intelligence.schemas.source import SourceRecord, SourceRegistryFile


class SourceRegistryError(RuntimeError):
    """Raised when source metadata, files, or hashes are inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class LoadedSource:
    record: SourceRecord
    base_dir: Path
    original_text: str
    normalized_text: str
    segments: tuple[dict, ...]

    def has_locator(self, locator: str) -> bool:
        return any(seg.get("locator") == locator for seg in self.segments)

    def segment_text(self, locator: str) -> dict | None:
        for seg in self.segments:
            if seg.get("locator") == locator:
                return seg
        return None


class SourceRegistry:
    def __init__(self, sources: dict[str, LoadedSource]):
        self.sources = sources

    def get(self, source_id: str) -> LoadedSource:
        try:
            return self.sources[source_id]
        except KeyError as exc:
            raise SourceRegistryError(f"Unknown source_id: {source_id}") from exc

    def has(self, source_id: str) -> bool:
        return source_id in self.sources


def _safe_path(base: Path, value: str) -> Path:
    p = (base / value).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError as exc:
        raise SourceRegistryError(f"Source path escapes corpus directory: {value}") from exc
    return p


def load_source_registry(path: Path) -> SourceRegistry:
    path = Path(path).resolve()
    if not path.is_file():
        raise SourceRegistryError(f"Missing source registry: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    file_model = SourceRegistryFile.model_validate(raw)
    loaded: dict[str, LoadedSource] = {}
    for record in file_model.sources:
        if record.source_id in loaded:
            raise SourceRegistryError(f"Duplicate source_id: {record.source_id}")
        base = path.parent
        original_path = _safe_path(base, record.original_text_path)
        normalized_path = _safe_path(base, record.normalized_text_path)
        segments_path = _safe_path(base, record.segments_path)
        for p in (original_path, normalized_path, segments_path):
            if not p.is_file():
                raise SourceRegistryError(f"Missing source file: {p}")
        original_bytes = original_path.read_bytes()
        normalized_bytes = normalized_path.read_bytes()
        if sha256_bytes(original_bytes) != record.content_sha256:
            raise SourceRegistryError(
                f"Source SHA-256 mismatch: {record.source_id} original_text"
            )
        if sha256_bytes(normalized_bytes) != record.normalized_sha256:
            raise SourceRegistryError(
                f"Source SHA-256 mismatch: {record.source_id} normalized_text"
            )
        original = original_bytes.decode("utf-8")
        normalized = normalized_bytes.decode("utf-8")
        segments_raw = json.loads(segments_path.read_text(encoding="utf-8"))
        if not isinstance(segments_raw, list) or not segments_raw:
            raise SourceRegistryError(f"Segments must be a non-empty list: {segments_path}")
        segments = tuple(segments_raw)
        locators = [seg.get("locator") for seg in segments]
        if len(locators) != len(set(locators)):
            raise SourceRegistryError(f"Duplicate locator in {segments_path}")
        loaded[record.source_id] = LoadedSource(
            record=record,
            base_dir=base,
            original_text=original,
            normalized_text=normalized,
            segments=segments,
        )
    if not loaded:
        raise SourceRegistryError("Source registry contains no sources")
    return SourceRegistry(loaded)
