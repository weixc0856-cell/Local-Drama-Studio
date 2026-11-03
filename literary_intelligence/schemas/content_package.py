from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VerificationStatus = Literal["draft", "evidence_checked", "human_reviewed", "published"]


class WorkInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    author: str = Field(min_length=1, max_length=80)
    dynasty: str = Field(default="", max_length=80)
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1, max_length=200)
    source_license_status: str = Field(min_length=1, max_length=200)


class ContentPositioning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_text: str = Field(min_length=1, max_length=500)
    target_locator: str = Field(min_length=1, max_length=200)
    surrounding_context: list[str] = Field(min_length=1, max_length=20)


class InterpretationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=1000)
    claim_refs: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"


class ImageryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1, max_length=80)
    meaning: str = Field(min_length=1, max_length=500)
    claim_refs: list[str] = Field(default_factory=list)


class HistoricalNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=1000)
    claim_refs: list[str] = Field(default_factory=list)
    verification: Literal["unverified", "verified"] = "unverified"


class LiteraryAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_analysis: list[str] = Field(min_length=1, max_length=30)
    literary_interpretation: list[InterpretationItem] = Field(min_length=1, max_length=20)
    imagery: list[ImageryItem] = Field(default_factory=list, max_length=30)
    emotion: list[str] = Field(default_factory=list, max_length=20)
    artistic_features: list[str] = Field(default_factory=list, max_length=20)
    historical_context: list[HistoricalNote] = Field(default_factory=list, max_length=20)
    uncertainty_notes: list[str] = Field(default_factory=list, max_length=20)


class ScenePlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(pattern=r"^scene_\d{3}$")
    duration_seconds: float = Field(gt=0, le=20)
    visual_source: str = Field(min_length=1, max_length=300)
    camera_motion: str = Field(min_length=1, max_length=100)
    visual_prompt: str = Field(min_length=1, max_length=1200)
    subtitle_ids: list[str] = Field(default_factory=list)


class SubtitleSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(pattern=r"^sub_\d{3}$")
    text: str = Field(min_length=1, max_length=300)
    claim_refs: list[str] = Field(default_factory=list)
    estimated_duration_seconds: float = Field(gt=0, le=20)


class PlatformMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    ai_disclosure: str = Field(default="", max_length=300)


class VideoContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_options: list[str] = Field(min_length=1, max_length=10)
    opening_hook: str = Field(min_length=1, max_length=500)
    narration: str = Field(min_length=1, max_length=4000)
    scene_plan: list[ScenePlanItem] = Field(min_length=1, max_length=60)
    visual_prompts: list[str] = Field(min_length=1, max_length=60)
    subtitle_segments: list[SubtitleSegment] = Field(min_length=1, max_length=120)
    ending: str = Field(min_length=1, max_length=1000)
    platform_metadata: PlatformMetadata


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_refs: list[str] = Field(min_length=1)
    claim_refs: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = "draft"
    generated_by: str = Field(min_length=1, max_length=200)
    generation_timestamp: str = Field(min_length=1, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=50)


class ContentPackage(BaseModel):
    """A production-facing literary video content package.

    This is intentionally separate from the R3 build inputs. An adapter maps
    scene_plan/subtitle_segments to segments.json and audio_manifest.json.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    work: WorkInfo
    positioning: ContentPositioning
    analysis: LiteraryAnalysis
    video: VideoContent
    provenance: Provenance

    @model_validator(mode="after")
    def _consistent(self) -> "ContentPackage":
        if self.work.source_id not in self.provenance.source_refs:
            raise ValueError("work.source_id must appear in provenance.source_refs")
        scene_ids = [s.scene_id for s in self.video.scene_plan]
        subtitle_ids = [s.segment_id for s in self.video.subtitle_segments]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("duplicate scene_id")
        if len(subtitle_ids) != len(set(subtitle_ids)):
            raise ValueError("duplicate subtitle segment_id")
        known_subtitles = set(subtitle_ids)
        for scene in self.video.scene_plan:
            missing = set(scene.subtitle_ids) - known_subtitles
            if missing:
                raise ValueError(f"{scene.scene_id} references unknown subtitle IDs: {sorted(missing)}")
        for segment in self.video.subtitle_segments:
            missing_claims = set(segment.claim_refs) - set(self.provenance.claim_refs)
            if missing_claims:
                raise ValueError(
                    f"{segment.segment_id} references claims not in provenance: {sorted(missing_claims)}"
                )
        return self
