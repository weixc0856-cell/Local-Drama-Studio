"""Derive production state from real files.

Nothing in this module invents progress. A step is ``PASS_VERIFIED`` only when
the artifact exists and (where a manifest records it) its hash still matches.
Missing evidence is reported as ``NOT_RUN``; unreadable evidence as ``FAILED``.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..config import find_project_root

ROOT = find_project_root()

PASS_VERIFIED = "PASS_VERIFIED"
PASS_STATIC = "PASS_STATIC"
PARTIAL = "PARTIAL"
NOT_RUN = "NOT_RUN"
BLOCKED = "BLOCKED"
FAILED = "FAILED"
UNKNOWN = "UNKNOWN"

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
AUDIO_EXT = {".wav", ".mp3", ".flac", ".m4a"}
SUB_EXT = {".srt", ".ass"}
TEXT_EXT = {".txt", ".md"}
FONT_EXT = {".otf", ".ttf", ".woff", ".woff2"}

ASSET_EXT_ALLOW = (
    IMAGE_EXT
    | VIDEO_EXT
    | AUDIO_EXT
    | SUB_EXT
    | TEXT_EXT
    | FONT_EXT
    | {".json", ".csv", ".pdf"}
)

_hash_cache: dict[tuple[str, int, int], str] = {}
_probe_cache: dict[tuple[str, int, int], dict[str, Any] | None] = {}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def resolve(rel_path: str | None) -> Path | None:
    if not rel_path:
        return None
    candidate = (ROOT / rel_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def read_json(path: Path | None) -> Any:
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_text(path: Path | None, limit: int = 200_000) -> str | None:
    if path is None or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except (OSError, UnicodeDecodeError):
        return None


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    cached = _hash_cache.get(key)
    if cached:
        return cached
    digest = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    value = digest.hexdigest()
    _hash_cache[key] = value
    return value


def probe_media(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    if key in _probe_cache:
        return _probe_cache[key]
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,"
                "r_frame_rate,duration,channels,sample_rate",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        data = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        data = None
    if data is not None:
        data["path"] = rel(path)
    _probe_cache[key] = data
    return data


def probe_summary(probe: dict[str, Any] | None) -> dict[str, Any] | None:
    if not probe:
        return None
    summary: dict[str, Any] = {"duration": None, "size": None, "bit_rate": None, "streams": []}
    fmt = probe.get("format") or {}
    try:
        summary["duration"] = round(float(fmt.get("duration")), 3) if fmt.get("duration") else None
    except (TypeError, ValueError):
        summary["duration"] = None
    try:
        summary["size"] = int(fmt.get("size")) if fmt.get("size") else None
    except (TypeError, ValueError):
        summary["size"] = None
    try:
        summary["bit_rate"] = int(fmt.get("bit_rate")) if fmt.get("bit_rate") else None
    except (TypeError, ValueError):
        summary["bit_rate"] = None
    for stream in probe.get("streams") or []:
        summary["streams"].append(
            {
                "index": stream.get("index"),
                "type": stream.get("codec_type"),
                "codec": stream.get("codec_name"),
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": stream.get("r_frame_rate"),
                "duration": stream.get("duration"),
                "channels": stream.get("channels"),
                "sample_rate": stream.get("sample_rate"),
            }
        )
    return summary


def file_info(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": rel(path),
        "name": path.name,
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
    }


def _step(
    step_id: str,
    label: str,
    status: str,
    detail: str,
    *,
    required: bool = True,
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "detail": detail,
        "required": required,
        "evidence": [e for e in evidence if e],
    }


def _exists(rel_path: str | None) -> bool:
    path = resolve(rel_path)
    return bool(path and path.is_file())


def _safe_stat_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _latest_iso(paths: Iterable[Path]) -> str | None:
    best = max(((_safe_stat_mtime(p), p) for p in paths), default=(0.0, None))
    if best[1] is None:
        return None
    return datetime.fromtimestamp(best[0], timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- builds


def _build_summary(manifest_path: Path) -> dict[str, Any] | None:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        return None
    outputs = manifest.get("outputs") or {}
    final_rel = outputs.get("final")
    final_path = resolve(final_rel)
    final = None
    if final_path is not None:
        actual = sha256(final_path)
        expected = outputs.get("final_sha256")
        final = {
            "path": rel(final_path),
            "exists": final_path.is_file(),
            "size": final_path.stat().st_size if final_path.is_file() else None,
            "sha256": actual,
            "sha_ok": bool(expected) and actual == expected,
            "probe": probe_summary(probe_media(final_path)),
        }
    burned_rel = outputs.get("burned")
    burned = None
    if burned_rel:
        burned_path = resolve(burned_rel)
        burned = {"path": burned_rel, "exists": bool(burned_path and burned_path.is_file())}
    font = manifest.get("font") if isinstance(manifest.get("font"), dict) else None
    quality = read_json(manifest_path.parent / "quality_report.json")
    quality_status = quality.get("status") if isinstance(quality, dict) else None
    is_current = "content_type" in manifest and "timeline" in manifest
    return {
        "dir": rel(manifest_path.parent),
        "manifest": rel(manifest_path),
        "created_at": datetime.fromtimestamp(manifest_path.stat().st_mtime, timezone.utc).isoformat(
            timespec="seconds"
        ),
        "total_seconds": manifest.get("total_seconds"),
        "audio_end_seconds": manifest.get("audio_end_seconds"),
        "content_type": manifest.get("content_type"),
        "segment_count": len(manifest.get("segments") or []),
        "final": final,
        "burned": burned,
        "font": font,
        "quality": quality_status,
        "quality_report": rel(manifest_path.parent / "quality_report.json") if quality_status else None,
        "outputs": {k: v for k, v in outputs.items() if isinstance(v, str)},
        "manifest_version": "current" if is_current else "legacy",
        "decode_returncode": manifest.get("decode_returncode"),
    }


def _collect_builds(ep: dict[str, Any], art_root: Path) -> list[dict[str, Any]]:
    manifests: list[Path] = []
    historical = art_root / "renders" / "build_manifest.json"
    if historical.is_file():
        manifests.append(historical)
    workspace_root = ROOT / "projects" / ep["project_id"] / "episodes" / ep["id"] / "renders"
    if workspace_root.is_dir():
        manifests.extend(sorted(workspace_root.glob("*/build_manifest.json")))
    builds = [b for b in (_build_summary(m) for m in manifests) if b]
    builds.sort(key=lambda b: b["created_at"] or "", reverse=True)
    return builds


def _latest_valid_build(builds: list[dict[str, Any]]) -> dict[str, Any] | None:
    for build in builds:
        final = build.get("final")
        if final and final.get("exists") and final.get("sha_ok"):
            return build
    return None


# ---------------------------------------------------------------- LI runs


def _corpus_source_ids(corpus: Path) -> set[str]:
    registry = read_json(corpus / "source_registry.json") or {}
    return {s.get("source_id") for s in registry.get("sources", []) if s.get("source_id")}


def find_li_runs(corpus: Path) -> list[dict[str, Any]]:
    source_ids = _corpus_source_ids(corpus)
    runs: list[dict[str, Any]] = []
    base = ROOT / "literary_intelligence" / "runs"
    if not source_ids or not base.is_dir():
        return runs
    for manifest_path in sorted(base.glob("*/real_pipeline.json")):
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            continue
        run_sources = set(manifest.get("source_ids") or [])
        if not run_sources or not run_sources.issubset(source_ids):
            continue
        passes = []
        for item in manifest.get("passes") or []:
            passes.append(
                {
                    "pass_name": item.get("pass_name"),
                    "status": item.get("status"),
                    "elapsed_s": item.get("elapsed_s"),
                    "claims": len(item.get("claims") or []),
                    "error_code": item.get("error_code"),
                    "error": item.get("error"),
                    "draft_text": item.get("draft_text") or "",
                    "coverage": item.get("coverage"),
                    "research_status": item.get("research_status"),
                    "skeptic_verdict": item.get("skeptic_verdict"),
                    "skeptic_findings": item.get("skeptic_findings") or [],
                    "notes": item.get("notes") or "",
                }
            )
        runs.append(
            {
                "dir": rel(manifest_path.parent),
                "manifest": rel(manifest_path),
                "started_at": manifest.get("started_at"),
                "finished_at": manifest.get("finished_at"),
                "model": manifest.get("model"),
                "all_evidence_valid": manifest.get("all_evidence_valid"),
                "human_review": manifest.get("human_review", "NOT_RUN"),
                "passes": passes,
            }
        )
    runs.sort(key=lambda r: r.get("finished_at") or "", reverse=True)
    return runs


# ---------------------------------------------------------------- video episode


def _analyze_video(ep: dict[str, Any], art_root: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    narration_path = art_root / "narration.json"
    segments_path = art_root / "segments.json"
    audio_path = art_root / "audio_manifest.json"
    renders = art_root / "renders"

    narration = read_json(narration_path)
    segments = read_json(segments_path)
    audio_manifest = read_json(audio_path)

    segments = segments if isinstance(segments, list) else []
    audio_lines = (audio_manifest or {}).get("lines") if isinstance(audio_manifest, dict) else []
    audio_lines = audio_lines or []
    narration_lines = (narration or {}).get("lines") if isinstance(narration, dict) else []
    narration_lines = narration_lines or []

    image_segments = [s for s in segments if s.get("type") == "image"]
    video_segments = [s for s in segments if s.get("type") == "video"]
    missing_sources = [s.get("source") for s in segments if not _exists(s.get("source"))]

    builds = _collect_builds(ep, art_root)
    latest = _latest_valid_build(builds)

    steps: list[dict[str, Any]] = []

    if narration_lines:
        steps.append(
            _step(
                "source",
                "原文",
                PASS_VERIFIED,
                f"{len(narration_lines)} 行文本",
                evidence=[rel(narration_path)],
            )
        )
    else:
        steps.append(
            _step("source", "原文", NOT_RUN, "未找到 narration.json 或 lines 为空", evidence=[rel(narration_path)])
        )

    steps.append(
        _step(
            "analysis",
            "文学分析",
            NOT_RUN,
            "该期未绑定 Literary Intelligence 运行记录",
            required=False,
        )
    )

    if narration_lines:
        steps.append(
            _step(
                "script",
                "文案",
                PARTIAL,
                f"旁白直接使用 {len(narration_lines)} 行原文；未记录独立的现代文案版本",
                required=False,
                evidence=[rel(narration_path)],
            )
        )
    else:
        steps.append(_step("script", "文案", NOT_RUN, "无 narration.json", required=False))

    if segments and not missing_sources:
        steps.append(
            _step(
                "storyboard",
                "分镜",
                PASS_VERIFIED,
                f"{len(segments)} 段（{len(image_segments)} 静帧 / {len(video_segments)} 视频）",
                evidence=[rel(segments_path)],
            )
        )
    elif segments:
        steps.append(
            _step(
                "storyboard",
                "分镜",
                FAILED,
                f"{len(missing_sources)} 个分段素材缺失：{', '.join(str(m) for m in missing_sources[:3])}",
                evidence=[rel(segments_path)],
            )
        )
    else:
        steps.append(_step("storyboard", "分镜", NOT_RUN, "未找到 segments.json", evidence=[rel(segments_path)]))

    if image_segments:
        ok = [s for s in image_segments if _exists(s.get("source"))]
        steps.append(
            _step(
                "images",
                "图片",
                PASS_VERIFIED if len(ok) == len(image_segments) else PARTIAL,
                f"{len(ok)}/{len(image_segments)} 静帧存在",
                evidence=[s.get("source") for s in image_segments],
            )
        )
    else:
        steps.append(_step("images", "图片", NOT_RUN, "分镜中没有静帧分段"))

    if video_segments:
        ok = [s for s in video_segments if _exists(s.get("source"))]
        steps.append(
            _step(
                "videos",
                "视频",
                PASS_VERIFIED if len(ok) == len(video_segments) else PARTIAL,
                f"{len(ok)}/{len(video_segments)} Wan 分段存在",
                evidence=[s.get("source") for s in video_segments],
            )
        )
    else:
        steps.append(_step("videos", "视频", NOT_RUN, "该期无 Wan 分段（全部为静帧推拉）", required=False))

    audio_detail = "未找到 audio_manifest.json"
    audio_status = NOT_RUN
    audio_evidence = [rel(audio_path)]
    verified_lines = 0
    if audio_lines:
        checks = []
        for line in audio_lines:
            path = resolve(line.get("file"))
            actual = sha256(path) if path else None
            expected = line.get("sha256")
            checks.append(bool(path and path.is_file() and (not expected or actual == expected)))
        verified_lines = sum(checks)
        if verified_lines == len(audio_lines):
            audio_status = PASS_VERIFIED
            audio_detail = f"{verified_lines}/{len(audio_lines)} 行音频存在且哈希一致"
        else:
            audio_status = PARTIAL
            audio_detail = f"{verified_lines}/{len(audio_lines)} 行音频通过校验"
        audio_evidence.extend(line.get("file") for line in audio_lines)
    steps.append(_step("voice", "配音", audio_status, audio_detail, evidence=audio_evidence))

    subtitle_paths = []
    for build in builds:
        for key in ("srt", "ass"):
            candidate = resolve((build.get("outputs") or {}).get(key))
            if candidate and candidate.is_file():
                subtitle_paths.append(candidate)
    if not subtitle_paths:
        for candidate in (renders / "drama.srt", renders / "drama.ass"):
            if candidate.is_file():
                subtitle_paths.append(candidate)
    steps.append(
        _step(
            "subtitles",
            "字幕",
            PASS_VERIFIED if subtitle_paths else NOT_RUN,
            f"{len(subtitle_paths)} 个字幕文件" if subtitle_paths else "未找到 SRT/ASS",
            required=False,
            evidence=[rel(p) for p in subtitle_paths],
        )
    )

    if latest:
        final = latest["final"]
        quality_failed = latest.get("quality") == "FAIL"
        steps.append(
            _step(
                "compose",
                "合成",
                FAILED if quality_failed else (PASS_VERIFIED if final.get("sha_ok") else PARTIAL),
                f"{latest['total_seconds']} s；最终文件哈希{'一致' if final.get('sha_ok') else '不一致'}"
                + ("；质量检查 FAILED" if quality_failed else ""),
                evidence=[latest["manifest"], final["path"]],
            )
        )
    else:
        steps.append(
            _step(
                "compose",
                "合成",
                NOT_RUN,
                "没有通过哈希校验的构建记录（历史 manifest 可能来自旧版脚本）",
                evidence=[b["manifest"] for b in builds],
            )
        )

    final_probe = (latest or {}).get("final", {}).get("probe") if latest else None
    if latest and final_probe:
        video_stream = next((s for s in final_probe["streams"] if s["type"] == "video"), None)
        steps.append(
            _step(
                "output",
                "成片",
                PASS_VERIFIED,
                f"{final_probe['duration']} s / {video_stream['width']}×{video_stream['height']} / "
                f"{len(final_probe['streams'])} 条流"
                if video_stream
                else f"{final_probe['duration']} s",
                evidence=[latest["final"]["path"]],
            )
        )
    else:
        steps.append(_step("output", "成片", NOT_RUN, "没有可探测的最终视频"))

    review_state = _review_state(tasks, ep)
    steps.append(
        _step(
            "review",
            "人工验收",
            review_state["status"],
            review_state["detail"],
            required=False,
        )
    )

    content = _video_content(narration_path, narration, narration_lines, audio_lines, segments)
    status, status_label = _episode_status(steps, latest, tasks)
    return {
        "kind": "video",
        "steps": steps,
        "builds": builds,
        "latest_build": latest,
        "final": (latest or {}).get("final"),
        "content": content,
        "storyboard": _video_storyboard(segments, segments_path),
        "audio": _video_audio(art_root, audio_path, audio_manifest, audio_lines),
        "status": status,
        "status_label": status_label,
        "review": review_state,
        "updated_at": _latest_iso(
            [
                p
                for p in (
                    narration_path,
                    segments_path,
                    audio_path,
                    renders / "build_manifest.json",
                    art_root / "renders" / "final_9x16.mp4",
                )
                if p.exists()
            ]
        ),
    }


def _review_state(tasks: list[dict[str, Any]], ep: dict[str, Any]) -> dict[str, Any]:
    review_path = (
        ROOT / "projects" / str(ep.get("project_id")) / "episodes" / str(ep.get("id")) / "human_review.json"
    )
    record = read_json(review_path)
    if isinstance(record, dict) and record.get("decision") in ("accept", "reject"):
        accepted = record["decision"] == "accept"
        note = str(record.get("note") or "").strip()
        detail = f"人工验收：{'通过' if accepted else '拒绝'}（{record.get('created_at', '')}）"
        if note:
            detail += f"；{note}"
        return {
            "status": PASS_VERIFIED if accepted else FAILED,
            "detail": detail,
            "record": record,
        }
    for task in tasks:
        if task.get("kind") in ("review.accept", "review.reject") and task.get("status") == "SUCCEEDED":
            accepted = task["kind"] == "review.accept"
            return {
                "status": PASS_VERIFIED if accepted else FAILED,
                "detail": f"人工验收记录：{'通过' if accepted else '拒绝'}（{task.get('created_at')}）",
                "record": None,
            }
    return {"status": NOT_RUN, "detail": "没有人工验收记录；技术上可成片不等于内容通过", "record": None}


def _episode_status(
    steps: list[dict[str, Any]], latest: dict[str, Any] | None, tasks: list[dict[str, Any]]
) -> tuple[str, str]:
    if any(t.get("status") == "RUNNING" for t in tasks):
        return "producing", "生产中"
    if latest and latest["final"].get("sha_ok"):
        return "completed", "已成片"
    if any(t.get("status") == "FAILED" for t in tasks[:1]):
        return "failed", "生产失败"
    required = [s for s in steps if s.get("required")]
    done = [s for s in required if s.get("status") == PASS_VERIFIED]
    if len(done) >= len(required) - 2 and len(done) >= 2:
        return "ready", "待合成"
    return "draft", "草稿"


def _video_content(
    narration_path: Path,
    narration: Any,
    narration_lines: list[str],
    audio_lines: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": "video",
        "source": {
            "title": (narration or {}).get("title") if isinstance(narration, dict) else None,
            "path": rel(narration_path) if narration_lines else None,
            "lines": narration_lines,
            "note": "原文行即旁白行；本仓库没有独立的原文来源登记文件",
        },
        "analysis": None,
        "script": {
            "status": PARTIAL if narration_lines else NOT_RUN,
            "lines": narration_lines,
            "reason": "旁白直接使用原文；没有独立现代文案" if narration_lines else "无旁白文本",
        },
        "narration": {
            "speaker": None,
            "lines": [
                {"index": line.get("index"), "text": line.get("text"), "duration": line.get("duration_seconds")}
                for line in audio_lines
            ],
        },
        "meta": {"title": None, "opening_hook": None, "ending": None},
    }


def _job_prompt_index() -> dict[str, dict[str, Any]]:
    """Map output sha256 -> generation parameters from any experiment job record.

    This keeps storyboard provenance generic: the workspace never assumes a
    particular experiment directory or a particular work.
    """
    index: dict[str, dict[str, Any]] = {}
    for job_path in ROOT.glob("experiments/*/runs/*/job.json"):
        job = read_json(job_path)
        if not isinstance(job, dict) or job.get("status") != "success":
            continue
        params = job.get("params") or {}
        for output in job.get("outputs") or []:
            digest = output.get("sha256") if isinstance(output, dict) else None
            if digest:
                index[digest] = {
                    "job_id": job.get("job_id"),
                    "prompt": params.get("positive_prompt"),
                    "negative_prompt": params.get("negative_prompt"),
                    "source": rel(job_path),
                }
    return index


def _video_storyboard(segments: list[dict[str, Any]], segments_path: Path) -> dict[str, Any]:
    jobs_by_sha = _job_prompt_index()
    items = []
    for seg in segments:
        source = str(seg.get("source") or "")
        path = resolve(source)
        digest = sha256(path) if path and path.is_file() else None
        job = jobs_by_sha.get(digest or "")
        items.append(
            {
                "id": seg.get("id"),
                "type": seg.get("type"),
                "duration": seg.get("duration"),
                "motion": seg.get("motion"),
                "source": source,
                "source_exists": bool(path and path.is_file()),
                "size": path.stat().st_size if path and path.is_file() else None,
                "sha256": digest,
                "prompt": (job or {}).get("prompt"),
                "negative_prompt": (job or {}).get("negative_prompt"),
                "prompt_source": (job or {}).get("source"),
                "source_job": (job or {}).get("job_id"),
            }
        )
    return {
        "segments": items,
        "segments_path": rel(segments_path) if segments_path.is_file() else None,
        "note": "当前没有 models.Storyboard 契约文件：生产链路使用 segments.json 的真实构建分段；"
        "提示词按输出文件 SHA-256 从 experiments/*/runs/*/job.json 反查，不绑定某一作品或实验目录。",
    }


def _video_audio(
    art_root: Path, audio_path: Path, audio_manifest: Any, audio_lines: list[dict[str, Any]]
) -> dict[str, Any]:
    lines = []
    for line in audio_lines:
        path = resolve(line.get("file"))
        actual = sha256(path) if path else None
        expected = line.get("sha256")
        lines.append(
            {
                "index": line.get("index"),
                "text": line.get("text"),
                "file": line.get("file"),
                "duration_seconds": line.get("duration_seconds"),
                "exists": bool(path and path.is_file()),
                "sha256": actual,
                "sha_ok": bool(expected) and actual == expected,
                "synth_seconds": line.get("synth_seconds"),
            }
        )
    timeline_path = art_root / "renders" / "timeline.json"
    timeline = read_json(timeline_path)
    return {
        "manifest": rel(audio_path) if audio_path.is_file() else None,
        "speaker": (audio_manifest or {}).get("speaker") if isinstance(audio_manifest, dict) else None,
        "lines": lines,
        "total_seconds": round(sum(float(l.get("duration_seconds") or 0) for l in lines), 3),
        "timeline": {
            "path": rel(timeline_path),
            "segments": timeline.get("segments") if isinstance(timeline, dict) else None,
            "note": None if isinstance(timeline, dict) else "该构建未生成 timeline.json（历史版本）；字幕仍来自 SRT/ASS",
        },
    }


# ---------------------------------------------------------------- literary episode


def _analyze_literary(ep: dict[str, Any], corpus: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    registry = read_json(corpus / "source_registry.json") or {}
    source = (registry.get("sources") or [{}])[0]
    original_text = read_text(corpus / "original_text.txt")
    normalized_text = read_text(corpus / "normalized_text.txt")
    segments = read_json(corpus / "segments.json") or []
    claims = read_json(corpus / "claims.json") or []
    reviews = read_json(corpus / "reviews.json") or []
    runs = find_li_runs(corpus)
    latest = runs[0] if runs else None

    hash_ok = bool(
        original_text
        and source.get("content_sha256")
        and sha256(corpus / "original_text.txt") == source.get("content_sha256")
    )

    steps: list[dict[str, Any]] = []
    steps.append(
        _step(
            "source",
            "原文",
            PASS_VERIFIED if original_text and hash_ok else (PARTIAL if original_text else NOT_RUN),
            f"{source.get('work', '?')} / {source.get('author', '?')}；原文哈希"
            f"{'一致' if hash_ok else '未核验或缺失'}；来源 {source.get('source_name', '?')}",
            evidence=[rel(corpus / "original_text.txt"), rel(corpus / "source_registry.json")],
        )
    )

    if latest:
        failed = [p for p in latest["passes"] if p.get("status") != PASS_VERIFIED]
        approved = [c for c in claims if c.get("review_status") == "approved"]
        status = PASS_VERIFIED if latest["human_review"] != "NOT_RUN" else PARTIAL
        detail = (
            f"真实 LLM 五轮：{len(latest['passes']) - len(failed)}/{len(latest['passes'])} 通过；"
            f"人工审核 {latest['human_review']}；approved claim {len(approved)}/{len(claims)}"
        )
        steps.append(_step("analysis", "文学分析", status, detail, evidence=[latest["manifest"]]))
    else:
        steps.append(_step("analysis", "文学分析", NOT_RUN, "没有与本文本绑定的 LLM 运行记录"))

    package_files = sorted(corpus.glob("*content_package*.json")) + sorted(corpus.glob("content_package.json"))
    steps.append(
        _step(
            "package",
            "内容包",
            PASS_VERIFIED if package_files else NOT_RUN,
            f"{len(package_files)} 个内容包文件" if package_files else "尚未生成 ContentPackage（LI-2-C Adapter 未实现）",
            evidence=[rel(p) for p in package_files],
        )
    )

    draft = ""
    if latest:
        draft = next((p.get("draft_text") or "" for p in latest["passes"] if p["pass_name"] == "editor"), "")
    steps.append(
        _step(
            "script",
            "文案",
            PASS_VERIFIED if draft.strip() else NOT_RUN,
            f"editor 输出 {len(draft)} 字" if draft.strip() else "无 approved claim；editor 输出为空（设计如此）",
            evidence=[latest["manifest"]] if latest else [],
        )
    )

    for step_id, label in (
        ("storyboard", "分镜"),
        ("images", "图片"),
        ("videos", "视频"),
        ("voice", "配音"),
        ("subtitles", "字幕"),
        ("compose", "合成"),
        ("output", "成片"),
    ):
        steps.append(
            _step(step_id, label, NOT_RUN, "文学阶段尚未产出，且没有真实素材", required=step_id in ("storyboard", "voice", "compose", "output"))
        )

    review_state = _review_state(tasks, ep)
    steps.append(_step("review", "人工审核", review_state["status"], review_state["detail"], required=False))

    content = _literary_content(source, original_text, normalized_text, segments, claims, reviews, latest)
    status, status_label = _literary_episode_status(latest, claims)
    updated = _latest_iso([corpus / "source_registry.json", corpus / "claims.json", corpus / "reviews.json"])
    return {
        "kind": "literary",
        "steps": steps,
        "builds": [],
        "latest_build": None,
        "final": None,
        "content": content,
        "storyboard": {"segments": [], "segments_path": None, "note": "该期尚无视觉分段"},
        "audio": {"manifest": None, "speaker": None, "lines": [], "total_seconds": 0, "timeline": None},
        "status": status,
        "status_label": status_label,
        "review": review_state,
        "updated_at": updated,
    }


def _literary_episode_status(latest: dict[str, Any] | None, claims: list[dict[str, Any]]) -> tuple[str, str]:
    if not latest:
        return "draft", "文献准备"
    approved = [c for c in claims if c.get("review_status") == "approved"]
    if latest.get("human_review") == "NOT_RUN" or not approved:
        return "draft", "文献准备（待人工审核）"
    return "ready", "文学内容就绪"


def _literary_content(
    source: dict[str, Any],
    original_text: str | None,
    normalized_text: str | None,
    segments: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    reviews: list[Any],
    latest: dict[str, Any] | None,
) -> dict[str, Any]:
    approved = [c for c in claims if c.get("review_status") == "approved"]
    draft = ""
    if latest:
        draft = next((p.get("draft_text") or "" for p in latest["passes"] if p["pass_name"] == "editor"), "")
    return {
        "kind": "literary",
        "source": {
            "work": source.get("work"),
            "author": source.get("author"),
            "edition": source.get("edition"),
            "source_name": source.get("source_name"),
            "url": source.get("url"),
            "license": source.get("license"),
            "commercial_use": source.get("commercial_use"),
            "locator": source.get("locator"),
            "original_text": original_text,
            "normalized_text": normalized_text,
            "segments": segments,
        },
        "analysis": {
            "status": PARTIAL if latest else NOT_RUN,
            "runs": [
                {
                    "dir": run["dir"],
                    "model": run["model"],
                    "finished_at": run["finished_at"],
                    "all_evidence_valid": run["all_evidence_valid"],
                    "human_review": run["human_review"],
                    "passes": run["passes"],
                }
                for run in ([latest] if latest else [])
            ],
            "claims": claims,
            "approved_claims": len(approved),
            "total_claims": len(claims),
            "reviews": reviews,
            "reviewed": bool(reviews),
            "reason": "所有 claim 仍为 unreviewed；reviews.json 为空，人工审核未执行",
        },
        "script": {
            "status": PASS_VERIFIED if draft.strip() else NOT_RUN,
            "draft_text": draft,
            "reason": None if draft.strip() else "editor 没有 approved claim 可用，输出为空",
        },
        "meta": {"title": None, "opening_hook": None, "ending": None},
    }


# ---------------------------------------------------------------- episode entry


def analyze_episode(store: Any, ep: dict[str, Any]) -> dict[str, Any]:
    project = store.get_project(ep["project_id"]) or {}
    art_root = resolve(ep.get("artifact_root")) if ep.get("artifact_root") else None
    art_exists = bool(art_root and art_root.is_dir())
    tasks = store.list_tasks(episode_id=ep["id"], limit=50)
    base: dict[str, Any] = {
        "id": ep["id"],
        "project_id": ep["project_id"],
        "project": {"id": project.get("id"), "name": project.get("name")},
        "number": ep.get("number"),
        "title": ep.get("title"),
        "track": ep.get("track"),
        "artifact_root": ep.get("artifact_root"),
        "artifact_root_exists": art_exists,
        "style": _style_view(store, ep),
        "style_snapshot": ep.get("style_snapshot") or {},
        "notes": ep.get("notes") or "",
        "origin": ep.get("origin"),
        "created_at": ep.get("created_at"),
        "tasks": tasks,
    }
    if not art_exists:
        steps = [
            _step("source", "原文", NOT_RUN, "产物目录不存在，无法派生任何状态"),
        ]
        base.update(
            {
                "kind": ep.get("track") or "video",
                "steps": steps,
                "builds": [],
                "latest_build": None,
                "final": None,
                "content": None,
                "storyboard": {"segments": [], "segments_path": None, "note": "无产物目录"},
                "audio": {"manifest": None, "speaker": None, "lines": [], "total_seconds": 0, "timeline": None},
                "status": "draft",
                "status_label": "产物目录缺失",
                "review": {"status": NOT_RUN, "detail": "无产物目录"},
                "progress": _progress(steps),
                "updated_at": ep.get("updated_at"),
            }
        )
        return base

    if ep.get("track") == "literary":
        detail = _analyze_literary(ep, art_root, tasks)
    else:
        detail = _analyze_video(ep, art_root, tasks)
    base.update(detail)
    base["progress"] = _progress(detail["steps"])
    base["updated_at"] = _latest_sort_key(detail.get("updated_at"), ep.get("updated_at"))
    base["workflow"] = _workflow(base)
    return base


def _style_view(store: Any, ep: dict[str, Any]) -> dict[str, Any] | None:
    snapshot = ep.get("style_snapshot") or {}
    style_id = ep.get("style_id")
    if not style_id and not snapshot:
        return None
    current = store.get_style(style_id) if style_id else None
    lock = (snapshot or {}).get("_style_lock") or {}
    return {
        "id": style_id,
        "name": (snapshot or current or {}).get("name"),
        "snapshot": snapshot,
        "current": current,
        "drifted": bool(current and snapshot and current.get("updated_at") != snapshot.get("updated_at")),
        "preset_id": lock.get("preset_id") or (snapshot or {}).get("preset_id"),
        "revision": lock.get("revision"),
        "sha256": lock.get("sha256"),
        "locked_at": lock.get("locked_at"),
        "history": lock.get("history") or [],
        "override_allowed": False,
    }


def _latest_sort_key(primary: str | None, secondary: str | None) -> str | None:
    return max([v for v in (primary, secondary) if v], default=None)


def _progress(steps: list[dict[str, Any]]) -> dict[str, Any]:
    required = [s for s in steps if s.get("required")]
    verified = [s for s in required if s.get("status") == PASS_VERIFIED]
    total = len(required)
    return {
        "verified": len(verified),
        "required": total,
        "percent": round(len(verified) * 100 / total) if total else 0,
        "partial": len([s for s in required if s.get("status") == PARTIAL]),
        "not_run": len([s for s in required if s.get("status") == NOT_RUN]),
    }


# ---------------------------------------------------------------- workflow


def _workflow(detail: dict[str, Any]) -> dict[str, Any]:
    step_by_id = {s["id"]: s for s in detail["steps"]}
    storyboard = detail.get("storyboard") or {}
    audio = detail.get("audio") or {}
    segments = storyboard.get("segments") or []
    image_sources = [s.get("source") for s in segments if s.get("type") == "image"]
    video_sources = [s.get("source") for s in segments if s.get("type") == "video"]
    voice_files = [l.get("file") for l in audio.get("lines") or []]

    def outputs_of(node_id: str) -> list[str]:
        step = step_by_id.get(node_id) or {}
        return [p for p in step.get("evidence") or [] if p]

    def node(
        node_id: str,
        label: str,
        inputs: list[str],
        task_kind: str | None = None,
        task_reason: str | None = None,
    ) -> dict[str, Any]:
        step = step_by_id.get(node_id, {})
        return {
            "id": node_id,
            "label": label,
            "status": step.get("status", NOT_RUN),
            "detail": step.get("detail", ""),
            "required": step.get("required", True),
            "inputs": [{"path": p, "exists": _exists(p)} for p in inputs if p],
            "outputs": [{"path": p, "exists": _exists(p)} for p in outputs_of(node_id)],
            "task_kind": task_kind,
            "task_reason": task_reason,
        }

    source_out = outputs_of("source")
    script_out = outputs_of("script")
    nodes = [
        node("source", "原文", []),
        node("analysis", "文学分析", source_out, None, "缺少与本期绑定的 LI 运行记录" if not outputs_of("analysis") else None),
        node("script", "文案", source_out, None, "写入路径未实现（只读派生）"),
        node("storyboard", "分镜", script_out, None, "分镜生成器未实现"),
        node(
            "images",
            "图片",
            image_sources,
            "comfy.batch",
            "需要显式指定 experiments/ 下的 jobs.json；工作台不会自动推断生成参数",
        ),
        node(
            "videos",
            "视频",
            video_sources,
            "comfy.batch",
            "需要显式指定 jobs.json；Wan 单段实测约 36 分钟",
        ),
        node(
            "voice",
            "配音",
            script_out,
            "tts.synthesize",
            "r3_tts.py 尚未参数化，只能处理 experiments/r3b",
        ),
        node("subtitles", "字幕", voice_files),
        node(
            "compose",
            "合成",
            [storyboard.get("segments_path"), audio.get("manifest")],
            "build.rebuild",
            None,
        ),
        node("output", "成片", [(detail.get("final") or {}).get("path")]),
    ]
    edges = [
        ("source", "analysis"),
        ("source", "script"),
        ("script", "storyboard"),
        ("storyboard", "images"),
        ("storyboard", "videos"),
        ("script", "voice"),
        ("voice", "subtitles"),
        ("images", "compose"),
        ("videos", "compose"),
        ("subtitles", "compose"),
        ("compose", "output"),
    ]
    return {"nodes": nodes, "edges": [{"from": a, "to": b} for a, b in edges]}


# ---------------------------------------------------------------- assets


def _asset_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in SUB_EXT:
        return "subtitle"
    if ext in FONT_EXT:
        return "font"
    if ext in TEXT_EXT:
        return "text"
    if ext == ".json":
        return "json"
    if ext in {".log", ".out", ".err", ".pid"}:
        return "log"
    return "other"


_TEMP_PATTERNS = (
    re.compile(r"(^|/)frames?/"),
    re.compile(r"(^|/)segments/"),
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"_\d{5}_?\.(png|jpg|jpeg|webp)$", re.IGNORECASE),
    re.compile(r"(^|/)video_(raw|faded)\.mp4$"),
    re.compile(r"(^|/)concat\.txt$"),
)


def _category(path: Path) -> str:
    rel_path = rel(path)
    if rel_path.startswith("assets/visual_style") or "/reference/" in rel_path:
        return "reference"
    if rel_path.startswith("assets/"):
        return "asset"
    if rel_path.startswith("projects/"):
        return "project"
    if rel_path.startswith("literary_intelligence/"):
        return "literary"
    if rel_path.startswith("workflows/"):
        return "workflow"
    if rel_path.startswith("experiments/"):
        return "experiment"
    return "other"


def _is_temporary(path: Path) -> bool:
    rel_path = rel(path)
    if path.suffix.lower() in {".log", ".out", ".err", ".pid"}:
        return True
    if any(p.search(rel_path) for p in _TEMP_PATTERNS):
        return True
    if re.search(r"frame_\d+\.png$", path.name):
        return True
    return False


_SCAN_ROOTS: tuple[tuple[str, int], ...] = (
    ("assets", 4),
    ("experiments", 6),
    ("projects", 8),
    ("literary_intelligence/corpus", 3),
    ("literary_intelligence/runs", 4),
    ("workflows", 2),
)


def _iter_files(root: Path, max_depth: int) -> Iterable[Path]:
    root_depth = len(root.parts)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if len(path.parts) - root_depth > max_depth:
            continue
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        yield path


def _referenced_paths() -> set[str]:
    referenced: set[str] = set()
    for segments in ROOT.glob("experiments/*/segments.json"):
        data = read_json(segments) or []
        if isinstance(data, list):
            for seg in data:
                if isinstance(seg, dict) and seg.get("source"):
                    referenced.add(str(seg["source"]).replace("\\", "/"))
    for manifest_path in list(ROOT.glob("experiments/*/audio_manifest.json")) + list(
        ROOT.glob("experiments/*/renders/build_manifest.json")
    ) + list(ROOT.glob("projects/*/episodes/*/renders/*/build_manifest.json")):
        data = read_json(manifest_path)
        if not isinstance(data, dict):
            continue
        for line in data.get("lines") or []:
            if line.get("file"):
                referenced.add(str(line["file"]).replace("\\", "/"))
        for seg in data.get("segments") or []:
            if isinstance(seg, dict) and seg.get("source"):
                referenced.add(str(seg["source"]).replace("\\", "/"))
        for value in (data.get("outputs") or {}).values():
            if isinstance(value, str) and value:
                referenced.add(value.replace("\\", "/"))
    return referenced


def _episode_lookup(store: Any) -> list[dict[str, Any]]:
    return store.list_episodes()


def _bind_episode(path: Path, episodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    rel_path = rel(path)
    best = None
    for ep in episodes:
        root = ep.get("artifact_root")
        if root and (rel_path == root or rel_path.startswith(root.rstrip("/") + "/")):
            if best is None or len(root) > len(best.get("artifact_root") or ""):
                best = ep
    if best:
        return {"episode_id": best["id"], "project_id": best["project_id"]}
    return None


def scan_assets(store: Any, include_temporary: bool = False, limit: int = 800) -> dict[str, Any]:
    referenced = _referenced_paths()
    episodes = _episode_lookup(store)
    items: list[dict[str, Any]] = []
    temporary = 0
    formal = 0
    truncated = False
    for root_name, depth in _SCAN_ROOTS:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in _iter_files(root, depth):
            if path.suffix.lower() not in ASSET_EXT_ALLOW:
                continue
            is_temp = _is_temporary(path)
            if is_temp:
                temporary += 1
                if not include_temporary:
                    continue
            else:
                formal += 1
            if len(items) >= limit:
                truncated = True
                continue
            info = file_info(path)
            asset_type = _asset_type(path)
            binding = _bind_episode(path, episodes)
            items.append(
                {
                    **info,
                    "type": asset_type,
                    "category": _category(path),
                    "temporary": is_temp,
                    "referenced": rel(path) in referenced,
                    "episode_id": binding["episode_id"] if binding else None,
                    "project_id": binding["project_id"] if binding else None,
                    "thumb": asset_type in ("image", "video"),
                }
            )
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return {
        "items": items,
        "temporary_total": temporary,
        "formal_total": formal,
        "limit": limit,
        "truncated": truncated,
    }


def episode_assets(ep: dict[str, Any]) -> list[dict[str, Any]]:
    art_root = resolve(ep.get("artifact_root"))
    if not art_root or not art_root.is_dir():
        return []
    referenced = _referenced_paths()
    items = []
    for path in _iter_files(art_root, 4):
        if path.name.startswith(".") or path.suffix.lower() not in ASSET_EXT_ALLOW:
            continue
        info = file_info(path)
        items.append(
            {
                **info,
                "type": _asset_type(path),
                "category": _category(path),
                "temporary": _is_temporary(path),
                "referenced": rel(path) in referenced,
                "thumb": _asset_type(path) in ("image", "video"),
            }
        )
    items.sort(key=lambda i: (i["temporary"], i["mtime"]), reverse=False)
    return items
