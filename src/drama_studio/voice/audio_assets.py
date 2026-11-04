"""Audio asset registry for BGM, SFX and TTS prompts.

The registry is a local JSON file. It is deliberately *not* a second database:
``assets/audio/manifest.json`` is the single source for audio assets. The loader
accepts both the older field names (``id``/``kind``) and the explicit names
(``asset_id``/``asset_type``) so existing records do not need a rewrite.

A production mix may only use assets whose status is ``VERIFIED`` or
``APPROVED`` and whose ``commercial_allowed`` is not false. ``PENDING`` /
``BLOCKED`` assets are allowed only when the caller explicitly opts in.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssetStatus = Literal["DISCOVERED", "TECHNICALLY_VALIDATED", "LICENSE_VERIFIED",
                      "VERIFIED", "APPROVED", "PENDING", "PENDING_REVIEW",
                      "REJECTED", "BLOCKED", "REVOKED", "UNKNOWN"]

READY_STATUSES = {"VERIFIED", "APPROVED"}


class AudioAssetError(RuntimeError):
    pass


class AudioAsset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_id: str = Field(min_length=1, max_length=120)
    asset_type: str = Field(min_length=1, max_length=40)
    path: str = Field(min_length=1, max_length=500)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    duration_ms: int | None = Field(default=None, ge=0)
    license_type: str | None = None
    license_evidence: str | None = None
    commercial_allowed: bool | None = None
    attribution_required: bool = False
    source_url: str | None = None
    status: AssetStatus = "UNKNOWN"

    @model_validator(mode="after")
    def _sha_or_status(self) -> "AudioAsset":
        if self.status in READY_STATUSES and not self.sha256:
            raise ValueError(f"{self.asset_id}: verified asset needs sha256")
        return self

    @property
    def ready(self) -> bool:
        return self.status in READY_STATUSES and self.commercial_allowed is not False


class AudioAssetRegistry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str = "1.0"
    assets: list[AudioAsset] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> "AudioAssetRegistry":
        ids = [a.asset_id for a in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate audio asset_id")
        return self

    def get(self, asset_id: str) -> AudioAsset:
        for asset in self.assets:
            if asset.asset_id == asset_id:
                return asset
        raise AudioAssetError(f"audio asset not found: {asset_id}")

    def resolve(self, asset_id: str, root: Path, *, require_ready: bool = True) -> Path:
        asset = self.get(asset_id)
        if require_ready and not asset.ready:
            raise AudioAssetError(
                f"{asset_id}: status={asset.status}, commercial_allowed={asset.commercial_allowed}; "
                "only VERIFIED/APPROVED assets may enter a production mix"
            )
        path = Path(asset.path)
        path = path if path.is_absolute() else (root / path)
        if not path.is_file():
            raise AudioAssetError(f"{asset_id}: file not found: {path}")
        if asset.sha256:
            actual = _sha256(path)
            if actual != asset.sha256:
                raise AudioAssetError(
                    f"{asset_id}: sha256 mismatch expected {asset.sha256} got {actual}")
        return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalise(item: dict[str, Any]) -> dict[str, Any]:
    data = dict(item)
    if "asset_id" not in data and "id" in data:
        data["asset_id"] = data["id"]
    if "asset_type" not in data and "kind" in data:
        data["asset_type"] = data["kind"]
    return data


def load_registry(path: Path) -> AudioAssetRegistry:
    path = Path(path)
    if not path.is_file():
        raise AudioAssetError(f"audio asset registry not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AudioAssetError(f"cannot read audio asset registry {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AudioAssetError("audio asset registry must be a JSON object")
    assets = [_normalise(item) for item in raw.get("assets") or []]
    return AudioAssetRegistry(
        schema_version=str(raw.get("schema_version") or "1.0"),
        assets=assets,
    )
