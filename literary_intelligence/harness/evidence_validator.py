from __future__ import annotations

from dataclasses import dataclass, field

from literary_intelligence.schemas.claim import Claim

from .source_registry import SourceRegistry


UNKNOWN_SOURCE = "UNKNOWN_SOURCE"
MISSING_SOURCE = "MISSING_SOURCE"
INVALID_LOCATOR = "INVALID_LOCATOR"
QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
SOURCE_QUOTE_NOT_FOUND = "SOURCE_QUOTE_NOT_FOUND"
QUOTE_WITHOUT_SOURCE = "QUOTE_WITHOUT_SOURCE"
MISSING_QUOTE = "MISSING_QUOTE"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    claim_id: str
    field: str


@dataclass
class ValidationResult:
    claim_id: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def codes(self) -> list[str]:
        return [issue.code for issue in self.issues]


def _issue(result: ValidationResult, code: str, message: str, field: str) -> None:
    result.issues.append(ValidationIssue(code, message, result.claim_id, field))


def validate_claim(claim: Claim, registry: SourceRegistry) -> ValidationResult:
    result = ValidationResult(claim_id=claim.claim_id)
    refs = list(dict.fromkeys(claim.source_refs))
    valid_sources = []
    for ref in refs:
        if registry.has(ref):
            valid_sources.append(registry.get(ref))
        else:
            _issue(result, UNKNOWN_SOURCE, f"source_ref does not exist: {ref}", "source_refs")

    if claim.claim_type in ("original_text", "historical_fact") and not refs:
        _issue(
            result,
            MISSING_SOURCE,
            f"{claim.claim_type} claim requires at least one source_ref",
            "source_refs",
        )
    if claim.claim_type == "original_text" and not claim.quote:
        _issue(result, MISSING_QUOTE, "original_text claim requires a quote", "quote")

    if claim.quote and not refs:
        _issue(result, QUOTE_WITHOUT_SOURCE, "quote present but no source_refs", "quote")

    if claim.source_quote and not refs:
        _issue(result, QUOTE_WITHOUT_SOURCE, "source_quote present but no source_refs", "source_quote")

    if valid_sources:
        if not any(src.has_locator(claim.locator) for src in valid_sources):
            _issue(result, INVALID_LOCATOR, f"locator not found in referenced sources: {claim.locator}", "locator")
        normalized_text = "\n".join(src.normalized_text for src in valid_sources)
        raw_text = "\n".join(src.original_text for src in valid_sources)
        if claim.quote and claim.quote not in normalized_text:
            _issue(result, QUOTE_NOT_FOUND, "normalized quote not found in source", "quote")
        if claim.source_quote and claim.source_quote not in raw_text:
            _issue(result, SOURCE_QUOTE_NOT_FOUND, "source_quote not found in raw source", "source_quote")

    return result


def assert_valid(claim: Claim, registry: SourceRegistry) -> None:
    result = validate_claim(claim, registry)
    if not result.ok:
        messages = "; ".join(f"{i.code}: {i.message}" for i in result.issues)
        raise ValueError(f"Invalid claim {claim.claim_id}: {messages}")
