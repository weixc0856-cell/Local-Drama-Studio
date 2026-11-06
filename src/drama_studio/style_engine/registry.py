"""Style Pack registry: load, validate and look up pack directories."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .schemas import StylePack

PACK_FILES = {
    "identity": "style.yaml",
    "image": "image_prompt.yaml",
    "video": "video_prompt.yaml",
    "camera": "camera_profile.yaml",
    "motion": "motion_profile.yaml",
    "lighting": "lighting_profile.yaml",
    "color": "color_profile.yaml",
    "material": "material_profile.yaml",
    "negative": "negative_constraints.yaml",
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def packs_root(root: Path) -> Path:
    return root / "config" / "style_packs"


def load_pack(directory: Path) -> StylePack:
    data = {}
    for key, name in PACK_FILES.items():
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"missing {name} in {directory}")
        data[key] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return StylePack.model_validate(data)


def validate_pack(pack: StylePack, directory: Path) -> list[str]:
    issues: list[str] = []
    style = pack.identity
    expected = f"{style.group}.{directory.name}"
    if style.id != expected:
        issues.append(f"id {style.id!r} does not match path {expected!r}")
    if not SEMVER.match(style.version):
        issues.append(f"version {style.version!r} is not semver")
    if len(pack.color.saturation_range) != 2:
        issues.append("saturation_range must have two values")
    if len(pack.color.edge_density_range) != 2:
        issues.append("edge_density_range must have two values")
    for anchor in pack.color.anchors:
        if not HEX.match(anchor.hex):
            issues.append(f"bad hex {anchor.hex!r} for {anchor.name!r}")
    if pack.video.secondary_limit > 2:
        issues.append("secondary_limit above 2 degrades Wan motion")
    for move in pack.camera.allowed_moves:
        if not move:
            issues.append("empty camera move")
    return issues


def load_all(root: Path) -> dict[str, StylePack]:
    base = packs_root(root)
    packs: dict[str, StylePack] = {}
    for directory in sorted(base.glob("*/*")):
        if not directory.is_dir():
            continue
        pack = load_pack(directory)
        issues = validate_pack(pack, directory)
        if issues:
            raise ValueError(f"{directory}: " + "; ".join(issues))
        if pack.identity.id in packs:
            raise ValueError(f"duplicate style id {pack.identity.id!r}")
        packs[pack.identity.id] = pack
    return packs


def list_packs(root: Path, group: str | None = None) -> list[StylePack]:
    packs = load_all(root)
    if group:
        return [p for p in packs.values() if p.identity.group == group]
    return list(packs.values())


def get_pack(root: Path, style_id: str) -> StylePack:
    packs = load_all(root)
    if style_id not in packs:
        raise KeyError(f"unknown style id {style_id!r}; known: {sorted(packs)}")
    return packs[style_id]
