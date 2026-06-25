"""Shared domain models for the MR Review Council review contract."""

from .base import CamelModel
from .comments import (
    CommentThread,
    CommentThreadStatus,
    SuggestedReply,
    ThreadComment,
)
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
from .git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportCommentsRequest,
    ImportCommentsResponse,
    ImportedCommentThread,
)
from .review import (
    HunkReference,
    PersonaReview,
    ReviewFinding,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
)
from .tone import (
    DEFAULT_TONE_PROFILE,
    ToneProfile,
    ToneStrictness,
    ToneStyle,
    ToneVerbosity,
    resolve_tone_profile,
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
    # tone
    "ToneStyle",
    "ToneStrictness",
    "ToneVerbosity",
    "ToneProfile",
    "DEFAULT_TONE_PROFILE",
    "resolve_tone_profile",
    # comments
    "CommentThreadStatus",
    "ThreadComment",
    "CommentThread",
    "SuggestedReply",
    # git import contracts (v0.3, Phase 1 — contracts only)
    "GitProviderType",
    "ExternalCommentReference",
    "ImportedCommentThread",
    "ImportCommentsRequest",
    "ImportCommentsResponse",
]
