"""P1 end-to-end acceptance runner.

Creates a disposable content instance from a short-text fixture, then runs the
registered task chain through the workspace:

    package.build -> script.generate -> tts.synthesize -> comfy.batch
    -> segments.build -> build.rebuild -> quality.check

It uses the real local services configured in ``config/settings.yaml``. It does
not start or stop those services; the caller owns their lifecycle.
"""

from __future__ import annotations

import argparse
import sys
import asyncio
import hashlib
import json
from pathlib import Path

from drama_studio.infrastructure.storage.store import WorkspaceStore
from drama_studio.application.operations.tasks import TaskRunner

ROOT = Path(__file__).resolve().parents[1]

if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_fixture(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [str(line).strip() for line in data.get("lines") or [] if str(line).strip()]
    if not lines:
        raise SystemExit(f"fixture has no lines: {path}")
    return {
        "work": str(data.get("work") or "测试短文本"),
        "author": str(data.get("author") or "测试作者"),
        "edition": str(data.get("edition") or "P1 验证"),
        "lines": lines,
    }


def ensure_case(store: WorkspaceStore, fixture: dict, project_id: str, episode_id: str, style_id: str, art_root: str) -> None:
    if store.get_project(project_id) is None:
        store.create_project(
            {
                "id": project_id,
                "name": f"P1 验证 · {fixture['work']}",
                "description": "P1 端到端验证内容实例。",
                "positioning": "东方写意 / 竖屏",
                "aspect_ratio": "9:16",
                "default_voice": "中文女",
                "target_platforms": [],
            }
        )
    if store.get_style(style_id) is None:
        store.create_style(
            {
                "id": style_id,
                "name": "P1 测试风格 · 东方写意",
                "description": "P1 验证用通用风格，不绑定具体作品。",
                "visual_language": "水墨质感与自然纪实结合，低饱和青绿与暖金",
                "color_palette": {"ink": "#1E2A32", "jade": "#4F6F63", "gold": "#C9A76A"},
                "lighting": "柔和自然光，清晨/黄昏低角度光",
                "camera_language": "static / slow push-in",
                "composition": "9:16 竖构图，近景在前，远景留白",
                "positive_prompt": "东方写意，水墨与自然纪实结合，低饱和青绿与暖金，柔和自然光，竖屏 9:16 电影感构图",
                "negative_prompt": "文字，水印，字幕，现代建筑，人物，过度饱和",
                "aspect_ratio": "9:16",
            }
        )
    episode = store.get_episode(episode_id)
    if episode is None:
        store.create_episode(
            {
                "id": episode_id,
                "project_id": project_id,
                "number": 1,
                "title": f"{fixture['lines'][0]} · P1 端到端",
                "track": "video",
                "artifact_root": art_root,
                "style_id": style_id,
                "notes": "P1 真实链路验证：package → script → TTS → FLUX → segments → build → quality。",
            }
        )
    elif not episode.get("style_snapshot"):
        store.update_episode(episode_id, {"style_id": style_id})


def ensure_corpus(root: Path, art_root: str, fixture: dict) -> Path:
    corpus = root / art_root / "source"
    corpus.mkdir(parents=True, exist_ok=True)
    lines = fixture["lines"]
    original = "\n".join(lines) + "\n"
    normalized = original
    (corpus / "original_text.txt").write_text(original, encoding="utf-8", newline="")
    (corpus / "normalized_text.txt").write_text(normalized, encoding="utf-8", newline="")
    (corpus / "normalization_map.json").write_text(
        json.dumps({"version": 1, "mapping": {}, "notes": "P1 测试语料，简体原文。"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    segments = [
        {
            "segment_id": f"p1_{i:03d}",
            "locator": f"测试文本/第{i}句",
            "raw_text": line,
            "normalized_text": line,
        }
        for i, line in enumerate(lines, start=1)
    ]
    (corpus / "segments.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=""
    )
    registry = {
        "sources": [
            {
                "source_id": "src_p1_short",
                "work": fixture["work"],
                "author": fixture["author"],
                "edition": fixture["edition"],
                "source_name": "P1 local fixture",
                "url": "https://example.invalid/p1-short",
                "retrieved_at": "2026-11-03T00:00:00Z",
                "license": "test fixture only",
                "commercial_use": "not applicable",
                "scope": "replaceable short test text",
                "locator": "测试文本/第1句",
                "original_text_path": "original_text.txt",
                "normalized_text_path": "normalized_text.txt",
                "segments_path": "segments.json",
                "normalization_map_path": "normalization_map.json",
                "content_sha256": sha256_bytes(original.encode("utf-8")),
                "normalized_sha256": sha256_bytes(normalized.encode("utf-8")),
                "status": "PASS_STATIC",
                "notes": "P1 end-to-end fixture; not production content.",
            }
        ]
    }
    (corpus / "source_registry.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=""
    )
    claims = [
        {
            "claim_id": f"p1_original_{i:03d}",
            "work": fixture["work"],
            "author": fixture["author"],
            "edition": fixture["edition"],
            "source_refs": ["src_p1_short"],
            "locator": f"测试文本/第{i}句",
            "quote": line,
            "source_quote": line,
            "display_quote": line,
            "claim_type": "original_text",
            "statement": f"P1 夹具原文第 {i} 句。",
            "confidence": "high",
            "review_status": "unreviewed",
            "notes": "fixture only",
        }
        for i, line in enumerate(lines, start=1)
    ]
    (corpus / "claims.json").write_text(
        json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=""
    )
    (corpus / "reviews.json").write_text("[]\n", encoding="utf-8", newline="")
    return corpus


async def run_task(runner: TaskRunner, store: WorkspaceStore, kind: str, params: dict) -> dict:
    task = runner.create(kind, params)
    task_id = task["id"]
    print(f"\n[task] {kind} -> {task_id} ({task['status']})", flush=True)
    if task["status"] == "BLOCKED":
        print("[blocked]", task.get("error"), flush=True)
        raise SystemExit(2)
    while True:
        current = store.get_task(task_id)
        if current["status"] not in ("PENDING", "RUNNING"):
            break
        await asyncio.sleep(3)
    print(f"[task] {kind} {current['status']} exit={current.get('exit_code')}", flush=True)
    if current.get("error"):
        print("[error]", current["error"][:1500], flush=True)
    log_path = ROOT / (current.get("log_path") or "")
    if log_path.is_file():
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        print("[log tail]\n" + tail, flush=True)
    if current["status"] != "SUCCEEDED":
        raise SystemExit(3)
    return current


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="tests/fixtures/p1_lines.json")
    parser.add_argument("--project-id", default="proj_p1_short")
    parser.add_argument("--episode-id", default="ep_p1_short")
    parser.add_argument("--style-id", default="style_p1_short")
    parser.add_argument("--resume", action="store_true", help="skip package.build and reuse an existing production_script.json")
    args = parser.parse_args()
    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = ROOT / fixture_path
    fixture = load_fixture(fixture_path)
    art_root = f"projects/{args.project_id}/episodes/{args.episode_id}/work"

    store = WorkspaceStore()
    ensure_case(store, fixture, args.project_id, args.episode_id, args.style_id, art_root)
    ensure_corpus(ROOT, art_root, fixture)
    runner = TaskRunner(store)
    if not args.resume:
        await run_task(runner, store, "package.build", {"episode_id": args.episode_id})
    await run_task(
        runner,
        store,
        "script.generate",
        {
            "episode_id": args.episode_id,
            "speaker": "中文女",
            "speed": 1.0,
            "reuse": args.resume,
            "confirm": True,
        },
    )
    await run_task(
        runner,
        store,
        "tts.synthesize",
        {"episode_id": args.episode_id, "speaker": "中文女", "confirm": True},
    )
    await run_task(
        runner,
        store,
        "comfy.batch",
        {"jobs": f"{art_root}/comfy/jobs.json", "confirm": True, "timeout": 1800},
    )
    await run_task(runner, store, "segments.build", {"episode_id": args.episode_id})
    await run_task(runner, store, "build.rebuild", {"episode_id": args.episode_id})
    await run_task(runner, store, "quality.check", {"episode_id": args.episode_id})
    print("\nP1_E2E_OK", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
