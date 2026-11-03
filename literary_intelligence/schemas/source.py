from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceStatus = Literal["PASS_VERIFIED", "PASS_STATIC", "PARTIAL", "NOT_RUN"]


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    work: str = Field(min_length=1)
    author: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    revision_id: int | None = None
    revision_timestamp: str | None = None
    revision_sha1: str | None = None
    license: str = Field(min_length=1)
    content_license: str | None = None
    transcription_license: str | None = None
    license_url: str | None = None
    commercial_use: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    original_text_path: str
    normalized_text_path: str
    segments_path: str
    normalization_map_path: str
    content_sha256: str = Field(min_length=64, max_length=64)
    normalized_sha256: str = Field(min_length=64, max_length=64)
    status: SourceStatus
    notes: str | None = None


class SourceRegistryFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceRecord]
