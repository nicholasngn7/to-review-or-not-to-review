"""Existing MR/PR comment-thread models and suggested-reply contract (v0.2).

Phase 14 adds the *contract and input foundation* for capturing existing review
discussion threads and (later) drafting replies to them. Important framing:

* This is about **suggested / draft replies** a human can copy — never autonomous
  commenting. Nothing here posts back to GitHub/GitLab.
* Phase 14 only captures `CommentThread`s as structured input and reserves the
  `SuggestedReply` shape. Deterministic reply *generation* arrives in Phase 15.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from .base import CamelModel
from .enums import ReviewerPersona
from .tone import ToneProfile


class CommentThreadStatus(str, Enum):
    """Resolution state of an existing comment thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


class ThreadComment(CamelModel):
    """A single comment within an existing MR/PR discussion thread."""

    id: str = Field(description="Stable identifier for this comment.")
    author: Optional[str] = Field(default=None, description="Comment author, if known.")
    body: str = Field(description="The comment text. Must not be empty.")
    created_at: Optional[str] = Field(
        default=None, description="ISO-ish timestamp string, if known."
    )
    is_resolved: Optional[bool] = Field(
        default=None, description="Whether this specific comment is marked resolved."
    )

    @field_validator("body")
    @classmethod
    def _body_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("comment body must not be empty")
        return trimmed


class CommentThread(CamelModel):
    """An existing comment thread anchored (optionally) to a file/line."""

    id: str = Field(description="Stable identifier for the thread.")
    file_path: Optional[str] = Field(
        default=None, description="File the thread is anchored to, if any."
    )
    line: Optional[int] = Field(
        default=None, description="Line number the thread is anchored to, if any."
    )
    status: CommentThreadStatus = Field(default=CommentThreadStatus.UNKNOWN)
    comments: list[ThreadComment] = Field(
        description="Comments in the thread; at least one is required.",
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional origin hint, e.g. 'gitlab' or 'github'.",
    )

    @field_validator("comments")
    @classmethod
    def _at_least_one_comment(
        cls, value: list[ThreadComment]
    ) -> list[ThreadComment]:
        if not value:
            raise ValueError("a comment thread must contain at least one comment")
        return value


class SuggestedReply(CamelModel):
    """A drafted, copy-only reply to an existing comment thread.

    Reserved in Phase 14 (the API returns an empty list); generated locally and
    deterministically in Phase 15. Always framed as a human-reviewed draft.
    """

    id: str = Field(description="Stable identifier for this suggested reply.")
    thread_id: str = Field(description="The CommentThread.id this reply responds to.")
    reviewer: ReviewerPersona = Field(description="Persona voice the reply uses.")
    suggested_reply: str = Field(description="The drafted reply text.")
    rationale: str = Field(description="Why this reply was suggested.")
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in the suggestion, 0.0-1.0.",
    )
    needs_human_review: bool = Field(
        default=True,
        description="Always true for now: replies are drafts for a human to send.",
    )
    tone_profile: Optional[ToneProfile] = Field(
        default=None, description="Tone used to frame the reply, if any."
    )
