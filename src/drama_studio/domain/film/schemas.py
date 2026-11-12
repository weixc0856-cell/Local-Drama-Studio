"""Script-to-Film data contracts.

Strict Pydantic models for the production layer that sits between image
generation and video generation. See docs/FILM_PRODUCTION_GUIDE.md.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SHOT_RE = re.compile(r"^S\d{2,3}$")
NARRATION_RE = re.compile(r"^N\d{3}$")


class ShotSize(str, Enum):
    EWS = "ews"
    WS = "ws"
    FS = "fs"
    MS = "ms"
    MCU = "mcu"
    CU = "cu"
    ECU = "ecu"
    OTS = "ots"


class CameraMove(str, Enum):
    STATIC = "static"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    PAN = "pan"
    TILT = "tilt"
    CRANE = "crane"
    ORBIT = "orbit"
    HANDHELD = "handheld"


class Transition(str, Enum):
    CUT = "cut"
    MATCH_CUT = "match_cut"
    DISSOLVE = "dissolve"
    FADE_BLACK = "fade_black"


class ShotStatus(str, Enum):
    PLANNED = "planned"
    KEYFRAME_GENERATED = "keyframe_generated"
    KEYFRAME_APPROVED = "keyframe_approved"
    VIDEO_GENERATED = "video_generated"
    VIDEO_APPROVED = "video_approved"
    ASSEMBLED = "assembled"
    FINALIZED = "finalized"


MotionDirection = Literal["left_to_right", "right_to_left", "toward_camera", "away_from_camera", "static"]
Dof = Literal["shallow", "medium", "deep"]


class NarrationSegment(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    text: str = Field(min_length=1)
    # Spoken text and subtitle text may differ: a simplified TTS script can
    # carry traditional subtitles without changing the reading.
    subtitle_text: str | None = None
    emotion: str | None = None
    delivery: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pause_after_ms: int = Field(default=0, ge=0, le=10000)
    # Optional per-line voice cast; only APPROVED profiles may enter production.
    voice_profile: str | None = None

    @field_validator("id")
    @classmethod
    def _id_shape(cls, value: str) -> str:
        if not NARRATION_RE.match(value):
            raise ValueError(f"narration id must look like N001, got {value!r}")
        return value


class Narration(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    language: str = "zh-CN"
    segments: list[NarrationSegment] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> "Narration":
        seen = [s.id for s in self.segments]
        if len(seen) != len(set(seen)):
            raise ValueError("narration ids must be unique")
        return self

    def ids(self) -> set[str]:
        return {s.id for s in self.segments}


class Screenplay(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    logline: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    acts: list[str] = Field(default_factory=list)
    emotion_curve: list[str] = Field(default_factory=list)


class SourceText(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    title: str
    author: str
    dynasty: str | None = None
    text: str = Field(min_length=1)
    notes: str | None = None


class ArtDirection(BaseModel):
    model_config = {"extra": "forbid"}

    style: str = Field(min_length=1)
    period: str | None = None
    aspect_ratio: str = "16:9"
    lighting: str = Field(min_length=1)
    palette: list[str] = Field(default_factory=list)


class CharacterDesign(BaseModel):
    model_config = {"extra": "forbid"}

    identity: str
    clothing: str | None = None
    color: str | None = None
    hair: str | None = None


class EnvironmentDesign(BaseModel):
    model_config = {"extra": "forbid"}

    architecture: str | None = None
    landscape: str | None = None
    weather: str | None = None
    atmosphere: str | None = None


class CameraLanguage(BaseModel):
    model_config = {"extra": "forbid"}

    movement: str = "slow_and_deliberate"
    depth: str = "layered"
    transitions: str = "motivated_cuts"


class VisualBible(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    art_direction: ArtDirection
    protagonist: CharacterDesign
    environment: EnvironmentDesign
    camera_language: CameraLanguage


class CameraSpec(BaseModel):
    model_config = {"extra": "forbid"}

    move: CameraMove
    angle: str = "eye"
    lens_mm: int = Field(default=35, ge=8, le=300)
    dof: Dof = "deep"


class Layers(BaseModel):
    model_config = {"extra": "forbid"}

    foreground: str = ""
    midground: str = ""
    background: str = ""

    @model_validator(mode="after")
    def _has_depth(self) -> "Layers":
        if not (self.foreground or self.midground or self.background):
            raise ValueError("at least one depth layer must be described")
        return self


class MotionSpec(BaseModel):
    model_config = {"extra": "forbid"}

    primary: str = Field(min_length=1)
    secondary: list[str] = Field(default_factory=list)

    @field_validator("secondary")
    @classmethod
    def _not_too_many(cls, value: list[str]) -> list[str]:
        if len(value) > 2:
            raise ValueError("at most two secondary motions; Wan degrades with stacked motion")
        return value


class ContinuitySpec(BaseModel):
    model_config = {"extra": "forbid"}

    previous_shot: str | None = None
    next_shot: str | None = None
    lighting: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    character_state: str = "none"
    motion_direction: MotionDirection = "static"
    match_cut_to: str | None = None


class GenerationSpec(BaseModel):
    model_config = {"extra": "forbid"}

    image_model: str = "flux3"
    video_model: str = "wan2.2_ti2v_5b"
    status: ShotStatus = ShotStatus.PLANNED


class ShotSpec(BaseModel):
    model_config = {"extra": "forbid"}

    shot_id: str
    scene_id: str = Field(min_length=1)
    narration_ids: list[str] = Field(default_factory=list)
    character_in_frame: bool = True
    keyframe_note: str | None = None
    duration_seconds: float = Field(gt=0, le=30)
    shot_size: ShotSize
    camera: CameraSpec
    layers: Layers
    motion: MotionSpec
    continuity: ContinuitySpec
    generation: GenerationSpec = Field(default_factory=GenerationSpec)

    @field_validator("shot_id")
    @classmethod
    def _shot_shape(cls, value: str) -> str:
        if not SHOT_RE.match(value):
            raise ValueError(f"shot_id must look like S01, got {value!r}")
        return value

    @field_validator("narration_ids")
    @classmethod
    def _narration_shape(cls, value: list[str]) -> list[str]:
        for item in value:
            if not NARRATION_RE.match(item):
                raise ValueError(f"narration id must look like N001, got {item!r}")
        return value


class Storyboard(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    shots: list[ShotSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _sequence_and_chain(self) -> "Storyboard":
        ids = [shot.shot_id for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("shot ids must be unique")
        numbers = [int(item[1:]) for item in ids]
        if numbers != list(range(1, len(ids) + 1)):
            raise ValueError(f"shots must be sequential S01..S{n:02d}, got {ids}")
        for index, shot in enumerate(self.shots):
            expected_prev = self.shots[index - 1].shot_id if index > 0 else None
            expected_next = self.shots[index + 1].shot_id if index + 1 < len(self.shots) else None
            if shot.continuity.previous_shot != expected_prev:
                raise ValueError(
                    f"{shot.shot_id}: previous_shot must be {expected_prev!r}, "
                    f"got {shot.continuity.previous_shot!r}"
                )
            if shot.continuity.next_shot != expected_next:
                raise ValueError(
                    f"{shot.shot_id}: next_shot must be {expected_next!r}, got {shot.continuity.next_shot!r}"
                )
        return self

    def ids(self) -> list[str]:
        return [shot.shot_id for shot in self.shots]


class TimelineEntry(BaseModel):
    model_config = {"extra": "forbid"}

    shot_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    narration_ids: list[str] = Field(default_factory=list)
    visual_asset: str | None = None
    asset_kind: str | None = None
    planned_duration_seconds: float | None = None
    transition_in: Transition = Transition.CUT
    transition_out: Transition = Transition.CUT

    @model_validator(mode="after")
    def _ordered(self) -> "TimelineEntry":
        if self.end_ms <= self.start_ms:
            raise ValueError(f"{self.shot_id}: end_ms must be greater than start_ms")
        return self


class NarrationEvent(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    shot_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = ""


class EditTimeline(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str
    sample_rate: int = 48000
    fps: int = 24
    leading_silence_ms: int = 0
    entries: list[TimelineEntry] = Field(min_length=1)
    narration_events: list[NarrationEvent] = Field(default_factory=list)
    total_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def _contiguous(self) -> "EditTimeline":
        cursor = 0
        for entry in self.entries:
            if entry.start_ms != cursor:
                raise ValueError(
                    f"{entry.shot_id}: start_ms {entry.start_ms} does not follow previous end {cursor}"
                )
            cursor = entry.end_ms
        if cursor != self.total_ms:
            raise ValueError(f"total_ms {self.total_ms} does not match last end {cursor}")
        return self
