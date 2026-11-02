"""Data contracts for the drama pipeline.

These models are the boundary between the local LLM and the rest of the
pipeline. The LLM must produce JSON that validates against
:class:`Storyboard`; free-form prose is never accepted.

Naming rules:
    character  char_001
    location   loc_001
    prop       prop_001
    shot       shot_001
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CHAR_ID = r"^char_\d{3}$"
LOC_ID = r"^loc_\d{3}$"
PROP_ID = r"^prop_\d{3}$"
SHOT_ID = r"^shot_\d{3}$"

CharId = Annotated[str, StringConstraints(pattern=CHAR_ID)]
LocId = Annotated[str, StringConstraints(pattern=LOC_ID)]
PropId = Annotated[str, StringConstraints(pattern=PROP_ID)]
ShotId = Annotated[str, StringConstraints(pattern=SHOT_ID)]


class ShotStatus(str, Enum):
    PENDING = "PENDING"
    IMAGE_GENERATING = "IMAGE_GENERATING"
    IMAGE_REVIEW = "IMAGE_REVIEW"
    VIDEO_GENERATING = "VIDEO_GENERATING"
    VIDEO_REVIEW = "VIDEO_REVIEW"
    AUDIO_READY = "AUDIO_READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CharId
    name: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=1, le=120)
    appearance: str = Field(min_length=4, max_length=400)
    wardrobe: str = Field(default="", max_length=400)
    voice_id: str = Field(min_length=1, max_length=40)


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: LocId
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=4, max_length=400)
    time_of_day: str = Field(default="", max_length=40)


class Prop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: PropId
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=300)


class Shot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: ShotId
    index: int = Field(ge=1, le=999)
    character_ids: list[CharId] = Field(default_factory=list)
    location_id: LocId | None = None
    prop_ids: list[PropId] = Field(default_factory=list)
    duration_seconds: float = Field(ge=1.0, le=15.0)
    camera: str = Field(min_length=1, max_length=60)
    action: str = Field(min_length=4, max_length=400)
    dialogue: str = Field(default="", max_length=300)
    image_prompt: str = Field(min_length=4, max_length=1200)
    video_prompt: str = Field(min_length=4, max_length=1200)
    status: ShotStatus = ShotStatus.PENDING
    notes: str = Field(default="", max_length=400)

    @model_validator(mode="after")
    def _id_matches_index(self) -> "Shot":
        expected = f"shot_{self.index:03d}"
        if self.shot_id != expected:
            raise ValueError(f"shot_id {self.shot_id!r} does not match index {self.index} (expected {expected!r})")
        return self


class Storyboard(BaseModel):
    """The single structured artifact produced by the script engine."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    logline: str = Field(min_length=4, max_length=400)
    duration_target_seconds: float = Field(ge=10.0, le=180.0)
    style: str = Field(default="cinematic, realistic", max_length=200)
    characters: list[Character] = Field(min_length=1)
    locations: list[Location] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)
    shots: list[Shot] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def _referential_integrity(self) -> "Storyboard":
        char_ids = [c.id for c in self.characters]
        loc_ids = [l.id for l in self.locations]
        prop_ids = [p.id for p in self.props]

        for label, ids in (("character", char_ids), ("location", loc_ids), ("prop", prop_ids)):
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {label} id")

        shot_ids = [s.shot_id for s in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("duplicate shot_id")
        indexes = [s.index for s in self.shots]
        if indexes != list(range(1, len(indexes) + 1)):
            raise ValueError("shot indexes must be contiguous starting at 1")

        known_chars, known_locs, known_props = set(char_ids), set(loc_ids), set(prop_ids)
        for shot in self.shots:
            missing_chars = set(shot.character_ids) - known_chars
            if missing_chars:
                raise ValueError(f"{shot.shot_id} references unknown characters: {sorted(missing_chars)}")
            missing_props = set(shot.prop_ids) - known_props
            if missing_props:
                raise ValueError(f"{shot.shot_id} references unknown props: {sorted(missing_props)}")
            if shot.location_id and shot.location_id not in known_locs:
                raise ValueError(f"{shot.shot_id} references unknown location {shot.location_id}")
        return self


class ProjectManifest(BaseModel):
    """Derived, human-readable summary of a project directory.

    The authoritative per-shot state lives in ``projects/<id>/state.db``.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: str
    title: str = ""
    created_at: datetime
    updated_at: datetime
    pipeline_stage: str = "created"
    storyboard_sha256: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    notes: str = ""
