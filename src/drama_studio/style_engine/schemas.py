"""Strict schemas for a Visual Style Pack."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StyleIdentity(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    id: str
    name: str
    group: str
    version: str
    status: str = "SPEC_DRAFT"
    summary: str
    layers: list[str] = Field(default_factory=lambda: ["identity", "execution", "consistency"])


class ImagePrompt(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    identity: str
    medium: str
    materials: list[str]
    composition: list[str]
    prompt_order: list[str]
    positive_anchors: list[str]


class VideoPrompt(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    motion_vocabulary: list[str]
    secondary_limit: int = 2
    preserve: list[str]
    avoid: list[str]


class CameraProfile(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    allowed_moves: list[str]
    preferred_lens_mm: int
    dof_strategy: str


class MotionProfile(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    primary_motions: list[str]
    secondary_motions: list[str]
    secondary_limit: int = 2


class LightingProfile(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    key: str
    temperature: str
    contrast: str


class ColorAnchor(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    hex: str


class ColorProfile(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    anchors: list[ColorAnchor]
    saturation_range: list[float]
    edge_density_range: list[float]
    value_range: list[float]
    note: str = ""


class MaterialProfile(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    materials: list[str]
    texture_cues: list[str]


class NegativeConstraints(BaseModel):
    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    forbidden: list[str]
    note: str = ""


class StylePack(BaseModel):
    model_config = {"extra": "forbid"}

    identity: StyleIdentity
    image: ImagePrompt
    video: VideoPrompt
    camera: CameraProfile
    motion: MotionProfile
    lighting: LightingProfile
    color: ColorProfile
    material: MaterialProfile
    negative: NegativeConstraints
