from __future__ import annotations

from literary_intelligence.schemas.claim import Claim

from .evidence_validator import validate_claim
from .source_registry import SourceRegistry


TYPE_LABELS = {
    "original_text": "原文",
    "historical_fact": "史实",
    "interpretation": "解释",
    "creative": "创作",
}


class ExportError(RuntimeError):
    pass


def approved_claims(claims: list[Claim]) -> list[Claim]:
    return [claim for claim in claims if claim.review_status == "approved"]


def export_markdown(claims: list[Claim], registry: SourceRegistry) -> str:
    selected = approved_claims(claims)
    lines = [
        "# 文学讲解候选",
        "",
        "> 仅输出 review_status=approved 的 claim；解释、史实、创作分别标注。",
        "",
    ]
    if not selected:
        lines.extend(["> 无 approved claim；未审核内容不会进入讲解稿。", ""])
        return "\n".join(lines)
    for claim in selected:
        validation = validate_claim(claim, registry)
        if not validation.ok:
            raise ExportError(
                f"Approved claim {claim.claim_id} is invalid: {', '.join(validation.codes)}"
            )
        lines.append(f"## {claim.claim_id} · {TYPE_LABELS[claim.claim_type]}")
        lines.append("")
        lines.append(claim.statement)
        if claim.display_quote:
            lines.append("")
            lines.append(f"> {claim.display_quote}")
        if claim.source_refs:
            lines.append("")
            lines.append(f"来源：{', '.join(claim.source_refs)}；locator：{claim.locator}")
        lines.append("")
    return "\n".join(lines)


def export_json(claims: list[Claim], registry: SourceRegistry) -> list[dict]:
    selected = approved_claims(claims)
    out = []
    for claim in selected:
        validation = validate_claim(claim, registry)
        if not validation.ok:
            raise ExportError(
                f"Approved claim {claim.claim_id} is invalid: {', '.join(validation.codes)}"
            )
        out.append({
            "claim_id": claim.claim_id,
            "claim_type": claim.claim_type,
            "statement": claim.statement,
            "display_quote": claim.display_quote,
            "source_refs": claim.source_refs,
            "locator": claim.locator,
            "review_status": claim.review_status,
        })
    return out
