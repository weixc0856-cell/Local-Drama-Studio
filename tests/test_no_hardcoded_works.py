from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("春江", "洛神", "曹植", "山海经", "山海經", "翩若")
SCAN_DIRS = (
    ROOT / "src" / "drama_studio",
    ROOT / "literary_intelligence" / "harness",
    ROOT / "literary_intelligence" / "schemas",
)
SUFFIXES = {".py", ".js", ".css", ".html"}


def test_generic_code_has_no_work_names() -> None:
    hits: list[str] = []
    for base in SCAN_DIRS:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUFFIXES:
                continue
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for word in FORBIDDEN:
                if word in text:
                    hits.append(f"{path.relative_to(ROOT)}: {word}")
    assert not hits, "specific works leaked into generic code: " + "; ".join(hits)
