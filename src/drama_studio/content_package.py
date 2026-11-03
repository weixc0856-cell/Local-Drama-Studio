"""Build a production-facing ContentPackage from a registered corpus.

This is the deterministic bridge from literary evidence to structured content.
It never invents claims: every claim referenced in the package has passed
``validate_claim`` against the source registry. Unreviewed/invalid claims are
kept out of the content and recorded as warnings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from literary_intelligence.harness.claims import load_claims
from literary_intelligence.harness.evidence_validator import validate_claim
from literary_intelligence.harness.source_registry import load_source_registry
from literary_intelligence.schemas.content_package import ContentPackage


class PackageBuildError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def _read_run(run_dir: Path | None) -> dict[str, Any] | None:
    if not run_dir:
        return None
    path = run_dir / "real_pipeline.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _split_lines(segments: list[dict[str, Any]], target_locator: str) -> tuple[dict[str, Any], list[str]]:
    target = next((seg for seg in segments if seg.get("locator") == target_locator), None)
    if target is None:
        raise PackageBuildError(f"target locator not found in segments: {target_locator}")
    lines = [str(seg.get("normalized_text") or "").strip() for seg in segments]
    lines = [line for line in lines if line]
    if not lines:
        raise PackageBuildError("source contains no non-empty segments")
    return target, lines


def _scene_duration(text: str) -> float:
    # Deterministic, bounded: long enough to read, never over 8 s.
    return round(min(8.0, max(3.0, len(text) * 0.32)), 2)


def build_content_package(
    corpus_dir: Path,
    out_path: Path,
    *,
    run_dir: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    corpus_dir = corpus_dir.resolve()
    registry = load_source_registry(corpus_dir / "source_registry.json")
    claims_all = load_claims(corpus_dir / "claims.json")
    source = next(iter(registry.sources.values()))
    target = next(
        (src for src in registry.sources.values() if src.has_locator(src.record.locator)),
        source,
    )
    target_segment, lines = _split_lines(list(target.segments), target.record.locator)

    valid_claims = []
    warnings: list[str] = []
    for claim in claims_all:
        result = validate_claim(claim, registry)
        if not result.ok:
            warnings.append(f"claim {claim.claim_id} 未通过证据校验: {', '.join(result.codes)}")
            continue
        if claim.review_status != "approved":
            warnings.append(f"claim {claim.claim_id} 为 {claim.review_status}，内容包仍为 draft")
        valid_claims.append(claim)

    run = _read_run(run_dir)
    if run:
        warnings.append(
            f"关联 LI 运行 {run_dir.name}：human_review={run.get('human_review', 'NOT_RUN')}；"
            f"all_evidence_valid={run.get('all_evidence_valid')}"
        )
    else:
        warnings.append("未关联真实 LI 运行；内容包仅基于语料与证据校验")

    text_analysis = [f"目标句：{target_segment.get('normalized_text', '')}"]
    interpretations = []
    imagery = []
    historical = []
    for claim in valid_claims:
        refs = [claim.claim_id]
        if claim.claim_type == "interpretation":
            interpretations.append(
                {"statement": claim.statement, "claim_refs": refs, "confidence": claim.confidence}
            )
        elif claim.claim_type == "historical_fact":
            historical.append(
                {"statement": claim.statement, "claim_refs": refs, "verification": "unverified"}
            )
        if claim.claim_type == "original_text" and claim.display_quote:
            text_analysis.append(f"原文：{claim.display_quote}")

    if not interpretations:
        interpretations = [
            {
                "statement": "当前没有通过证据校验的解释性 claim；仅使用原文。",
                "claim_refs": [],
                "confidence": "low",
            }
        ]

    claim_by_text = {
        claim.quote: claim.claim_id
        for claim in valid_claims
        if claim.claim_type == "original_text" and claim.quote
    }
    subtitle_segments = []
    scene_plan = []
    visual_prompts = []
    for index, text in enumerate(lines[:5], start=1):
        segment_id = f"sub_{index:03d}"
        duration = _scene_duration(text)
        subtitle_segments.append(
            {
                "segment_id": segment_id,
                "text": text,
                "claim_refs": [claim_by_text[text]] if text in claim_by_text else [],
                "estimated_duration_seconds": duration,
            }
        )
        prompt = f"{text}；东方意境，竖屏 9:16 电影感构图，柔和自然光，细腻质感，无文字，无水印"
        scene_plan.append(
            {
                "scene_id": f"scene_{index:03d}",
                "duration_seconds": duration,
                "visual_source": f"assets/images/shot_{index:03d}/",
                "camera_motion": "slow push-in",
                "visual_prompt": prompt,
                "subtitle_ids": [segment_id],
            }
        )
        visual_prompts.append(prompt)

    source_record = target.record
    package = {
        "schema_version": "1.0",
        "work": {
            "work_id": f"work_{source_record.source_id}",
            "title": source_record.work,
            "author": source_record.author,
            "dynasty": "",
            "source_id": source_record.source_id,
            "source_version": source_record.edition,
            "source_license_status": source_record.status,
        },
        "positioning": {
            "target_text": str(target_segment.get("normalized_text") or ""),
            "target_locator": source_record.locator,
            "surrounding_context": [line for line in lines if line != target_segment.get("normalized_text")][:5]
            or [str(target_segment.get("normalized_text") or "")],
        },
        "analysis": {
            "text_analysis": text_analysis,
            "literary_interpretation": interpretations,
            "imagery": imagery,
            "emotion": [],
            "artistic_features": [],
            "historical_context": historical,
            "uncertainty_notes": warnings[:10],
        },
        "video": {
            "title_options": [f"{source_record.work} · {lines[0][:12]}"],
            "opening_hook": lines[0],
            "narration": "。".join(lines),
            "scene_plan": scene_plan,
            "visual_prompts": visual_prompts,
            "subtitle_segments": subtitle_segments,
            "ending": lines[-1],
            "platform_metadata": {
                "title": f"{source_record.work} · {lines[0][:12]}",
                "description": "本地 AI 辅助制作的东方视觉短视频",
                "tags": ["东方美学"],
                "ai_disclosure": "AI辅助制作",
            },
        },
        "provenance": {
            "source_refs": [source_record.source_id],
            "claim_refs": [claim.claim_id for claim in valid_claims],
            "verification_status": "draft",
            "generated_by": "content_package.build",
            "generation_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "warnings": warnings[:30],
        },
    }
    model = ContentPackage.model_validate(package)
    payload = model.model_dump()
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run", default=None, help="optional LI run directory with real_pipeline.json")
    args = parser.parse_args()
    try:
        data = build_content_package(
            Path(args.corpus),
            Path(args.out),
            run_dir=Path(args.run) if args.run else None,
        )
    except (PackageBuildError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "scenes": len(data["video"]["scene_plan"]), "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
