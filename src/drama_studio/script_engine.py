"""LLM-driven production script and storyboard generation.

The LLM may choose titles, shot grouping and visual descriptions, but narration
text comes from the validated ContentPackage subtitle segments. This keeps every
spoken line traceable to evidence while still producing an editable script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from literary_intelligence.harness.llm_client import chat_json
from literary_intelligence.schemas.content_package import ContentPackage


class ScriptGenerationError(RuntimeError):
    pass


class DraftShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["image"] = "image"
    scene_prompt: str = Field(min_length=4, max_length=1200)
    duration_seconds: float = Field(ge=1.0, le=15.0)
    motion: str = Field(default="slow push-in", max_length=80)
    line_indexes: list[int] = Field(min_length=1, max_length=6)


class DraftScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    logline: str = Field(min_length=4, max_length=300)
    line_order: list[int] = Field(default_factory=list, max_length=10)
    shots: list[DraftShot] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def _line_refs(self) -> "DraftScript":
        for shot in self.shots:
            if any(index < 1 for index in shot.line_indexes):
                raise ValueError("line_indexes are 1-based positive integers")
        return self


class ScriptLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str = Field(pattern=r"^line_\d{3}$")
    text: str = Field(min_length=1, max_length=300)
    source_segment_id: str


class ScriptShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(pattern=r"^shot_\d{3}$")
    index: int = Field(ge=1, le=24)
    type: Literal["image", "video"] = "image"
    duration_seconds: float = Field(ge=1.0, le=15.0)
    motion: str = Field(min_length=1, max_length=80)
    scene_prompt: str = Field(min_length=4, max_length=1200)
    visual_prompt: str = Field(min_length=4, max_length=2000)
    negative_prompt: str = Field(default="", max_length=1000)
    line_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _id_matches_index(self) -> "ScriptShot":
        expected = f"shot_{self.index:03d}"
        if self.shot_id != expected:
            raise ValueError(f"shot_id {self.shot_id!r} does not match index {self.index}")
        return self


class ProductionScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    title: str = Field(min_length=1, max_length=80)
    logline: str = Field(min_length=4, max_length=300)
    # A full-length poetry work needs one line per registered stanza and one
    # shot per narrative beat; the caps here match the ContentPackage limits.
    lines: list[ScriptLine] = Field(min_length=1, max_length=60)
    shots: list[ScriptShot] = Field(min_length=1, max_length=24)
    style_id: str | None = None
    style_sha256: str
    package_sha256: str
    model: str
    generated_at: str

    @model_validator(mode="after")
    def _integrity(self) -> "ProductionScript":
        line_ids = [line.line_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("duplicate line_id")
        indexes = [shot.index for shot in self.shots]
        if indexes != list(range(1, len(indexes) + 1)):
            raise ValueError("shot indexes must be contiguous starting at 1")
        known = set(line_ids)
        covered: set[str] = set()
        for shot in self.shots:
            missing = set(shot.line_ids) - known
            if missing:
                raise ValueError(f"{shot.shot_id} references unknown lines: {sorted(missing)}")
            covered.update(shot.line_ids)
        if covered != known:
            raise ValueError("every narration line must be covered by at least one shot")
        return self


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def compose_visual_prompt(style: dict[str, Any], scene_prompt: str) -> str:
    positive = str(style.get("positive_prompt") or "").strip()
    visual = str(style.get("visual_language") or "").strip()
    prefix = "；".join(part for part in (visual, positive) if part)
    return f"{prefix}；{scene_prompt}" if prefix else scene_prompt


def _messages(package: dict[str, Any], style: dict[str, Any]) -> list[dict[str, str]]:
    lines = [
        {"index": index, "segment_id": seg["segment_id"], "text": seg["text"]}
        for index, seg in enumerate(package["video"]["subtitle_segments"], start=1)
    ]
    payload = {
        "work": package["work"]["title"],
        "target_text": package["positioning"]["target_text"],
        "narration_lines": lines,
        "style": {
            "name": style.get("name"),
            "visual_language": style.get("visual_language"),
            "camera_language": style.get("camera_language"),
            "composition": style.get("composition"),
            "negative_prompt": style.get("negative_prompt"),
        },
    }
    contract = {
        "title": "短标题，不超过 20 字",
        "logline": "一句话说明本期内容",
        "line_order": [],
        "shots": [
            {
                "scene_prompt": "纯视觉描述，不写文字、水印、字幕",
                "duration_seconds": 3.0,
                "motion": "slow push-in / static / slow lateral track",
                "line_indexes": [1],
            }
        ],
    }
    system = (
        "你是本地短视频生产的分镜生成器。只能使用给定的 narration_lines 文本，不得新增事实、引文或作品名。"
        "输出 3-5 个镜头，覆盖全部台词行；每个镜头至少绑定一行。只输出 JSON，不要 Markdown。"
    )
    user = (
        "输入数据：\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n\n输出合同示例：\n"
        + json.dumps(contract, ensure_ascii=False, indent=2)
        + "\n\n镜头类型固定为 image；不要输出 visual_prompt，风格由系统拼接。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_script(
    package_path: Path,
    style_path: Path,
    out_path: Path,
    *,
    base_url: str,
    model: str,
    api_key: str = "",
    timeout_s: float = 900.0,
    max_tokens: int = 2000,
    speaker: str | None = None,
    speed: float = 1.0,
    http_client: Any = None,
) -> ProductionScript:
    package = json.loads(package_path.read_text(encoding="utf-8"))
    ContentPackage.model_validate(package)
    style = json.loads(style_path.read_text(encoding="utf-8"))
    if not isinstance(style, dict) or not style.get("name"):
        raise ScriptGenerationError("style snapshot is missing or invalid")

    segments = package["video"]["subtitle_segments"]
    messages = _messages(package, style)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw_paths: list[Path] = []
    draft: DraftScript | None = None
    built: ProductionScript | None = None
    last_error = ""
    for attempt in range(3):
        try:
            payload, raw = chat_json(
                base_url,
                model,
                messages,
                api_key=api_key,
                timeout_s=timeout_s,
                max_tokens=max_tokens,
                http_client=http_client,
            )
        except Exception as exc:  # noqa: BLE001 - preserve transport failure
            raise ScriptGenerationError(f"LLM 调用失败: {type(exc).__name__}: {exc}") from exc
        raw_path = out_path.parent / f"script_raw_attempt{attempt + 1}.json"
        raw_path.write_text(raw, encoding="utf-8")
        raw_paths.append(raw_path)
        try:
            draft = DraftScript.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - repair and retry
            last_error = str(exc)
            messages = messages + [
                {"role": "assistant", "content": raw[:4000]},
                {"role": "user", "content": f"输出未通过 Schema 校验：{last_error}\n请只返回修正后的 JSON。"},
            ]
            continue
        if not 3 <= len(draft.shots) <= 5:
            last_error = f"shots must be 3-5, got {len(draft.shots)}"
            messages = messages + [
                {"role": "assistant", "content": raw[:4000]},
                {"role": "user", "content": f"{last_error}。请只返回修正后的 JSON。"},
            ]
            continue
        # Validate indexes before accepting.
        try:
            built = _build_script(draft, package, segments, style, model)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            messages = messages + [
                {"role": "assistant", "content": raw[:4000]},
                {"role": "user", "content": f"引用关系无效：{last_error}\n请只返回修正后的 JSON。"},
            ]
            continue
        break

    if built is None:
        raise ScriptGenerationError(
            f"LLM 未生成合法分镜（原始输出保留在 {', '.join(str(p) for p in raw_paths)}）: {last_error}"
        )
    script = built
    script = script.model_copy(
        update={
            "style_id": style.get("id"),
            "style_sha256": _canonical_sha(style),
            "package_sha256": _sha256(package_path),
            "model": model,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(script.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)

    narration = {
        "speaker": speaker,
        "speed": speed,
        "lines": [line.text for line in script.lines],
        "source_script": str(out_path.name),
    }
    (out_path.parent / "narration.json").write_text(
        json.dumps(narration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return script


def _build_script(
    draft: DraftScript,
    package: dict[str, Any],
    segments: list[dict[str, Any]],
    style: dict[str, Any],
    model: str,
) -> ProductionScript:
    order = draft.line_order or list(range(1, len(segments) + 1))
    if sorted(order) != list(range(1, len(segments) + 1)):
        raise ValueError("line_order must contain each narration line exactly once")
    source_by_index = {index: seg for index, seg in enumerate(segments, start=1)}
    lines = [
        ScriptLine(
            line_id=f"line_{position:03d}",
            text=source_by_index[source_index]["text"],
            source_segment_id=source_by_index[source_index]["segment_id"],
        )
        for position, source_index in enumerate(order, start=1)
    ]
    line_id_by_source_index = {
        source_index: f"line_{position:03d}"
        for position, source_index in enumerate(order, start=1)
    }
    shots = []
    for index, shot in enumerate(draft.shots, start=1):
        line_ids = [line_id_by_source_index[source_index] for source_index in shot.line_indexes]
        shots.append(
            ScriptShot(
                shot_id=f"shot_{index:03d}",
                index=index,
                type="image",
                duration_seconds=shot.duration_seconds,
                motion=shot.motion,
                scene_prompt=shot.scene_prompt,
                visual_prompt=compose_visual_prompt(style, shot.scene_prompt),
                negative_prompt=str(style.get("negative_prompt") or ""),
                line_ids=line_ids,
            )
        )
    return ProductionScript(
        title=draft.title,
        logline=draft.logline,
        lines=lines,
        shots=shots,
        style_id=style.get("id"),
        style_sha256=_canonical_sha(style),
        package_sha256="",
        model=model,
        generated_at="",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--style", required=True, help="style snapshot JSON")
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--max-tokens", type=int, default=2000)
    parser.add_argument("--speaker", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--reuse", action="store_true", help="validate an existing production_script.json without calling the LLM")
    args = parser.parse_args()
    if args.reuse:
        script_path = Path(args.out)
        if not script_path.is_file():
            print(json.dumps({"ok": False, "error": f"reuse: missing {args.out}"}, ensure_ascii=False))
            return 1
        try:
            script = ProductionScript.model_validate(json.loads(script_path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            print(json.dumps({"ok": False, "error": f"reuse validation failed: {exc}"}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": True, "shots": len(script.shots), "out": args.out, "reused": True}, ensure_ascii=False))
        return 0
    try:
        script = generate_script(
            Path(args.package),
            Path(args.style),
            Path(args.out),
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            timeout_s=args.timeout,
            max_tokens=args.max_tokens,
            speaker=args.speaker,
            speed=args.speed,
        )
    except (ScriptGenerationError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "shots": len(script.shots), "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
