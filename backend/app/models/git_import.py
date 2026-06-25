"""Contract models for future GitHub/GitLab comment import (v0.3, Phase 1).

These are **contracts only**. They define the shape that a future, fixture-based
mapping layer would produce when normalizing recorded provider comment JSON into the
existing `CommentThread` contract. As of this phase there are:

* no mapper functions,
* no fixtures,
* no live GitHub/GitLab API calls,
* no OAuth, no token input,
* no endpoints,
* no frontend/UI changes.

Provider-native identity is preserved in `ExternalCommentReference` so imported
threads stay traceable (and a future, separate posting design could round-trip)
without polluting the core `CommentThread` contract. See
`docs/v0.3-plan-git-comment-import-mappers.md` and
`docs/future-git-provider-comment-import.md`.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Union

from pydantic import Field

from .base import CamelModel
from .comments import CommentThread


class GitProviderType(str, Enum):
    """Supported source providers for (future) comment import."""

    GITHUB = "github"
    GITLAB = "gitlab"


class ExternalCommentReference(CamelModel):
    """Provider-native identity for an imported thread.

    Captures the source ids/links verbatim so imported threads are traceable and
    re-imports can be deduplicated, without adding provider-specific fields to the
    core `CommentThread`. Purely provenance: it never affects review behavior.
    """

    provider: GitProviderType = Field(description="Which provider the thread came from.")
    repository: Optional[str] = Field(
        default=None, description="GitHub repository, e.g. 'owner/repo'."
    )
    project_id: Optional[str] = Field(
        default=None, description="GitLab project path or numeric id."
    )
    pull_request_number: Optional[int] = Field(
        default=None, description="GitHub pull request number."
    )
    merge_request_iid: Optional[int] = Field(
        default=None, description="GitLab merge request iid."
    )
    discussion_id: Optional[str] = Field(
        default=None, description="GitLab discussion id (thread root)."
    )
    review_id: Optional[str] = Field(
        default=None, description="GitHub review id, when the comment is part of a review."
    )
    comment_id: Optional[str] = Field(
        default=None, description="Provider comment id (thread root) when applicable."
    )
    note_id: Optional[str] = Field(
        default=None, description="GitLab note id when applicable."
    )
    web_url: Optional[str] = Field(
        default=None, description="Human-openable link to the comment/thread."
    )
    is_outdated: Optional[bool] = Field(
        default=None,
        description="Whether the source comment is anchored to an outdated line, if known.",
    )


class ImportedCommentThread(CamelModel):
    """A normalized imported thread plus provider provenance.

    `thread` is the *existing* `CommentThread` consumed by the review/reply pipeline;
    `external_reference` is optional side-car metadata; `warnings` records non-fatal
    normalization notes (e.g. an outdated line that was dropped).
    """

    thread: CommentThread = Field(description="The normalized, contract-shaped thread.")
    external_reference: ExternalCommentReference = Field(
        description="Provider-native identity/links for this thread."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal notes produced while normalizing this thread.",
    )


class ImportCommentsRequest(CamelModel):
    """Future local import request contract.

    Deliberately carries **no token** and triggers **no** network access. A future
    phase would pass already-fetched provider JSON via `raw_payload`; the mapping
    layer (not yet built) turns that into `ImportedCommentThread`s.
    """

    provider: GitProviderType = Field(description="Which provider the payload is from.")
    source: Optional[str] = Field(
        default=None, description="Optional origin hint or label for the payload."
    )
    raw_payload: Optional[Union[dict[str, Any], list[Any]]] = Field(
        default=None,
        description="Already-fetched provider JSON to normalize. Not fetched by us.",
    )


class ImportCommentsResponse(CamelModel):
    """Result of a (future) import: normalized threads plus any warnings."""

    provider: GitProviderType = Field(description="Provider the threads were imported from.")
    threads: list[ImportedCommentThread] = Field(
        default_factory=list, description="Normalized imported threads."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Top-level, non-fatal notes about the import as a whole.",
    )
