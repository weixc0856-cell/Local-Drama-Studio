"""Spoken-text cleaning before TTS.

Director notes belong in metadata, not in the mouth of the narrator. A line such
as ``黄河入海流（majestic, expansive）`` must be spoken as ``黄河入海流``. The
cleaner is deliberately conservative: it removes bracketed stage directions,
Latin words from a Chinese-language project, and stray repeated punctuation,
and it records exactly what it removed so the removal can be audited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

BRACKETS = re.compile(
    r"\([^)]*\)|（[^）]*）|\[[^\]]*\]|【[^】]*】|\*[^*]*\*"
)
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
MULTISPACE = re.compile(r"\s+")
REPEATED_PUNCT = re.compile(r"([，,。.!！？?；;：:])\1+")
LEADING_TRAILING_PUNCT = re.compile(r"^[\s，,。.!！？?；;：:、\-—]+|[\s，,。.!！？?；;：:、\-—]+$")


class TextCleanError(ValueError):
    pass


@dataclass(frozen=True)
class TextAudit:
    original: str
    cleaned: str
    removed: list[str] = field(default_factory=list)
    latin_removed: list[str] = field(default_factory=list)

    def as_record(self) -> dict:
        return {
            "original": self.original,
            "cleaned": self.cleaned,
            "removed": self.removed,
            "latin_removed": self.latin_removed,
        }


def clean_spoken_text(
    text: str,
    *,
    language: str = "zh-CN",
    allow_latin: bool = False,
) -> TextAudit:
    """Return the speakable text plus an audit record.

    ``《...》`` is stripped because it is a title marker, not spoken content; the
    title itself remains outside the brackets. Chinese projects drop Latin words
    unless ``allow_latin`` is explicit, because an English director tag in a
    Chinese line is always a bug, never a performance choice.
    """
    if not isinstance(text, str) or not text.strip():
        raise TextCleanError("empty spoken text")
    original = text
    removed: list[str] = []

    def _strip(match: re.Match[str]) -> str:
        removed.append(match.group(0))
        return ""

    cleaned = BRACKETS.sub(_strip, text)
    if "《" in cleaned or "》" in cleaned:
        removed.append("《》")
        cleaned = cleaned.replace("《", "").replace("》", "")
    latin_removed: list[str] = []
    if language.lower().startswith("zh") and not allow_latin:
        for match in LATIN_WORD.finditer(cleaned):
            latin_removed.append(match.group(0))
        cleaned = LATIN_WORD.sub("", cleaned)
    cleaned = MULTISPACE.sub(" ", cleaned)
    cleaned = REPEATED_PUNCT.sub(r"\1", cleaned)
    cleaned = LEADING_TRAILING_PUNCT.sub("", cleaned).strip()
    if not cleaned:
        raise TextCleanError(f"spoken text is empty after cleaning: {original!r}")
    return TextAudit(original=original, cleaned=cleaned,
                     removed=removed, latin_removed=latin_removed)


def assert_no_director_tags(text: str) -> None:
    """Fail fast when obvious production metadata is still in the line."""
    lowered = text.lower()
    tags = ("emotion", "delivery", "tone:", "style:", "camera", "resolute",
            "contemplative", "majestic", "expansive", "solemn", "gentle")
    hit = [tag for tag in tags if tag in lowered]
    if hit:
        raise TextCleanError(f"director metadata still present: {hit} in {text!r}")
