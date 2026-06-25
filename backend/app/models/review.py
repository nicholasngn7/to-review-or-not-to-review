"""Review request/response models — the core API contract.

This is the shape exchanged between the frontend and `POST /api/reviews`.
The review engine lives in `app.services.review_engine`.
"""

from typing import Optional

from pydantic import Field

from .base import CamelModel
from .diff import DiffStats
from .enums import (
    FindingSeverity,
    MergeRecommendation,
    ReviewerPersona,
    RiskLevel,
)


class ReviewRequest(CamelModel):
    """Incoming request to review a diff through the selected personas."""

    diff_text: str = Field(description="Raw unified diff / patch text to review.")
    selected_personas: list[ReviewerPersona] = Field(
        default_factory=list,
        description="Personas to run. Empty implies the caller picks none yet.",
    )
    title: Optional[str] = Field(
        default=None, description="Optional MR/PR title for context."
    )
    description: Optional[str] = Field(
        default=None, description="Optional MR/PR description for context."
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional origin hint, e.g. 'gitlab' or 'github'.",
    )


class HunkReference(CamelModel):
    """Points a finding at a specific hunk (and optionally a line) in a file."""

    hunk_index: int = Field(
        description="Index of the hunk within its DiffFile.hunks list."
    )
    header: Optional[str] = Field(
        default=None, description="The hunk's @@ header, for display."
    )
    line: Optional[int] = Field(
        default=None,
        description="New-file line number the finding refers to, when known.",
    )


class ReviewFinding(CamelModel):
    """A single 'finding card' produced by a reviewer persona."""

    id: str = Field(description="Stable identifier for this finding.")
    reviewer: ReviewerPersona
    severity: FindingSeverity
    title: str
    explanation: str = Field(description="What the issue is and why it matters.")
    recommendation: str = Field(description="Suggested action to address it.")
    file_path: Optional[str] = Field(
        default=None, description="File the finding relates to, if any."
    )
    hunk_reference: Optional[HunkReference] = Field(
        default=None, description="Hunk/line the finding is tied to, if any."
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence in this finding, 0.0-1.0.",
    )


class PersonaReview(CamelModel):
    """One persona's verdict and findings."""

    persona: ReviewerPersona
    risk_level: RiskLevel
    summary: str = Field(description="This persona's short narrative summary.")
    findings: list[ReviewFinding] = Field(default_factory=list)


class ReviewSummary(CamelModel):
    """Council-level summary of the whole review."""

    headline: str = Field(description="One-line takeaway.")
    details: str = Field(description="Longer narrative summary.")
    total_findings: int = 0
    findings_by_severity: dict[FindingSeverity, int] = Field(
        default_factory=dict,
        description="Count of findings per severity level.",
    )


class ReviewResponse(CamelModel):
    """The full review result returned to the frontend."""

    overall_risk: RiskLevel
    merge_recommendation: MergeRecommendation
    summary: ReviewSummary
    diff_stats: DiffStats
    persona_reviews: list[PersonaReview] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(
        default_factory=list,
        description="Flattened finding cards across all personas, for display.",
    )
