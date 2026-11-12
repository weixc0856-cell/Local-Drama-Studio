from __future__ import annotations

import hashlib
import json

from drama_studio.application.voice.audio_assets import load_registry


def test_template_aliases_are_accepted(tmp_path):
    """The v2 template uses asset_id/type/license/attribution_text/tags."""
    wav = tmp_path / "tone.wav"
    wav.write_bytes(b"fake-audio-bytes")
    payload = {
        "schema_version": "2.0.0",
        "assets": [{
            "asset_id": "bgm_tpl_01",
            "name": "Sunny Days",
            "artist": "Anno Domini Beats",
            "source_platform": "youtube_studio",
            "source_url": "https://studio.youtube.com",
            "style": "shinkai_scenery",
            "type": "bgm",
            "path": str(wav),
            "sha256": hashlib.sha256(b"fake-audio-bytes").hexdigest(),
            "duration_ms": 1000,
            "license": "CC0-1.0",
            "commercial_allowed": True,
            "attribution_required": False,
            "attribution_text": "",
            "status": "APPROVED",
            "default_gain_db": -16.0,
            "tags": ["bright", "acoustic_guitar"],
        }],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    registry = load_registry(manifest)
    asset = registry.assets[0]
    assert asset.asset_id == "bgm_tpl_01"
    assert asset.asset_type == "bgm"
    assert asset.license_type == "CC0-1.0"
    assert asset.style_tags == ["bright", "acoustic_guitar"]
    assert registry.resolve("bgm_tpl_01", tmp_path).is_file()


def test_attribution_text_alias_feeds_attribution(tmp_path):
    payload = {
        "assets": [{
            "id": "bgm_attr", "kind": "bgm", "path": "x.wav",
            "status": "PENDING", "attribution_text": "Track by Someone",
        }],
    }
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    asset = load_registry(manifest).assets[0]
    assert asset.attribution == "Track by Someone"
