"""Tests for the pure GitHub PR issue-comment mapper (v0.3, Phase 3).

Fixture-only and network-free. PR conversation (issue) comments are line-less and
unthreaded, so each non-empty comment becomes its own single-comment thread.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from app.models.comments import CommentThread, CommentThreadStatus
from app.models.git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportedCommentThread,
)
from app.services.git_import import map_github_issue_comments_to_threads

FIXTURE = Path(__file__).parent / "fixtures" / "github_pr_issue_comments.json"

REPO = "acme/widgets"
PR = 7


def _load() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _map(**kwargs) -> list[ImportedCommentThread]:
    return map_github_issue_comments_to_threads(
        _load(), repository=REPO, pull_request_number=PR, **kwargs
    )


def _by_comment_id(
    threads: list[ImportedCommentThread], comment_id: str
) -> ImportedCommentThread | None:
    for imported in threads:
        if imported.external_reference.comment_id == comment_id:
            return imported
    return None


# 1. Fixture loads successfully.
def test_fixture_loads():
    data = _load()
    assert isinstance(data, list)
    assert len(data) == 7


# 2. Each non-empty issue comment becomes one line-less single-comment thread.
def test_each_comment_becomes_single_comment_thread():
    threads = _map()
    # 2004 (whitespace) is dropped; the rest map 1:1 in input order.
    ids = [t.external_reference.comment_id for t in threads]
    assert ids == ["2001", "2002", "2003", "2005", "2006", "2007"]
    for imported in threads:
        assert len(imported.thread.comments) == 1


# 3. filePath and line are None for all mapped issue-comment threads.
def test_threads_are_line_less():
    for imported in _map():
        assert imported.thread.file_path is None
        assert imported.thread.line is None
        assert imported.thread.status is CommentThreadStatus.UNKNOWN
        assert imported.thread.source == "github"


# 4. Empty/whitespace body comments are dropped.
def test_whitespace_body_dropped():
    assert _by_comment_id(_map(), "2004") is None


# 5. Author and createdAt map when present (incl. camelCase keys).
def test_author_and_created_at_map():
    threads = _map()
    first = _by_comment_id(threads, "2001")
    assert first.thread.comments[0].author == "reviewer-alpha"
    assert first.thread.comments[0].created_at == "2026-02-01T09:00:00Z"

    # 2003 uses camelCase keys (createdAt / htmlUrl).
    camel = _by_comment_id(threads, "2003")
    assert camel.thread.comments[0].created_at == "2026-02-01T11:15:00Z"
    assert camel.external_reference.web_url.endswith("#issuecomment-2003")

    # 2007 falls back to user.name when login is also present (login wins here).
    delta = _by_comment_id(threads, "2007")
    assert delta.thread.comments[0].author == "reviewer-delta"


# 6. Missing author / createdAt are handled safely.
def test_missing_author_and_created_at_safe():
    threads = _map()
    no_author = _by_comment_id(threads, "2005")
    assert no_author.thread.comments[0].author is None
    assert no_author.thread.comments[0].created_at == "2026-02-01T12:30:00Z"

    no_date = _by_comment_id(threads, "2006")
    assert no_date.thread.comments[0].author == "reviewer-alpha"
    assert no_date.thread.comments[0].created_at is None
    assert no_date.external_reference.web_url is None


# 7. ExternalCommentReference preserves GitHub provenance.
def test_external_reference_provenance():
    ref = _by_comment_id(_map(), "2001").external_reference
    assert ref.provider is GitProviderType.GITHUB
    assert ref.repository == REPO
    assert ref.pull_request_number == PR
    assert ref.comment_id == "2001"
    assert ref.web_url.endswith("#issuecomment-2001")


# 8. Review/thread-only fields stay None for issue comments.
def test_review_related_fields_remain_none():
    for imported in _map():
        ref = imported.external_reference
        assert ref.review_id is None
        assert ref.discussion_id is None
        assert ref.note_id is None
        assert ref.is_outdated is None
        assert ref.merge_request_iid is None


# 9. Synthetic ids are deterministic across repeated calls.
def test_synthetic_ids_deterministic():
    first = [t.thread.id for t in _map()]
    second = [t.thread.id for t in _map()]
    assert first == second
    assert _by_comment_id(_map(), "2001").thread.id == "github:acme/widgets:7:ic:2001"


# 10. Output conforms to ImportedCommentThread / CommentThread models.
def test_output_conforms_to_models():
    for imported in _map():
        assert isinstance(imported, ImportedCommentThread)
        assert isinstance(imported.thread, CommentThread)
        assert isinstance(imported.external_reference, ExternalCommentReference)
        ImportedCommentThread.model_validate(imported.model_dump())
        assert imported.thread.comments
        assert all(c.body.strip() for c in imported.thread.comments)


# 11. Unknown/extra fields are ignored safely.
def test_unknown_fields_ignored():
    # 2007 carries reactions / author_association / performed_via_github_app.
    delta = _by_comment_id(_map(), "2007")
    assert delta is not None
    assert delta.thread.comments[0].body.startswith("Nit: rename")


# 12. Mapper requires no network, tokens, or endpoints.
def test_no_network_or_token_surface():
    params = set(inspect.signature(map_github_issue_comments_to_threads).parameters)
    assert "token" not in params
    assert "url" not in params
    assert map_github_issue_comments_to_threads([]) == []
