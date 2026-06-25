"""Shared domain models for the MR Review Council review contract."""

from .base import CamelModel
from .diff import (
    DiffFile,
    DiffHunk,
    DiffLine,
    DiffStats,
    FileChangeType,
    LineKind,
    ParsedDiff,
)
from .enums import (
    FindingSeverity,
    MergeRecommendation,
    ReviewerPersona,
    RiskLevel,
)
from .review import (
    HunkReference,
    PersonaReview,
    ReviewFinding,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
)

__all__ = [
    "CamelModel",
    # enums
    "ReviewerPersona",
    "RiskLevel",
    "MergeRecommendation",
    "FindingSeverity",
    # diff
    "LineKind",
    "FileChangeType",
    "DiffLine",
    "DiffHunk",
    "DiffFile",
    "DiffStats",
    "ParsedDiff",
    # review
    "ReviewRequest",
    "HunkReference",
    "ReviewFinding",
    "PersonaReview",
    "ReviewSummary",
    "ReviewResponse",
]
