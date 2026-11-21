import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/fonts/font_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


ALLOWED_UPSTREAMS = (
    "https://github.com/adobe-fonts/",
    "https://github.com/lxgw/",
    "https://github.com/TrionesType/",
    "https://raw.githubusercontent.com/lxgw/",
    "https://raw.githubusercontent.com/TrionesType/",
    "https://raw.githubusercontent.com/google/fonts/",
)


def test_manifest_describes_every_selected_weight() -> None:
    data = _manifest()
    weights = [
        item for font in data["fonts"] for item in font.get("selected_weights", [])
    ]
    # The registry grows as verified OFL families are added; assert the invariants,
    # not a frozen count.
    assert len(weights) >= 6
    for item in weights:
        path = (ROOT / item["file"]).resolve()
        assert path.is_relative_to((ROOT / "assets/fonts").resolve())
        assert len(item["sha256"]) == 64
        assert path.suffix.lower() in {".otf", ".ttf"}


def test_manifest_has_deterministic_upstream_urls() -> None:
    for font in _manifest()["fonts"]:
        archive = font.get("archive") or {}
        if archive:
            assert archive.get("url", "").startswith(ALLOWED_UPSTREAMS), font["asset_id"]
            assert len(archive.get("sha256", "")) == 64
            assert archive.get("file")
        else:
            # Fonts published as individual files carry a pinned URL per weight.
            for item in font["selected_weights"]:
                assert item.get("url", "").startswith(ALLOWED_UPSTREAMS), font["asset_id"]
                assert len(item["sha256"]) == 64
        if font.get("license_url"):
            assert font["license_url"].startswith(ALLOWED_UPSTREAMS), font["asset_id"]


def test_fetch_script_exists() -> None:
    assert (ROOT / "scripts/fetch_fonts.py").is_file()


def test_installed_fonts_match_manifest_when_present() -> None:
    for font in _manifest()["fonts"]:
        for item in font["selected_weights"]:
            path = (ROOT / item["file"]).resolve()
            if not path.is_file():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == item["sha256"], item["file"]
