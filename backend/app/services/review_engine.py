"""Review engine: orchestrates personas and aggregates their findings.

Parses the diff, runs the selected personas through the mock provider, and
aggregates everything into the shared `ReviewResponse` contract. Deterministic
and fully offline.
"""

from __future__ import annotations

from app.models.enums import (
    FindingSeverity,
    MergeRecommendation,
    ReviewerPersona,
    RiskLevel,
)
from app.models.review import (
    PersonaReview,
    ReviewFinding,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
)
from app.services.diff_parser import parse_diff
from app.services.mock_review_provider import MockReviewProvider

# Personas whose high-severity findings warrant a human's eyes before merge.
_SENSITIVE_PERSONAS = {ReviewerPersona.SECURITY, ReviewerPersona.ARCHITECT}

_SEVERITY_ORDER = {
    FindingSeverity.INFO: 0,
    FindingSeverity.LOW: 1,
    FindingSeverity.MEDIUM: 2,
    FindingSeverity.HIGH: 3,
}


def _dedupe_personas(personas: list[ReviewerPersona]) -> list[ReviewerPersona]:
    """Preserve order, drop duplicates."""
    seen: set[ReviewerPersona] = set()
    ordered: list[ReviewerPersona] = []
    for persona in personas:
        if persona not in seen:
            seen.add(persona)
            ordered.append(persona)
    return ordered


def _persona_risk(findings: list[ReviewFinding]) -> RiskLevel:
    if not findings:
        return RiskLevel.LOW
    top = max(_SEVERITY_ORDER[f.severity] for f in findings)
    if top >= _SEVERITY_ORDER[FindingSeverity.HIGH]:
        return RiskLevel.HIGH
    if top >= _SEVERITY_ORDER[FindingSeverity.MEDIUM]:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _persona_summary(
    persona: ReviewerPersona, findings: list[ReviewFinding]
) -> str:
    if not findings:
        return f"No concerns from the {persona.value} reviewer."
    highs = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
    mediums = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
    parts = [f"{len(findings)} finding(s)"]
    if highs:
        parts.append(f"{highs} high")
    if mediums:
        parts.append(f"{mediums} medium")
    return f"{persona.value} reviewer raised " + ", ".join(parts) + "."


def _aggregate_risk(findings: list[ReviewFinding]) -> RiskLevel:
    if any(f.severity == FindingSeverity.HIGH for f in findings):
        return RiskLevel.HIGH
    if any(f.severity == FindingSeverity.MEDIUM for f in findings):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _recommend(findings: list[ReviewFinding]) -> MergeRecommendation:
    highs = [f for f in findings if f.severity == FindingSeverity.HIGH]
    mediums = [f for f in findings if f.severity == FindingSeverity.MEDIUM]
    lows = [f for f in findings if f.severity == FindingSeverity.LOW]

    sensitive_high = any(f.reviewer in _SENSITIVE_PERSONAS for f in highs)

    if sensitive_high:
        return MergeRecommendation.NEEDS_HUMAN_REVIEW
    if highs or len(mediums) >= 3:
        return MergeRecommendation.NEEDS_CHANGES
    if mediums or lows:
        return MergeRecommendation.READY_WITH_FOLLOWUPS
    return MergeRecommendation.READY


_RECOMMENDATION_HEADLINE = {
    MergeRecommendation.READY: "Looks ready to merge.",
    MergeRecommendation.READY_WITH_FOLLOWUPS: "Mergeable with a few follow-ups.",
    MergeRecommendation.NEEDS_CHANGES: "Changes recommended before merge.",
    MergeRecommendation.NEEDS_HUMAN_REVIEW: "Needs human review before merge.",
}


def _build_summary(
    findings: list[ReviewFinding],
    recommendation: MergeRecommendation,
    persona_count: int,
) -> ReviewSummary:
    by_severity: dict[FindingSeverity, int] = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    headline = _RECOMMENDATION_HEADLINE[recommendation]
    if not findings:
        details = (
            f"{persona_count} reviewer(s) ran and found no notable issues in this diff."
        )
    else:
        sev_bits = ", ".join(
            f"{by_severity[s]} {s.value}"
            for s in (
                FindingSeverity.HIGH,
                FindingSeverity.MEDIUM,
                FindingSeverity.LOW,
                FindingSeverity.INFO,
            )
            if by_severity.get(s)
        )
        details = (
            f"{persona_count} reviewer(s) produced {len(findings)} finding(s) "
            f"({sev_bits})."
        )

    return ReviewSummary(
        headline=headline,
        details=details,
        total_findings=len(findings),
        findings_by_severity=by_severity,
    )


def run_review(request: ReviewRequest) -> ReviewResponse:
    """Run the selected personas over the request's diff and aggregate results."""
    parsed = parse_diff(request.diff_text)
    provider = MockReviewProvider(parsed)

    persona_reviews: list[PersonaReview] = []
    all_findings: list[ReviewFinding] = []

    personas = _dedupe_personas(request.selected_personas)
    for persona in personas:
        findings = provider.review(persona)
        persona_reviews.append(
            PersonaReview(
                persona=persona,
                risk_level=_persona_risk(findings),
                summary=_persona_summary(persona, findings),
                findings=findings,
            )
        )
        all_findings.extend(findings)

    overall_risk = _aggregate_risk(all_findings)
    recommendation = _recommend(all_findings)
    summary = _build_summary(all_findings, recommendation, len(personas))

    return ReviewResponse(
        overall_risk=overall_risk,
        merge_recommendation=recommendation,
        summary=summary,
        diff_stats=parsed.stats,
        persona_reviews=persona_reviews,
        findings=all_findings,
    )
