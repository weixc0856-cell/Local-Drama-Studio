import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/fonts/font_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_describes_every_selected_weight() -> None:
    data = _manifest()
    weights = [
        item for font in data["fonts"] for item in font.get("selected_weights", [])
    ]
    assert len(weights) == 6
    for item in weights:
        path = (ROOT / item["file"]).resolve()
        assert path.is_relative_to((ROOT / "assets/fonts").resolve())
        assert len(item["sha256"]) == 64
        assert path.suffix.lower() == ".otf"


def test_manifest_has_deterministic_archive_urls() -> None:
    for font in _manifest()["fonts"]:
        archive = font.get("archive") or {}
        assert archive.get("url", "").startswith("https://github.com/adobe-fonts/")
        assert len(archive.get("sha256", "")) == 64
        assert archive.get("file")


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
