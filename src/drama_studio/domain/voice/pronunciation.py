"""Phrase-level pronunciation layers for classical Chinese narration.

Four text layers are kept strictly apart:

``source_text``   the authored original (often traditional);
``display_text``  subtitles, never rewritten;
``tts_text``      the simplified text handed to the engine before fixes;
``acoustic_text`` ``tts_text`` after safe homophone aliases.

The alias engine only changes ``acoustic_text``. Display and source text stay
byte-identical, so subtitles cannot "fix" a pronunciation by changing words.
Every alias starts as ``candidate`` and needs an audio test plus human approval
before it can be ``verified``; the validator enforces that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from drama_studio.config import find_project_root

_CJK = re.compile(r"[㐀-鿿]")
_PINYIN = re.compile(r"^[a-züāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ0-9·\s]+$")


class Capabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_phoneme_control: bool
    api_pinyin_control: bool
    pitch_control: bool
    duration_control: bool
    note: str = ""
    acoustic_substitution: bool = True
    display_text_protected: bool = True
    substitution_method: str = "curated homophone alias, acoustic layer only"


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,31}$")
    phrase: str = Field(min_length=2, max_length=12)
    pinyin: str = Field(min_length=2, max_length=64)
    category: Literal["polyphone", "proper_noun", "common", "variant"]
    note: str = Field(default="", max_length=300)
    variants: list[str] = Field(default_factory=list, max_length=6)
    tts_alias: str | None = Field(
        default=None, min_length=2, max_length=12,
        description="acoustic-only homophone text; display_text is never changed",
    )
    status: Literal["candidate", "verified", "rejected"] = "candidate"
    context: str = Field(default="", max_length=300)
    audio_test: str = Field(default="NOT_RUN", max_length=40)
    human_review: str = Field(default="PENDING", max_length=40)

    @model_validator(mode="after")
    def _valid(self) -> "Entry":
        if _CJK.search(self.pinyin) or not _PINYIN.match(self.pinyin):
            raise ValueError(f"{self.phrase}: pinyin must be latin pinyin, got {self.pinyin!r}")
        length = len(self.phrase)
        for variant in self.variants:
            if len(variant) != length or variant == self.phrase:
                raise ValueError(
                    f"{self.phrase}: variant {variant!r} must have the same length "
                    f"({length}) and differ from the phrase"
                )
        if self.tts_alias is not None:
            if len(self.tts_alias) != length:
                raise ValueError(
                    f"{self.phrase}: tts_alias {self.tts_alias!r} must have the same "
                    f"length ({length}) so audio and subtitle stay aligned"
                )
            if any(not _CJK.match(char) for char in self.tts_alias):
                raise ValueError(f"{self.phrase}: tts_alias must be CJK characters")
            if self.tts_alias in [self.phrase, *self.variants]:
                raise ValueError(f"{self.phrase}: tts_alias must differ from the phrase")
        if self.status == "verified":
            if self.audio_test != "PASS" or self.human_review != "APPROVED":
                raise ValueError(
                    f"{self.phrase}: verified requires audio_test=PASS and "
                    "human_review=APPROVED"
                )
        return self

    @property
    def entry_id(self) -> str:
        return self.id or self.phrase


class Lexicon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    capabilities: Capabilities
    entries: list[Entry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique(self) -> "Lexicon":
        phrases = [entry.phrase for entry in self.entries]
        if len(phrases) != len(set(phrases)):
            raise ValueError("duplicate phrase in pronunciation lexicon")
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate entry id in pronunciation lexicon")
        if any(len(entry.phrase) < 2 for entry in self.entries):
            raise ValueError("single-character entries are not allowed; match by phrase")
        return self


@dataclass(frozen=True)
class Hit:
    phrase: str
    matched: str
    pinyin: str
    category: str
    note: str
    start: int
    end: int
    on: str  # "display" or "tts"
    entry_id: str = ""
    alias: str | None = None
    status: str = "candidate"


@dataclass(frozen=True)
class Replacement:
    entry_id: str
    phrase: str
    matched: str
    alias: str
    pinyin: str
    status: str
    start: int
    end: int


def empty_lexicon() -> Lexicon:
    return Lexicon(
        schema_version="0",
        capabilities=Capabilities(
            api_phoneme_control=False,
            api_pinyin_control=False,
            pitch_control=False,
            duration_control=False,
            note="lexicon unavailable for this root",
        ),
        entries=[],
    )


def load_lexicon(root: Path | None = None, *, allow_missing: bool = False) -> Lexicon:
    root = (root or find_project_root()).resolve()
    path = root / "config" / "pronunciation.yaml"
    if not path.is_file():
        if allow_missing:
            return empty_lexicon()
        raise FileNotFoundError(f"Missing config file: {path}")
    return Lexicon.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def annotate(text: str, lexicon: Lexicon) -> list[Hit]:
    """Longest-match, non-overlapping phrase hits; never rewrites ``text``."""
    # (surface, entry) pairs, longest surface first, so traditional variants
    # and the simplified canonical form match the same lexicon entry.
    pairs: list[tuple[str, Entry]] = []
    for entry in lexicon.entries:
        pairs.append((entry.phrase, entry))
        for variant in entry.variants:
            pairs.append((variant, entry))
    by_first: dict[str, list[tuple[str, Entry]]] = {}
    for surface, entry in pairs:
        by_first.setdefault(surface[0], []).append((surface, entry))
    for bucket in by_first.values():
        bucket.sort(key=lambda item: len(item[0]), reverse=True)
    hits: list[Hit] = []
    index = 0
    while index < len(text):
        bucket = by_first.get(text[index], [])
        match = next((item for item in bucket if text.startswith(item[0], index)), None)
        if match is None:
            index += 1
            continue
        surface, entry = match
        hits.append(
            Hit(
                phrase=entry.phrase,
                matched=surface,
                pinyin=entry.pinyin,
                category=entry.category,
                note=entry.note,
                start=index,
                end=index + len(surface),
                on="display",
                entry_id=entry.entry_id,
                alias=entry.tts_alias,
                status=entry.status,
            )
        )
        index += len(surface)
    return hits


def _match_table(lexicon: Lexicon) -> dict[str, list[tuple[str, Entry]]]:
    pairs: list[tuple[str, Entry]] = []
    for entry in lexicon.entries:
        pairs.append((entry.phrase, entry))
        for variant in entry.variants:
            pairs.append((variant, entry))
    by_first: dict[str, list[tuple[str, Entry]]] = {}
    for surface, entry in pairs:
        by_first.setdefault(surface[0], []).append((surface, entry))
    for bucket in by_first.values():
        bucket.sort(key=lambda item: len(item[0]), reverse=True)
    return by_first


def rewrite_acoustic(text: str, lexicon: Lexicon) -> tuple[str, list[Replacement]]:
    """Longest-match homophone substitution, acoustic layer only.

    The output has the same length as the input because every alias is required
    to match its phrase length. Non-matching text is copied byte-for-byte.
    """
    by_first = _match_table(lexicon)
    pieces: list[str] = []
    replacements: list[Replacement] = []
    last = 0
    index = 0
    while index < len(text):
        bucket = by_first.get(text[index], [])
        match = next((item for item in bucket if text.startswith(item[0], index)), None)
        if match is None:
            index += 1
            continue
        surface, entry = match
        if entry.tts_alias is None or entry.status == "rejected":
            index += len(surface)
            continue
        pieces.append(text[last:index])
        pieces.append(entry.tts_alias)
        replacements.append(
            Replacement(
                entry_id=entry.entry_id,
                phrase=entry.phrase,
                matched=surface,
                alias=entry.tts_alias,
                pinyin=entry.pinyin,
                status=entry.status,
                start=index,
                end=index + len(surface),
            )
        )
        index += len(surface)
        last = index
    pieces.append(text[last:])
    rewritten = "".join(pieces)
    if len(rewritten) != len(text):
        raise ValueError("acoustic rewrite changed the text length; alias length mismatch")
    return rewritten, replacements


def _check_overrides(overrides: list[dict[str, Any]], lexicon: Lexicon, text: str) -> list[dict[str, Any]]:
    known = {entry.phrase for entry in lexicon.entries}
    checked: list[dict[str, Any]] = []
    for item in overrides:
        if not isinstance(item, dict):
            raise ValueError("pronunciation_overrides entries must be objects")
        phrase = str(item.get("phrase") or "")
        pinyin = str(item.get("pinyin") or "")
        if not phrase or phrase not in text:
            raise ValueError(f"override phrase {phrase!r} does not occur in the line")
        if not pinyin or _CJK.search(pinyin) or not _PINYIN.match(pinyin):
            raise ValueError(f"override for {phrase!r} needs latin pinyin")
        if phrase not in known:
            # Allowed, but it is an explicit extension that must be reviewed.
            pass
        checked.append({"phrase": phrase, "pinyin": pinyin, "note": str(item.get("note") or ""),
                        "in_lexicon": phrase in known})
    return checked


def line_layers(item: Any, lexicon: Lexicon, index: int = 0) -> dict[str, Any]:
    """Split one narration item into text layers without mutating any text."""
    if isinstance(item, dict):
        tts = item.get("tts_text") or item.get("text")
        display = item.get("display_text") or item.get("subtitle_text") or tts
        source = item.get("source_text") or display or tts
        overrides = item.get("pronunciation_overrides") or []
        review = item.get("pronunciation_review") or {"status": "PENDING", "note": ""}
    else:
        source = display = tts = str(item)
        overrides = []
        review = {"status": "PENDING", "note": ""}
    if not isinstance(source, str) or not source.strip():
        raise ValueError(f"line {index}: source_text is empty")
    if not isinstance(tts, str) or not tts.strip():
        raise ValueError(f"line {index}: tts_text is empty")
    if not isinstance(display, str) or not display.strip():
        raise ValueError(f"line {index}: display_text is empty")
    display = display.strip()
    tts = tts.strip()
    checked = _check_overrides(list(overrides), lexicon, display + "\n" + tts)
    display_hits = annotate(display, lexicon)
    tts_hits = [
        Hit(phrase=hit.phrase, matched=hit.matched, pinyin=hit.pinyin,
            category=hit.category, note=hit.note,
            start=hit.start, end=hit.end, on="tts",
            entry_id=hit.entry_id, alias=hit.alias, status=hit.status)
        for hit in annotate(tts, lexicon)
    ]
    acoustic, replacements = rewrite_acoustic(tts, lexicon)
    return {
        "index": index,
        "source_text": source.strip(),
        "display_text": display,
        "tts_text": tts,
        "acoustic_text": acoustic,
        "overrides": checked,
        "hits": [hit.__dict__ for hit in display_hits + tts_hits],
        "replacements": [replacement.__dict__ for replacement in replacements],
        "display_is_source": display == source.strip(),
        "acoustic_differs": acoustic != tts,
        "review": review,
    }


def build_report(lines: list[dict[str, Any]], lexicon: Lexicon) -> dict[str, Any]:
    return {
        "lexicon": "config/pronunciation.yaml",
        "lexicon_available": bool(lexicon.entries),
        "schema_version": lexicon.schema_version,
        "capabilities": lexicon.capabilities.model_dump(),
        "entries": len(lexicon.entries),
        "lines": lines,
        "summary": {
            "lines": len(lines),
            "hit_lines": sum(1 for line in lines if line["hits"]),
            "acoustic_lines": sum(1 for line in lines if line["acoustic_differs"]),
            "acoustic_changes": sum(len(line["replacements"]) for line in lines),
            "overrides": sum(len(line["overrides"]) for line in lines),
            "display_equals_source": all(line["display_is_source"] for line in lines),
            "candidate_aliases": sum(1 for entry in lexicon.entries
                                     if entry.tts_alias and entry.status == "candidate"),
            "verified_aliases": sum(1 for entry in lexicon.entries
                                    if entry.tts_alias and entry.status == "verified"),
            "review_status": (
                "PASS"
                if any(entry.tts_alias for entry in lexicon.entries)
                and all(entry.status == "verified" and entry.human_review == "APPROVED"
                        for entry in lexicon.entries if entry.tts_alias)
                else "PENDING"
            ),
        },
        "note": (
            "谐音替换只作用于 acoustic_text；display_text / source_text 不变。"
            "新映射初始为 candidate，必须通过音频测试与人工复核后才能改为 verified。"
        ),
    }
