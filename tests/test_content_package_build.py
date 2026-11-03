from __future__ import annotations

import json
from pathlib import Path

from drama_studio.content_package import build_content_package

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "literary_intelligence" / "tests" / "fixtures" / "corpus_short"


def test_build_package_from_short_corpus(tmp_path: Path) -> None:
    out = tmp_path / "content_package.json"
    data = build_content_package(CORPUS, out)
    assert out.is_file()
    assert data["work"]["title"] == "测试短文本"
    assert data["positioning"]["target_text"] == "白日依山尽"
    assert len(data["video"]["scene_plan"]) == 2
    assert len(data["video"]["subtitle_segments"]) == 2
    assert data["video"]["subtitle_segments"][0]["claim_refs"] == ["short_original_001"]
    assert data["provenance"]["claim_refs"] == ["short_original_001"]
    assert any("unreviewed" in warning for warning in data["provenance"]["warnings"])
    assert data["provenance"]["verification_status"] == "draft"


def test_package_uses_only_evidence_checked_claims(tmp_path: Path) -> None:
    source = json.loads((CORPUS / "source_registry.json").read_text(encoding="utf-8"))
    claims = json.loads((CORPUS / "claims.json").read_text(encoding="utf-8"))
    bad = dict(claims[0])
    bad["claim_id"] = "bad_001"
    bad["source_refs"] = ["src_missing"]
    claims.append(bad)
    (tmp_path / "source_registry.json").write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "claims.json").write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    for name in ("original_text.txt", "normalized_text.txt", "segments.json", "normalization_map.json"):
        (tmp_path / name).write_bytes((CORPUS / name).read_bytes())

    data = build_content_package(tmp_path, tmp_path / "pkg.json")
    assert "bad_001" not in data["provenance"]["claim_refs"]
    assert any("bad_001" in warning for warning in data["provenance"]["warnings"])
