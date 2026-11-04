"""Recitation modes: speed, pauses and sentence splitting — no character edits.

Three levels are kept strictly apart:

1. ``narration`` — ordinary narration.
2. ``recitation`` — standard Putonghua recitation with line-level pacing.
3. ``classical_recitation`` — slower line pacing plus intra-line breath pauses.

``chant`` (a real melody with pitch and note durations) is declared unsupported
in ``config/audio.yaml``: the SFT service has no pitch or duration control. This
module will not approximate it and will not label a plain recitation as chant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..config import find_project_root, load_audio

ModeName = Literal["narration", "recitation", "classical_recitation", "chant"]


class ModeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool = True
    reason: str = ""
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    leading_ms: int = Field(default=300, ge=0, le=5000)
    line_pause_ms: int = Field(default=800, ge=0, le=5000)
    intra_line_pause_ms: int = Field(default=0, ge=0, le=3000)
    split_at_punctuation: bool = False
    punctuation: str = "，、；："
    metrical_split: bool = False
    metrical_pause_ms: int = Field(default=220, ge=0, le=1000)


class RecitationError(RuntimeError):
    pass


DEFAULTS: dict[str, dict[str, Any]] = {
    "narration": {"speed": 1.0, "leading_ms": 300, "line_pause_ms": 800},
    "recitation": {"speed": 0.92, "leading_ms": 450, "line_pause_ms": 950,
                   "intra_line_pause_ms": 0, "split_at_punctuation": False,
                   "punctuation": "，、；：？。！"},
    "classical_recitation": {"speed": 0.82, "leading_ms": 550, "line_pause_ms": 1000,
                             "intra_line_pause_ms": 0, "split_at_punctuation": False,
                             "punctuation": "，、；：？。！",
                             "metrical_split": False, "metrical_pause_ms": 0},
    "chant": {"supported": False, "reason": "CosyVoice-300M-SFT 无音高/旋律/时长控制接口"},
}


def load_modes(root: Path | None = None) -> dict[str, ModeSpec]:
    root = (root or find_project_root()).resolve()
    raw = (load_audio(root).get("narration_modes") or {})
    modes: dict[str, ModeSpec] = {}
    for name, defaults in DEFAULTS.items():
        data = dict(defaults)
        if isinstance(raw.get(name), dict):
            data.update(raw[name])
        modes[name] = ModeSpec(**data)
    return modes


def mode_spec(root: Path | None, mode: str) -> ModeSpec:
    modes = load_modes(root)
    if mode not in modes:
        raise RecitationError(f"未知诵读模式：{mode}；可选 {sorted(modes)}")
    spec = modes[mode]
    if not spec.supported:
        raise RecitationError(
            f"{mode}：{spec.reason or '当前模型不支持'}。不得用普通朗诵冒充吟唱。"
        )
    return spec


_CLAUSE_MARKS = "，。！？；：、,.!?;:"


def breath_text(text: str) -> str:
    """Insert a dash breath inside a 7- or 5-character clause.

    The audio is still one whole-line request; the dash is punctuation the
    frontend turns into a pause. No audio is cut into separate files.
    """
    clauses: list[str] = []
    buffer = ""
    for char in text:
        buffer += char
        if char in _CLAUSE_MARKS:
            clauses.append(buffer)
            buffer = ""
    if buffer:
        clauses.append(buffer)
    out: list[str] = []
    for clause in clauses:
        core = clause
        tail = ""
        while core and core[-1] in _CLAUSE_MARKS:
            tail = core[-1] + tail
            core = core[:-1]
        if "——" not in core:
            if len(core) == 7:
                core = core[:4] + "——" + core[4:]
            elif len(core) == 5:
                core = core[:2] + "——" + core[2:]
        out.append(core + tail)
    return "".join(out)


def split_line(text: str, spec: ModeSpec) -> list[dict[str, Any]]:
    """One whole-line part; retained for callers that still read ``parts``."""
    return [{"text": breath_text(text), "pause_after_ms": 0}]


def plan_line(text: str, spec: ModeSpec) -> dict[str, Any]:
    breath = breath_text(text)
    return {
        "text": text,
        "breath_text": breath,
        "parts": [{"text": breath, "pause_after_ms": 0}],
        "intra_pause_ms": 0,
        "part_count": 1,
    }


def pitch_supported(root: Path | None = None) -> bool:
    """The SFT service has no pitch control; this is a hard capability boundary."""
    return False
