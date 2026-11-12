"""Font configuration and integrity checks for local video builds.

Fonts are read from ``config/fonts.yaml`` and checked against the asset
manifest. Missing files or SHA-256 mismatches fail loudly; a build must not
silently fall back to a system font.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from drama_studio.config import find_project_root


class FontConfigurationError(RuntimeError):
    """Raised when a configured local font is missing or altered."""


@dataclass(frozen=True)
class FontFace:
    font_key: str
    weight: str
    path: Path
    family: str
    postscript_name: str
    sha256: str
    ass_bold: int

    @property
    def ass_name(self) -> str:
        return self.family


@dataclass(frozen=True)
class FontRole:
    name: str
    font_key: str
    weights: tuple[str, ...]
    default_weight: str
    size_px: int
    size_range_px: tuple[int, int] | None
    line_gap_px: int | None
    margin_bottom_px: int
    outline_px: int
    backplate_allowed: bool
    integration: str


@dataclass(frozen=True)
class FontConfig:
    root: Path
    manifest_path: Path
    faces: dict[tuple[str, str], FontFace]
    roles: dict[str, FontRole]

    def role(self, name: str) -> FontRole:
        try:
            return self.roles[name]
        except KeyError as exc:
            raise FontConfigurationError(f"Unknown font role: {name}") from exc

    def face(self, role: str | FontRole, weight: str | None = None) -> FontFace:
        spec = self.role(role) if isinstance(role, str) else role
        chosen = weight or spec.default_weight
        if chosen not in spec.weights:
            raise FontConfigurationError(
                f"Role {spec.name} does not allow weight {chosen}; allowed: {spec.weights}"
            )
        try:
            return self.faces[(spec.font_key, chosen)]
        except KeyError as exc:
            raise FontConfigurationError(
                f"Missing font face {spec.font_key}/{chosen}"
            ) from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_font_config(root: Path | None = None) -> FontConfig:
    root = (root or find_project_root()).resolve()
    config_path = root / "config" / "fonts.yaml"
    if not config_path.is_file():
        raise FontConfigurationError(f"Missing font config: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FontConfigurationError(f"Font config must be a mapping: {config_path}")

    manifest_path = root / raw.get("manifest", "assets/fonts/font_manifest.json")
    if not manifest_path.is_file():
        raise FontConfigurationError(f"Missing font manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_fonts = {item["asset_id"]: item for item in manifest.get("fonts", [])}

    faces: dict[tuple[str, str], FontFace] = {}
    for font_key, spec in (raw.get("fonts") or {}).items():
        asset_id = spec.get("asset_id")
        item = manifest_fonts.get(asset_id)
        if item is None:
            raise FontConfigurationError(
                f"Font asset {asset_id} for {font_key} is absent from {manifest_path}"
            )
        for weight_data in item.get("selected_weights", []):
            weight = weight_data["weight"].lower()
            path = (root / weight_data["file"]).resolve()
            if not path.is_file():
                raise FontConfigurationError(
                    f"Configured font missing: {font_key}/{weight}: {path}"
                )
            actual = _sha256(path)
            if actual != weight_data["sha256"]:
                raise FontConfigurationError(
                    f"Font SHA-256 mismatch: {font_key}/{weight}: {path} "
                    f"expected {weight_data['sha256']}, got {actual}"
                )
            faces[(font_key, weight)] = FontFace(
                font_key=font_key,
                weight=weight,
                path=path,
                family=weight_data["family"],
                postscript_name=weight_data["postscript_name"],
                sha256=actual,
                ass_bold=-1 if weight == "bold" else 0,
            )

    roles: dict[str, FontRole] = {}
    for name, spec in (raw.get("roles") or {}).items():
        font_key = spec["font"]
        weights = tuple(w.lower() for w in spec.get("weights", ()))
        default_weight = spec.get("default_weight", weights[0] if weights else "")
        if not weights:
            raise FontConfigurationError(f"Role {name} has no weights")
        if default_weight not in weights:
            raise FontConfigurationError(
                f"Role {name} default_weight {default_weight} is not in {weights}"
            )
        for weight in weights:
            if (font_key, weight) not in faces:
                raise FontConfigurationError(
                    f"Role {name} references missing font face {font_key}/{weight}"
                )
        raw_range = spec.get("size_range_px")
        size_range = tuple(raw_range) if raw_range else None
        if size_range is not None and len(size_range) != 2:
            raise FontConfigurationError(f"Role {name} size_range_px must have two values")
        roles[name] = FontRole(
            name=name,
            font_key=font_key,
            weights=weights,
            default_weight=default_weight,
            size_px=int(spec.get("size_px", 56)),
            size_range_px=size_range,
            line_gap_px=int(spec["line_gap_px"]) if spec.get("line_gap_px") else None,
            margin_bottom_px=int(spec.get("margin_bottom_px", 0)),
            outline_px=int(spec.get("outline_px", 0)),
            backplate_allowed=bool(spec.get("backplate_allowed", False)),
            integration=str(spec.get("integration", "preview_only")),
        )

    return FontConfig(root=root, manifest_path=manifest_path, faces=faces, roles=roles)
