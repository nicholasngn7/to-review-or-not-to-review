"""Pure import orchestrator (v0.3, Phase 5).

Dispatches an `ImportCommentsRequest` to the correct per-provider mapper and returns
an `ImportCommentsResponse`. Strictly:

* no network calls, no HTTP clients, no tokens,
* no endpoints (this is a plain function),
* deterministic: same request in -> same response out.

The orchestrator never silently guesses a mapper. A `source` selects the mapper
explicitly; when `source` is omitted it is inferred *only* when unambiguous (GitLab
has a single mapper). Anything unsupported or ambiguous raises a clear `ValueError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from app.models.git_import import (
    GitProviderType,
    ImportCommentsRequest,
    ImportCommentsResponse,
    ImportedCommentThread,
)

from .github import (
    map_github_issue_comments_to_threads,
    map_github_review_comments_to_threads,
)
from .gitlab import map_gitlab_discussions_to_threads

# Stable, documented source identifiers.
SOURCE_GITHUB_REVIEW_COMMENTS = "github_review_comments"
SOURCE_GITHUB_ISSUE_COMMENTS = "github_issue_comments"
SOURCE_GITLAB_DISCUSSIONS = "gitlab_discussions"


@dataclass(frozen=True)
class _SourceSpec:
    provider: GitProviderType
    mapper: Callable[..., list[ImportedCommentThread]]
    # Keys under which a dict payload may nest the list of items.
    list_keys: tuple[str, ...]
    # mapper-kwarg -> candidate payload keys (only used for dict payloads).
    meta: dict[str, tuple[str, ...]]


_SOURCES: dict[str, _SourceSpec] = {
    SOURCE_GITHUB_REVIEW_COMMENTS: _SourceSpec(
        provider=GitProviderType.GITHUB,
        mapper=map_github_review_comments_to_threads,
        list_keys=("comments", "review_comments", "reviewComments"),
        meta={
            "repository": ("repository", "repo"),
            "pull_request_number": ("pull_request_number", "pullRequestNumber"),
        },
    ),
    SOURCE_GITHUB_ISSUE_COMMENTS: _SourceSpec(
        provider=GitProviderType.GITHUB,
        mapper=map_github_issue_comments_to_threads,
        list_keys=("comments", "issue_comments", "issueComments"),
        meta={
            "repository": ("repository", "repo"),
            "pull_request_number": ("pull_request_number", "pullRequestNumber"),
        },
    ),
    SOURCE_GITLAB_DISCUSSIONS: _SourceSpec(
        provider=GitProviderType.GITLAB,
        mapper=map_gitlab_discussions_to_threads,
        list_keys=("discussions",),
        meta={
            "project_id": ("project_id", "projectId"),
            "merge_request_iid": ("merge_request_iid", "mergeRequestIid"),
        },
    ),
}

# Mappers available per provider when `source` is omitted.
_PROVIDER_SOURCES: dict[GitProviderType, list[str]] = {
    GitProviderType.GITHUB: [
        SOURCE_GITHUB_REVIEW_COMMENTS,
        SOURCE_GITHUB_ISSUE_COMMENTS,
    ],
    GitProviderType.GITLAB: [SOURCE_GITLAB_DISCUSSIONS],
}


def _resolve_source(request: ImportCommentsRequest) -> str:
    """Pick the source id for this request, or raise a clear ValueError."""
    source = (request.source or "").strip()
    if source:
        spec = _SOURCES.get(source)
        if spec is None:
            raise ValueError(
                f"Unsupported import source '{source}'. "
                f"Expected one of: {', '.join(sorted(_SOURCES))}."
            )
        if spec.provider is not request.provider:
            raise ValueError(
                f"Source '{source}' is not valid for provider "
                f"'{request.provider.value}'."
            )
        return source

    # No source: infer only when the provider has exactly one mapper.
    candidates = _PROVIDER_SOURCES.get(request.provider, [])
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(
        f"Provider '{request.provider.value}' has multiple import sources "
        f"({', '.join(candidates)}); specify `source` explicitly rather than guessing."
    )


def _extract_items(
    payload: object, spec: _SourceSpec
) -> tuple[Optional[list], list[str]]:
    """Return (items, warnings). items is None when no list could be located."""
    if isinstance(payload, list):
        return payload, []
    if isinstance(payload, dict):
        for key in spec.list_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value, []
        # Fall back to the first list-valued entry, if any.
        for value in payload.values():
            if isinstance(value, list):
                return value, []
        return None, [
            "rawPayload was an object with no recognizable list of items; "
            "nothing imported."
        ]
    return None, ["rawPayload had an unexpected shape; nothing imported."]


def _extract_meta(payload: object, spec: _SourceSpec) -> dict:
    if not isinstance(payload, dict):
        return {}
    meta: dict = {}
    for kwarg, keys in spec.meta.items():
        for key in keys:
            value = payload.get(key)
            if value is not None:
                meta[kwarg] = value
                break
    return meta


def import_comments(request: ImportCommentsRequest) -> ImportCommentsResponse:
    """Normalize an import request into `ImportedCommentThread`s. Pure, no network."""
    if not request.raw_payload:
        return ImportCommentsResponse(
            provider=request.provider,
            threads=[],
            warnings=["rawPayload was empty; no comment threads were imported."],
        )

    source = _resolve_source(request)
    spec = _SOURCES[source]

    items, warnings = _extract_items(request.raw_payload, spec)
    if items is None:
        return ImportCommentsResponse(
            provider=request.provider, threads=[], warnings=warnings
        )

    meta = _extract_meta(request.raw_payload, spec)
    threads = spec.mapper(items, **meta)

    # Surface per-thread warnings at the top level while leaving them intact.
    aggregated = list(warnings)
    for thread in threads:
        aggregated.extend(thread.warnings)

    return ImportCommentsResponse(
        provider=request.provider, threads=threads, warnings=aggregated
    )
