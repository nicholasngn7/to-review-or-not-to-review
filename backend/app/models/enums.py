"""Enumerations for the MR Review Council review contract.

These are the canonical, stable string values shared between the backend and
the frontend. Keep the values in sync with `frontend/src/types/review.ts`.
"""

from enum import Enum


class ReviewerPersona(str, Enum):
    """The engineering perspective a review is produced from."""

    ARCHITECT = "architect"
    QA = "qa"
    SECURITY = "security"
    FRONTEND = "frontend"
    BACKEND = "backend"
    SRE = "sre"
    PRODUCT = "product"


class RiskLevel(str, Enum):
    """Overall risk a change carries."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MergeRecommendation(str, Enum):
    """The council's recommendation on whether to merge."""

    READY = "ready"
    READY_WITH_FOLLOWUPS = "ready_with_followups"
    NEEDS_CHANGES = "needs_changes"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class FindingSeverity(str, Enum):
    """Severity of an individual finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
