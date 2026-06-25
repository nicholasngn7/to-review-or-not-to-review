"""Review engine: selects a provider and aggregates its per-persona reviews.

The engine parses the diff, hands it to the configured `ReviewProvider` (mock by
default), and aggregates the returned `PersonaReview`s into the shared
`ReviewResponse` contract: overall risk, merge recommendation, summary, diff
stats, persona reviews, and a flattened findings list.

Provider selection is driven by `REVIEW_PROVIDER` (see `app.core.config`). The
API response contract is independent of which provider runs.
"""

from __future__ import annotations

from typing import Optional

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
from app.models.tone import ToneProfile, resolve_tone_profile
from app.services.diff_parser import parse_diff
from app.services.providers import ReviewProvider, create_provider

# Personas whose high-severity findings warrant a human's eyes before merge.
_SENSITIVE_PERSONAS = {ReviewerPersona.SECURITY, ReviewerPersona.ARCHITECT}


def _dedupe_personas(personas: list[ReviewerPersona]) -> list[ReviewerPersona]:
    """Preserve order, drop duplicates."""
    seen: set[ReviewerPersona] = set()
    ordered: list[ReviewerPersona] = []
    for persona in personas:
        if persona not in seen:
            seen.add(persona)
            ordered.append(persona)
    return ordered


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


def run_review(
    request: ReviewRequest, provider: Optional[ReviewProvider] = None
) -> ReviewResponse:
    """Run the selected personas over the request's diff and aggregate results.

    `provider` can be injected (mainly for tests); otherwise the configured
    provider (`REVIEW_PROVIDER`, default ``mock``) is used.
    """
    parsed = parse_diff(request.diff_text)
    provider = provider or create_provider()

    personas = _dedupe_personas(request.selected_personas)
    # Resolve tone per persona (per-persona override -> global -> default) and pass
    # it to the provider. Tone is presentation only and never affects aggregation.
    tone_profiles: dict[ReviewerPersona, ToneProfile] = {
        persona: resolve_tone_profile(persona, request) for persona in personas
    }
    persona_reviews: list[PersonaReview] = provider.review(
        parsed,
        personas,
        title=request.title,
        description=request.description,
        tone_profiles=tone_profiles,
    )

    all_findings: list[ReviewFinding] = [
        finding for pr in persona_reviews for finding in pr.findings
    ]

    overall_risk = _aggregate_risk(all_findings)
    recommendation = _recommend(all_findings)
    summary = _build_summary(all_findings, recommendation, len(persona_reviews))

    return ReviewResponse(
        overall_risk=overall_risk,
        merge_recommendation=recommendation,
        summary=summary,
        diff_stats=parsed.stats,
        persona_reviews=persona_reviews,
        findings=all_findings,
    )
