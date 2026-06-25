"""Pure, fixture-driven Git provider comment-import mappers (v0.3).

This package normalizes already-parsed provider comment JSON into the existing
`ImportedCommentThread` / `CommentThread` contract. It performs **no** network calls,
uses **no** tokens, and exposes **no** endpoints — provider payloads are supplied by
the caller (today: test fixtures). GitHub PR review comments land in Phase 2; GitLab
discussions and an orchestrator follow in later phases.
"""

from .common import (
    clean_body,
    resolve_status,
    synthetic_thread_id,
    to_thread_comment,
)
from .github import (
    map_github_issue_comments_to_threads,
    map_github_review_comments_to_threads,
)
from .gitlab import map_gitlab_discussions_to_threads
from .orchestrator import (
    SOURCE_GITHUB_ISSUE_COMMENTS,
    SOURCE_GITHUB_REVIEW_COMMENTS,
    SOURCE_GITLAB_DISCUSSIONS,
    import_comments,
)

__all__ = [
    "clean_body",
    "synthetic_thread_id",
    "to_thread_comment",
    "resolve_status",
    "map_github_review_comments_to_threads",
    "map_github_issue_comments_to_threads",
    "map_gitlab_discussions_to_threads",
    "import_comments",
    "SOURCE_GITHUB_REVIEW_COMMENTS",
    "SOURCE_GITHUB_ISSUE_COMMENTS",
    "SOURCE_GITLAB_DISCUSSIONS",
]
