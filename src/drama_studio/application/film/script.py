"""Text → narration → director beats.

Any input text must be able to enter the film chain without hand-authoring a
beats file. This module does the deterministic part that does not need a model:

* split the text at sentence and clause punctuation, with paragraph breaks kept;
* turn each line into a narration segment with a pause derived from punctuation;
* place shots with a cinematic grammar (establish → move in → detail → release)
  while staying inside the style pack's allowed camera moves.

It deliberately does not invent facts or claim the result is a screenplay
written by an author. An LLM can refine the beats later; the contract and the
timeline do not change.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from drama_studio.paths import config_root
from drama_studio.application.film.config import ProductionSettings
from drama_studio.domain.film.schemas import ArtDirection, CameraLanguage, CharacterDesign, EnvironmentDesign, Narration, NarrationSegment, Screenplay, SourceText, VisualBible
from drama_studio.application.film.storyboard import plan_storyboard

SENTENCE_END = "。！？!?；;"
CLAUSE_END = "，,、：:"
PERSON_WORDS = ("人", "我", "予", "吾", "君", "客", "舟人", "渔", "翁", "女", "郎", "士", "夫")
CAMERA_CYCLE = ("crane", "dolly_in", "tracking", "static", "dolly_out", "pan")
SHOT_SIZE_CYCLE = ("ews", "ws", "ms", "ws", "cu", "ws")
MOTION_BY_CAMERA = {
    "crane": "camera_descent",
    "dolly_in": "camera_push_in",
    "dolly_out": "camera_pull_out",
    "tracking": "camera_lateral",
    "pan": "camera_lateral",
    "tilt": "camera_tilt_up",
    "static": "environment_drift",
}
SECONDARY_BY_WORD = (
    (("云", "雾", "霭"), "cloud_drift"),
    (("江", "河", "湖", "海", "水", "波", "浪"), "water_flow"),
    (("风", "树", "木", "草", "竹", "柳"), "branch_sway"),
    (("雨", "雪"), "weather_drift"),
)


class ScriptError(RuntimeError):
    pass


def _split_long(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    parts = re.split(f"([{re.escape(CLAUSE_END)}])", sentence)
    merged: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if len(current) + len(part) > max_chars and current:
            merged.append(current)
            current = part
        else:
            current += part
    if current:
        merged.append(current)
    words: list[str] = []
    for chunk in merged:
        if len(chunk) <= max_chars or " " not in chunk:
            words.append(chunk)
            continue
        current_word = ""
        for word in chunk.split(" "):
            candidate = (current_word + " " + word).strip()
            if len(candidate) > max_chars and current_word:
                words.append(current_word)
                current_word = word
            else:
                current_word = candidate
        if current_word:
            words.append(current_word)
    return words


def split_text(text: str, *, max_chars: int = 28, min_chars: int = 6) -> list[str]:
    """Split prose or poetry into spoken lines without changing a character.

    Paragraph breaks are hard boundaries. A short clause is merged with the next
    one so a two-character poem line does not become a two-second shot.
    """
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise ScriptError("source text is empty")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    if not paragraphs:
        paragraphs = [normalized]
    lines: list[str] = []
    for paragraph in paragraphs:
        raw = re.split(r"\n", paragraph)
        for block in raw:
            block = block.strip()
            if not block:
                continue
            pieces = re.split(f"(?<=[{re.escape(SENTENCE_END)}])", block)
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    continue
                for chunk in _split_long(piece, max_chars):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    if lines and len(lines[-1]) < min_chars and len(lines[-1]) + len(chunk) <= max_chars:
                        lines[-1] += chunk
                    else:
                        lines.append(chunk)
    return lines


def _pause_after(line: str) -> int:
    if line.endswith(tuple("。！？!?")):
        return 900
    if line.endswith(tuple("；;")):
        return 650
    if line.endswith(tuple("，,、：:")):
        return 350
    return 500


def build_narration(
    project_id: str,
    lines: list[str],
    *,
    language: str = "zh-CN",
    speed: float = 1.0,
    subtitle_text: list[str] | None = None,
) -> Narration:
    if not lines:
        raise ScriptError("no lines")
    segments = []
    for index, line in enumerate(lines, start=1):
        pause = _pause_after(line)
        if index == len(lines):
            pause = 1200
        segments.append(NarrationSegment(
            id=f"N{index:03d}",
            text=line,
            subtitle_text=(subtitle_text[index - 1] if subtitle_text else None),
            pause_after_ms=pause,
            speed=speed,
        ))
    return Narration(project_id=project_id, language=language, segments=segments)


def build_screenplay(project_id: str, title: str, text: str, theme: str | None = None) -> Screenplay:
    paragraphs = [part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    return Screenplay(
        project_id=project_id,
        logline=f"{title}：{text.strip()[:60]}",
        theme=theme or title,
        acts=[f"第 {index} 段" for index in range(1, min(len(paragraphs), 6) + 1)] or ["全篇"],
        emotion_curve=["起", "承", "转", "合"],
    )


def build_bible(project_id: str, title: str, text: str, pack: Any | None) -> VisualBible:
    if pack is not None:
        palette = [anchor.name for anchor in pack.color.anchors]
        style = pack.image.identity
        lighting = f"{pack.lighting.key}，{pack.lighting.temperature} temperature，{pack.lighting.contrast} contrast"
        lens = pack.camera.preferred_lens_mm
        dof = pack.camera.dof_strategy
        allowed = list(pack.camera.allowed_moves)
    else:
        palette = ["墨黑", "宣白", "赭石"]
        style = "traditional Chinese ink wash"
        lighting = "soft atmospheric light, low contrast"
        lens = 35
        dof = "deep"
        allowed = list(CAMERA_CYCLE)
    has_person = any(word in text for word in PERSON_WORDS)
    protagonist = CharacterDesign(
        identity="poet or scholar in period dress" if has_person else "no recurring character",
        clothing="traditional robe" if has_person else None,
    )
    landscape = title if not any(word in title for word in ("楼", "阁", "亭", "宫")) else None
    return VisualBible(
        project_id=project_id,
        art_direction=ArtDirection(
            style=style,
            period="中国古代",
            aspect_ratio="9:16",
            lighting=lighting,
            palette=palette,
        ),
        protagonist=protagonist,
        environment=EnvironmentDesign(
            architecture=title if title and landscape is None else None,
            landscape=landscape or "mountains, river and sky",
            weather=None,
            atmosphere="layered distance, atmospheric haze",
        ),
        camera_language=CameraLanguage(
            movement="slow_and_deliberate",
            depth="layered",
            transitions="motivated_cuts",
        ),
    )


def _secondary_motions(text: str) -> list[str]:
    found: list[str] = []
    for words, motion in SECONDARY_BY_WORD:
        if any(word in text for word in words) and motion not in found:
            found.append(motion)
    return found[:2]


def _layers(text: str) -> dict[str, str]:
    if any(word in text for word in ("楼", "阁", "亭", "宫", "台")):
        return {"foreground": "railing and eaves, softly blurred",
                "midground": "traditional timber tower",
                "background": "distant mountains and open sky"}
    if any(word in text for word in ("江", "河", "湖", "海", "水", "波")):
        return {"foreground": "reeds and ripples",
                "midground": "river water and distant shore",
                "background": "layered mountain silhouettes, sky"}
    if any(word in text for word in ("山", "峰", "岭", "岩")):
        return {"foreground": "foreground rocks and pines",
                "midground": "mountain ridge",
                "background": "cloud sea and pale sky"}
    return {"foreground": "mist and foreground branches",
            "midground": "open landscape",
            "background": "distant peaks and sky"}


def build_beats(
    text: str,
    narration: Narration,
    bible: VisualBible,
    *,
    settings: ProductionSettings | None = None,
    allowed_cameras: list[str] | None = None,
    shots_per_scene: int = 6,
    target_duration_seconds: float | None = None,
) -> list[dict[str, Any]]:
    settings = settings or ProductionSettings()
    allowed = [move for move in (allowed_cameras or CAMERA_CYCLE)
               if move in CAMERA_CYCLE]
    if not allowed:
        allowed = ["static"]
    lines = narration.segments
    hint = None
    if target_duration_seconds and lines:
        hint = max(settings.min_shot_seconds,
                   min(settings.max_shot_seconds,
                       (target_duration_seconds - settings.leading_silence_ms / 1000.0)
                       / len(lines)))
    beats: list[dict[str, Any]] = []
    for index, segment in enumerate(lines):
        scene = index // max(1, shots_per_scene) + 1
        camera = allowed[index % len(allowed)]
        shot_size = SHOT_SIZE_CYCLE[index % len(SHOT_SIZE_CYCLE)]
        layers = _layers(segment.text)
        beats.append({
            "scene_id": f"SC{scene:02d}",
            "duration_seconds": round(hint or max(settings.min_shot_seconds,
                                                  min(settings.max_shot_seconds,
                                                      3.5 + len(segment.text) / 14.0)), 2),
            "shot_size": shot_size,
            "move": camera,
            "lens_mm": 35,
            "dof": "deep",
            "motion_primary": MOTION_BY_CAMERA.get(camera, "environment_drift"),
            "motion_direction": (
                "left_to_right" if camera in ("pan", "tracking") else
                "toward_camera" if camera == "dolly_in" else
                "away_from_camera" if camera == "dolly_out" else
                "static"
            ),
            "secondary": _secondary_motions(segment.text),
            "character_in_frame": any(word in segment.text for word in PERSON_WORDS),
            "narration_ids": [segment.id],
            "lighting": bible.art_direction.lighting,
            "environment": f"SC{scene:02d}",
            "foreground": layers["foreground"],
            "midground": layers["midground"],
            "background": layers["background"],
            "keyframe_note": "layered depth, period-accurate architecture, no text",
        })
    return beats


def init_project(
    root: Path,
    project_id: str,
    *,
    title: str,
    text: str,
    author: str = "",
    dynasty: str | None = None,
    style_id: str = "oriental.ink_wash",
    target_duration_seconds: float | None = None,
    language: str = "zh-CN",
    speed: float = 1.0,
    force: bool = False,
) -> dict[str, Any]:
    directory = root / "projects" / project_id
    if (directory / "project.json").is_file() and not force:
        raise ScriptError(f"project already exists: {directory}; use --force to replace")
    directory.mkdir(parents=True, exist_ok=True)
    from drama_studio.domain.style import get_pack

    try:
        pack = get_pack(config_root(root), style_id)
    except KeyError as exc:
        raise ScriptError(str(exc)) from exc

    settings = ProductionSettings()
    lines = split_text(text)
    narration = build_narration(project_id, lines, language=language, speed=speed)
    screenplay = build_screenplay(project_id, title, text)
    bible = build_bible(project_id, title, text, pack)
    beats = build_beats(
        text, narration, bible, settings=settings,
        allowed_cameras=list(pack.camera.allowed_moves),
        target_duration_seconds=target_duration_seconds,
    )
    storyboard = plan_storyboard(project_id, beats, bible)

    meta = {
        "project_id": project_id,
        "title": title,
        "author": author,
        "dynasty": dynasty,
        "aspect_ratio": "9:16",
        "target_duration_seconds": target_duration_seconds,
        "language": language,
        "created_at": date.today().isoformat(),
        "visual": {"style_id": style_id, "style_version": pack.identity.version},
        "production": settings.model_dump(mode="json"),
        "notes": "由 drama film init 从文本生成；分镜可人工修改后重新 validate。",
    }
    (directory / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    (directory / "source.json").write_text(json.dumps(SourceText(
        project_id=project_id, title=title, author=author, dynasty=dynasty, text=text
    ).model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "screenplay.json").write_text(
        json.dumps(screenplay.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (directory / "narration.json").write_text(
        json.dumps(narration.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (directory / "visual_bible.yaml").write_text(
        yaml.safe_dump(bible.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (directory / "beats.json").write_text(
        json.dumps(beats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "storyboard.json").write_text(
        json.dumps(storyboard.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return {
        "project_id": project_id,
        "directory": str(directory),
        "lines": len(lines),
        "shots": len(storyboard.shots),
        "target_seconds": round(sum(shot.duration_seconds for shot in storyboard.shots), 2),
        "style_id": style_id,
    }
