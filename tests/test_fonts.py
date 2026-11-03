from __future__ import annotations

from pathlib import Path

import pytest

from drama_studio.fonts import FontConfigurationError, load_font_config

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/fonts/font_manifest.json"


def _fonts_installed() -> bool:
    import json

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return all((ROOT / item["file"]).is_file() for font in data["fonts"] for item in font["selected_weights"])


pytestmark = pytest.mark.skipif(
    not _fonts_installed(),
    reason="font OTFs not installed; run scripts/fetch_fonts.py",
)


def test_font_config_loads_all_six_faces() -> None:
    cfg = load_font_config()
    assert len(cfg.faces) == 6
    assert cfg.face("subtitle").ass_name == "Source Han Sans CN"
    assert cfg.face("subtitle").ass_bold == 0
    assert cfg.face("classical_title").ass_name == "Source Han Serif CN"
    assert cfg.face("classical_title").ass_bold == -1
    assert cfg.face("poetry_body").ass_name == "Source Han Serif CN Medium"
    assert cfg.role("subtitle").integration == "formal_build"
    assert cfg.role("classical_title").integration == "preview_only"


def test_missing_font_fails_loudly(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "assets/fonts").mkdir(parents=True)
    manifest = {
        "fonts": [
            {
                "asset_id": "FONT-TEST",
                "selected_weights": [
                    {
                        "weight": "Regular",
                        "file": "assets/fonts/missing.otf",
                        "family": "Test Font",
                        "postscript_name": "TestFont-Regular",
                        "sha256": "0" * 64,
                    }
                ],
            }
        ]
    }
    import json
    (tmp_path / "assets/fonts/font_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "config/fonts.yaml").write_text(
        """
manifest: assets/fonts/font_manifest.json
fonts:
  test:
    asset_id: FONT-TEST
roles:
  subtitle:
    font: test
    weights: [regular]
    default_weight: regular
""",
        encoding="utf-8",
    )
    with pytest.raises(FontConfigurationError, match="Configured font missing"):
        load_font_config(tmp_path)


def test_font_hash_mismatch_fails_loudly(tmp_path: Path) -> None:
    actual = (Path(__file__).resolve().parents[1] / "assets/fonts/source-han-sans-cn/SourceHanSansCN-Regular.otf").resolve()
    (tmp_path / "config").mkdir()
    (tmp_path / "assets/fonts").mkdir(parents=True)
    manifest = {
        "fonts": [
            {
                "asset_id": "FONT-TEST",
                "selected_weights": [
                    {
                        "weight": "Regular",
                        "file": str(actual),
                        "family": "Test Font",
                        "postscript_name": "TestFont-Regular",
                        "sha256": "0" * 64,
                    }
                ],
            }
        ]
    }
    import json
    (tmp_path / "assets/fonts/font_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "config/fonts.yaml").write_text(
        """
manifest: assets/fonts/font_manifest.json
fonts:
  test:
    asset_id: FONT-TEST
roles:
  subtitle:
    font: test
    weights: [regular]
    default_weight: regular
""",
        encoding="utf-8",
    )
    with pytest.raises(FontConfigurationError, match="SHA-256 mismatch"):
        load_font_config(tmp_path)
