from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from literary_intelligence.schemas.claim import Claim
from literary_intelligence.schemas.llm_pass import LLMPassOutput, PassName

from .evidence_validator import ValidationResult, validate_claim
from .llm_client import LLMClient, MockLLMClient
from .source_registry import SourceRegistry


PASS_ORDER: tuple[PassName, ...] = (
    "text_analyst",
    "literary_analyst",
    "researcher",
    "skeptic",
    "editor",
)


class RoleContractError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class TargetCoverage:
    target_locator: str
    target_claim_ids: tuple[str, ...]
    contextual_claim_ids: tuple[str, ...]
    not_analyzable: bool
    ok: bool


@dataclass
class PipelineResult:
    outputs: list[LLMPassOutput]
    validations: dict[str, ValidationResult]
    target_coverage: TargetCoverage | None = None

    @property
    def all_valid(self) -> bool:
        return all(v.ok for v in self.validations.values())


def _target_from_registry(registry: SourceRegistry) -> dict:
    for source in registry.sources.values():
        segment = source.segment_text(source.record.locator)
        if segment is not None:
            return {
                "source_id": source.record.source_id,
                "work": source.record.work,
                "locator": source.record.locator,
                "raw_text": segment["raw_text"],
                "normalized_text": segment["normalized_text"],
            }
    raise RoleContractError("TARGET_NOT_CONFIGURED", "No source target locator is registered")


def build_context(registry: SourceRegistry, claims: list[Claim] | None = None) -> dict:
    sources = []
    for source in registry.sources.values():
        sources.append({
            "source_id": source.record.source_id,
            "work": source.record.work,
            "author": source.record.author,
            "edition": source.record.edition,
            "locator": source.record.locator,
            "license": source.record.license,
            "commercial_use": source.record.commercial_use,
            "raw_text": source.original_text,
            "normalized_text": source.normalized_text,
            "segments": list(source.segments),
        })
    registered = claims or []
    return {
        "source_ids": sorted(registry.sources),
        "target": _target_from_registry(registry),
        "sources": sources,
        "claims": [claim.model_dump() for claim in registered],
        "approved_claims": [
            claim.model_dump() for claim in registered if claim.review_status == "approved"
        ],
        "instruction": "Return only candidate claims; do not self-approve.",
    }


def check_text_analyst(output: LLMPassOutput, target: dict) -> TargetCoverage:
    target_locator = target["locator"]
    if output.coverage == "not_analyzable":
        if output.claims:
            raise RoleContractError(
                "TEXT_NOT_ANALYZABLE_WITH_CLAIMS",
                "not_analyzable must not carry claims",
            )
        return TargetCoverage(target_locator, (), (), True, True)
    if output.coverage != "target":
        raise RoleContractError(
            "TEXT_COVERAGE_MISSING",
            "text_analyst must set coverage=target or coverage=not_analyzable",
        )
    target_claim_ids: list[str] = []
    contextual_ids: list[str] = []
    for claim in output.claims:
        if claim.locator == target_locator:
            if claim.scope != "target":
                raise RoleContractError(
                    "TARGET_CLAIM_SCOPE_MISMATCH",
                    f"{claim.claim_id} locator is target but scope={claim.scope}",
                )
            target_claim_ids.append(claim.claim_id)
        else:
            if claim.scope != "contextual":
                raise RoleContractError(
                    "CONTEXTUAL_CLAIM_SCOPE_REQUIRED",
                    f"{claim.claim_id} is outside target locator but scope={claim.scope}",
                )
            contextual_ids.append(claim.claim_id)
    if not target_claim_ids:
        raise RoleContractError(
            "TARGET_NOT_COVERED",
            "text_analyst produced no claim at the target locator",
        )
    return TargetCoverage(
        target_locator,
        tuple(target_claim_ids),
        tuple(contextual_ids),
        False,
        True,
    )


def check_researcher(output: LLMPassOutput, registered_claims: list[Claim]) -> None:
    for claim in output.claims:
        if claim.claim_type == "original_text":
            raise RoleContractError(
                "RESEARCHER_ORIGINAL_TEXT",
                f"researcher may not output original_text claim: {claim.claim_id}",
            )
        for existing in registered_claims:
            same_id = claim.claim_id == existing.claim_id
            same_quote = (
                bool(claim.source_quote)
                and claim.source_quote == existing.source_quote
                and claim.locator == existing.locator
            )
            if same_id or same_quote:
                raise RoleContractError(
                    "RESEARCHER_DUPLICATE_CLAIM",
                    f"researcher repeated existing claim {existing.claim_id}",
                )
        if claim.claim_type == "historical_fact" and not claim.source_refs:
            raise RoleContractError(
                "RESEARCHER_UNSOURCED_FACT",
                f"historical_fact {claim.claim_id} has no source_refs",
            )


def check_skeptic(output: LLMPassOutput) -> None:
    if output.claims:
        raise RoleContractError("SKEPTIC_CLAIMS_NOT_ALLOWED", "skeptic must not output claims")
    if output.skeptic_verdict == "not_reviewed":
        raise RoleContractError("SKEPTIC_NOT_REVIEWED", "skeptic did not return a verdict")
    if output.skeptic_verdict == "findings":
        if not output.skeptic_findings:
            raise RoleContractError("SKEPTIC_FINDINGS_MISSING", "findings verdict has no findings")
        for finding in output.skeptic_findings:
            if finding.verdict != "risk":
                raise RoleContractError(
                    "SKEPTIC_VERDICT_MISMATCH",
                    f"{finding.target_claim_id} finding has verdict={finding.verdict}",
                )
    elif output.skeptic_verdict == "no_material_risk":
        if not output.reviewed_dimensions:
            raise RoleContractError(
                "SKEPTIC_DIMENSIONS_MISSING",
                "no_material_risk must list reviewed dimensions",
            )


def check_editor(output: LLMPassOutput, approved_claims: list[Claim]) -> None:
    if output.claims:
        raise RoleContractError("EDITOR_CLAIMS_NOT_ALLOWED", "editor must not create claims")
    if not approved_claims and output.draft_text.strip():
        raise RoleContractError(
            "EDITOR_DRAFT_WITHOUT_APPROVAL",
            "editor produced draft text without approved claims",
        )


def check_role_contracts(
    pass_name: PassName,
    output: LLMPassOutput,
    target: dict,
    registered_claims: list[Claim],
) -> TargetCoverage | None:
    if pass_name == "text_analyst":
        return check_text_analyst(output, target)
    if pass_name == "researcher":
        check_researcher(output, registered_claims)
    elif pass_name == "skeptic":
        check_skeptic(output)
    elif pass_name == "editor":
        approved = [c for c in registered_claims if c.review_status == "approved"]
        check_editor(output, approved)
    return None


def run_pipeline(
    registry: SourceRegistry,
    client: LLMClient,
    claims: list[Claim] | None = None,
) -> PipelineResult:
    """Run five role passes without approving any claim."""
    outputs: list[LLMPassOutput] = []
    validations: dict[str, ValidationResult] = {}
    registered = claims or []
    context = build_context(registry, registered)
    target_coverage: TargetCoverage | None = None
    for pass_name in PASS_ORDER:
        output = client.complete(pass_name, context)
        if output.pass_name != pass_name:
            raise RoleContractError(
                "PASS_NAME_MISMATCH",
                f"expected {pass_name}, got {output.pass_name}",
            )
        for claim in output.claims:
            if claim.review_status != "unreviewed":
                raise RoleContractError(
                    "LLM_SELF_APPROVAL",
                    f"LLM claim {claim.claim_id} has review_status={claim.review_status}",
                )
            validations[claim.claim_id] = validate_claim(claim, registry)
        coverage = check_role_contracts(pass_name, output, context["target"], registered)
        if coverage is not None:
            target_coverage = coverage
        outputs.append(output)
        context["previous_pass"] = pass_name
        context["previous_claims"] = [c.model_dump() for c in output.claims]
    return PipelineResult(
        outputs=outputs,
        validations=validations,
        target_coverage=target_coverage,
    )


def run_mock_pipeline(registry: SourceRegistry, fixture_path: Path) -> PipelineResult:
    return run_pipeline(registry, MockLLMClient(fixture_path))
