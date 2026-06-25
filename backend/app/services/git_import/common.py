"""Shared, pure helpers for Git provider comment-import mappers (v0.3, Phase 2).

These helpers are deliberately tiny and side-effect free: parsed JSON-ish values in,
domain objects out. No network, no tokens, no I/O. They are shared by the per-provider
mappers (GitHub first; GitLab later) so normalization rules live in one place.
"""

from __future__ import annotations

from typing import Optional

from app.models.comments import CommentThreadStatus, ThreadComment
from app.models.git_import import GitProviderType


def clean_body(value: object) -> Optional[str]:
    """Trim a comment body; return None for missing/empty/whitespace-only values.

    Non-string values (e.g. None, numbers from malformed payloads) yield None so the
    caller can drop the comment rather than fabricate text.
    """
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def synthetic_thread_id(provider: object, *parts: object) -> str:
    """Build a deterministic, readable thread id stable across repeated imports.

    The id is a colon-joined string of the provider plus the supplied parts (None
    parts are skipped). It contains no randomness or timestamps, so importing the
    same payload twice yields identical ids — safe to use as `CommentThread.id`.
    """
    head = provider.value if isinstance(provider, GitProviderType) else str(provider)
    pieces = [head]
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if text:
            pieces.append(text)
    return ":".join(pieces)


def to_thread_comment(
    *,
    comment_id: object,
    body: object,
    author: Optional[str] = None,
    created_at: Optional[str] = None,
    is_resolved: Optional[bool] = None,
) -> Optional[ThreadComment]:
    """Map provider comment fields into a `ThreadComment`, or None if unusable.

    Bodies are trimmed; a comment with no usable body returns None so the caller can
    drop it (the contract forbids empty comment bodies).
    """
    cleaned = clean_body(body)
    if cleaned is None:
        return None
    return ThreadComment(
        id=str(comment_id),
        author=author,
        body=cleaned,
        created_at=created_at,
        is_resolved=is_resolved,
    )


def resolve_status(resolved: Optional[bool]) -> CommentThreadStatus:
    """Map a provider's resolution flag onto the existing `CommentThreadStatus`.

    * `True`  -> `resolved`
    * `False` -> `open`
    * `None`  -> `unknown` (provider didn't expose resolution state)
    """
    if resolved is None:
        return CommentThreadStatus.UNKNOWN
    return CommentThreadStatus.RESOLVED if resolved else CommentThreadStatus.OPEN


def first_present(data: dict, *keys: str) -> object:
    """Return the first non-None value among `keys` in `data` (tolerant `.get`)."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None
