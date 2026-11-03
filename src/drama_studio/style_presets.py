"""Two core visual style presets.

``config/styles.yaml`` is the canonical definition of the product's two core
aesthetics (see ``docs/VISUAL_STYLE_SPEC.md``). Works choose a style by id; the
pipeline never branches on a style name in code.

This module validates the presets and exposes them as plain data. It never
writes to ``projects/workspace.db``: that database contains user-created facts
only, so presets are not auto-seeded. Use ``preset.as_style_entity()`` when a
caller explicitly wants to create a workspace style from a preset.

Only ``visual_language`` and ``positive_prompt`` are consumed by the current
generation path (``script_engine.compose_visual_prompt``). The structured
material/line/detail fields are audit data, and motion/compositing describe the
S2 animation work that is not wired into production yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import find_project_root

# Same rule as cli.py: a piped MSYS/PowerShell stdout defaults to the ANSI code
# page and Chinese preset names become mojibake.
if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Keep in sync with drama_studio.workspace.store.STYLE_FIELDS; a test asserts
# equality so a preset can always be handed to the workspace style API.
STYLE_ENTITY_FIELDS = (
    "name",
    "description",
    "visual_language",
    "color_palette",
    "lighting",
    "camera_language",
    "composition",
    "character_design",
    "environment_design",
    "positive_prompt",
    "negative_prompt",
    "reference_assets",
    "aspect_ratio",
    "applicable_content_types",
    "source_files",
)

AbilityStatus = Literal[
    "PASS_VERIFIED",
    "PASS_STATIC",
    "PARTIAL",
    "NOT_RUN",
    "BLOCKED",
    "DEPRECATED",
]
Primitive = Literal[
    "scroll_pan",
    "ink_matte",
    "ink_diffusion",
    "paper_texture",
    "line_reveal",
    "local_motion",
    "parallax_2_5d",
]
PrimaryMotion = Literal[
    "static",
    "scroll_pan",
    "slow_push_in",
    "slow_lateral_track",
    "ink_diffusion",
]
LocalMotion = Literal["clouds", "mist", "water", "birds", "petals", "foliage", "ink_diffusion"]

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class MaterialSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["silk", "paper", "raw_paper", "sized_paper"]
    prompt: str = Field(min_length=4, max_length=300)


class LineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: Literal["fine_line", "freehand", "outline"]
    prompt: str = Field(min_length=4, max_length=300)


class DetailSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["high", "moderate"]
    prompt: str = Field(min_length=4, max_length=300)


class WanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    usage: Literal["none", "local_supplement", "limited"]
    note: str = ""


class MotionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: list[PrimaryMotion] = Field(min_length=1)
    local: list[LocalMotion] = Field(default_factory=list)
    wan: WanSpec
    forbidden: list[str] = Field(default_factory=list)


class TextureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["silk", "paper", "raw_paper", "none"]
    asset: str | None = None
    opacity: float = Field(default=0.0, ge=0.0, le=0.3)
    note: str = ""


class ParallaxSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool = False
    requires: str = ""


class CompositingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primitives: list[Primitive] = Field(min_length=1)
    texture: TextureSpec
    parallax: ParallaxSpec = Field(default_factory=ParallaxSpec)
    note: str = ""


class StylePreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    name: str = Field(min_length=1, max_length=80)
    name_en: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=400)
    validation_status: AbilityStatus = "NOT_RUN"

    # Shared with the workspace style entity.
    visual_language: str = Field(min_length=4, max_length=600)
    color_palette: dict[str, str]
    lighting: str = Field(min_length=4, max_length=400)
    camera_language: str = Field(min_length=4, max_length=400)
    composition: str = Field(min_length=4, max_length=600)
    character_design: str = Field(min_length=4, max_length=400)
    environment_design: str = Field(min_length=4, max_length=400)
    positive_prompt: str = Field(min_length=4, max_length=1500)
    negative_prompt: str = Field(min_length=4, max_length=1000)
    reference_assets: list[str] = Field(default_factory=list)
    aspect_ratio: str = Field(pattern=r"^[0-9]{1,2}:[0-9]{1,2}$")
    applicable_content_types: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)

    # Config-layer only: not stored in workspace.db.
    material: MaterialSpec
    line: LineSpec
    detail: DetailSpec
    motion: MotionSpec
    compositing: CompositingSpec

    @field_validator("color_palette")
    @classmethod
    def _palette_is_hex(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("color_palette must not be empty")
        for name, color in value.items():
            if not _HEX.match(color):
                raise ValueError(f"color_palette[{name!r}] is not a #RRGGBB value: {color!r}")
        return value

    def as_style_entity(self) -> dict[str, object]:
        """Return exactly the fields accepted by ``WorkspaceStore.create_style``."""

        return {field: getattr(self, field) for field in STYLE_ENTITY_FIELDS}


class StylePresetRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    styles: dict[str, StylePreset] = Field(min_length=1)

    @model_validator(mode="after")
    def _keys_match_ids(self) -> "StylePresetRegistry":
        for key, preset in self.styles.items():
            if key != preset.id:
                raise ValueError(f"styles key {key!r} does not match preset id {preset.id!r}")
        return self

    def get(self, style_id: str) -> StylePreset:
        try:
            return self.styles[style_id]
        except KeyError as exc:
            raise KeyError(f"unknown style preset: {style_id}") from exc

    def ids(self) -> list[str]:
        return list(self.styles)


def load_style_presets(root: Path | None = None) -> StylePresetRegistry:
    root = (root or find_project_root()).resolve()
    path = root / "config" / "styles.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    registry = StylePresetRegistry.model_validate(data)
    for preset in registry.styles.values():
        for rel in preset.reference_assets:
            if not (root / rel).is_file():
                raise ValueError(f"{preset.id}: reference asset does not exist: {rel}")
        for rel in preset.source_files:
            if not (root / rel).is_file():
                raise ValueError(f"{preset.id}: source file does not exist: {rel}")
        texture_asset = preset.compositing.texture.asset
        if texture_asset and not (root / texture_asset).is_file():
            raise ValueError(f"{preset.id}: texture asset does not exist: {texture_asset}")
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List or export the two core style presets")
    parser.add_argument("--json", action="store_true", help="dump the full registry as JSON")
    parser.add_argument("--id", help="preset id to export")
    parser.add_argument("--entity", action="store_true", help="with --id: emit workspace style entity JSON")
    args = parser.parse_args(argv)

    registry = load_style_presets()
    if args.id:
        try:
            preset = registry.get(args.id)
        except KeyError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        payload = preset.as_style_entity() if args.entity else preset.model_dump()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.json:
        print(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2))
        return 0
    for preset in registry.styles.values():
        print(f"{preset.id}\t{preset.name}\t{preset.validation_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
