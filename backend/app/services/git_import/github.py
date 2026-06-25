"""Pure GitHub PR review-comment mapper (v0.3, Phase 2).

Normalizes already-parsed, GitHub-style review-comment dicts into the existing
`ImportedCommentThread` / `CommentThread` contract. Strictly:

* no network calls, no HTTP clients, no tokens,
* defensive `.get(...)` parsing (the exact provider shape is still to be verified
  against official GitHub docs — see `docs/v0.3-plan-git-comment-import-mappers.md`),
* deterministic output ordered by first-seen root order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.comments import CommentThread, ThreadComment
from app.models.git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportedCommentThread,
)

from .common import (
    clean_body,
    first_present,
    resolve_status,
    synthetic_thread_id,
    to_thread_comment,
)


@dataclass
class _Assembling:
    """Mutable scratch state for a thread being built from one or more comments."""

    root_id: str
    comments: list[ThreadComment]
    file_path: Optional[str] = None
    line: Optional[int] = None
    resolved: Optional[bool] = None
    is_outdated: Optional[bool] = None
    review_id: Optional[str] = None
    web_url: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


def _reply_target(comment: dict) -> object:
    return first_present(comment, "in_reply_to_id", "inReplyToId")


def _author(comment: dict) -> Optional[str]:
    user = comment.get("user")
    if isinstance(user, dict):
        login = user.get("login") or user.get("name")
        if isinstance(login, str) and login.strip():
            return login.strip()
    author = comment.get("author")
    return author if isinstance(author, str) and author.strip() else None


def _created_at(comment: dict) -> Optional[str]:
    value = first_present(comment, "created_at", "createdAt")
    return value if isinstance(value, str) else None


def _line(comment: dict) -> Optional[int]:
    # Prefer the current-diff line; fall back to the original line.
    value = first_present(
        comment, "line", "original_line", "originalLine", "position"
    )
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _outdated_raw(comment: dict) -> Optional[bool]:
    value = first_present(comment, "outdated", "is_outdated", "isOutdated")
    return bool(value) if value is not None else None


def _resolved_raw(comment: dict) -> Optional[bool]:
    value = first_present(comment, "resolved", "is_resolved", "isResolved")
    return bool(value) if value is not None else None


def _review_id(comment: dict) -> Optional[str]:
    value = first_present(
        comment, "pull_request_review_id", "pullRequestReviewId", "review_id", "reviewId"
    )
    return str(value) if value is not None else None


def _web_url(comment: dict) -> Optional[str]:
    value = first_present(comment, "html_url", "htmlUrl", "web_url", "webUrl")
    return value if isinstance(value, str) and value.strip() else None


def map_github_review_comments_to_threads(
    comments: list[dict],
    *,
    repository: Optional[str] = None,
    pull_request_number: Optional[int] = None,
    include_resolved: bool = True,
    include_outdated: bool = False,
) -> list[ImportedCommentThread]:
    """Normalize GitHub PR review comments into `ImportedCommentThread`s.

    Roots (no `in_reply_to_id`) become threads; replies attach to their root thread.
    Empty-body comments are dropped; outdated/resolved threads are filtered per the
    `include_*` flags. Output order follows first-seen root order.
    """
    if not comments:
        return []

    roots: dict[str, _Assembling] = {}
    roots_order: list[str] = []
    skipped_roots: set[str] = set()

    # Pass 1: roots (comments that are not replies).
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        if _reply_target(comment) is not None:
            continue

        root_id = str(comment.get("id"))
        body = clean_body(comment.get("body"))
        if body is None:
            # Empty-body root: drop it; any replies become missing-root threads.
            continue

        resolved = _resolved_raw(comment)
        outdated = _outdated_raw(comment)

        if outdated and not include_outdated:
            skipped_roots.add(root_id)
            continue
        if resolved and not include_resolved:
            skipped_roots.add(root_id)
            continue

        warnings: list[str] = []
        line = _line(comment)
        if outdated and include_outdated:
            # The current-diff line is no longer reliable for outdated anchors.
            line = None
            warnings.append(
                f"comment {root_id} is outdated; line context was dropped"
            )

        comment_obj = to_thread_comment(
            comment_id=comment.get("id"),
            body=comment.get("body"),
            author=_author(comment),
            created_at=_created_at(comment),
            is_resolved=resolved,
        )
        if comment_obj is None:
            continue

        path = comment.get("path")
        roots[root_id] = _Assembling(
            root_id=root_id,
            comments=[comment_obj],
            file_path=path if isinstance(path, str) and path.strip() else None,
            line=line,
            resolved=resolved,
            is_outdated=outdated,
            review_id=_review_id(comment),
            web_url=_web_url(comment),
            warnings=warnings,
        )
        roots_order.append(root_id)

    # Pass 2: replies (attach to root, or create a standalone thread + warning).
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        target = _reply_target(comment)
        if target is None:
            continue

        target_id = str(target)
        comment_obj = to_thread_comment(
            comment_id=comment.get("id"),
            body=comment.get("body"),
            author=_author(comment),
            created_at=_created_at(comment),
            is_resolved=_resolved_raw(comment),
        )
        if comment_obj is None:
            continue  # empty-body reply: drop.

        if target_id in roots:
            roots[target_id].comments.append(comment_obj)
            continue
        if target_id in skipped_roots:
            continue  # parent thread was filtered out; drop the reply with it.

        # Missing root: surface the reply as its own thread with a warning.
        reply_id = str(comment.get("id"))
        path = comment.get("path")
        roots[reply_id] = _Assembling(
            root_id=reply_id,
            comments=[comment_obj],
            file_path=path if isinstance(path, str) and path.strip() else None,
            line=_line(comment),
            resolved=_resolved_raw(comment),
            is_outdated=_outdated_raw(comment),
            review_id=_review_id(comment),
            web_url=_web_url(comment),
            warnings=[
                f"reply {reply_id} references missing root {target_id}; "
                "created a standalone thread"
            ],
        )
        roots_order.append(reply_id)

    results: list[ImportedCommentThread] = []
    for root_id in roots_order:
        assembling = roots[root_id]
        thread = CommentThread(
            id=synthetic_thread_id(
                GitProviderType.GITHUB,
                repository,
                pull_request_number,
                "rc",
                root_id,
            ),
            file_path=assembling.file_path,
            line=assembling.line,
            status=resolve_status(assembling.resolved),
            comments=assembling.comments,
            source="github",
        )
        external = ExternalCommentReference(
            provider=GitProviderType.GITHUB,
            repository=repository,
            pull_request_number=pull_request_number,
            review_id=assembling.review_id,
            comment_id=root_id,
            web_url=assembling.web_url,
            is_outdated=assembling.is_outdated,
        )
        results.append(
            ImportedCommentThread(
                thread=thread,
                external_reference=external,
                warnings=assembling.warnings,
            )
        )

    return results
