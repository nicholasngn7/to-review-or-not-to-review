"""Tests for the pure GitHub PR review-comment mapper (v0.3, Phase 2).

Fixture-only and network-free: the mapper consumes already-parsed dicts. These tests
pin down thread reconstruction, file/line mapping, provenance, filtering, and
determinism against a synthetic fixture.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from app.models.git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportedCommentThread,
)
from app.models.comments import CommentThread, CommentThreadStatus
from app.services.git_import import map_github_review_comments_to_threads

FIXTURE = Path(__file__).parent / "fixtures" / "github_pr_review_comments.json"

REPO = "acme/widgets"
PR = 7


def _load() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _map(**kwargs) -> list[ImportedCommentThread]:
    return map_github_review_comments_to_threads(
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


# 2. Root + reply chain reconstruct into one thread with multiple comments.
def test_root_and_reply_reconstruct_into_one_thread():
    threads = _map()
    root = _by_comment_id(threads, "1001")
    assert root is not None
    assert len(root.thread.comments) == 2
    bodies = [c.body for c in root.thread.comments]
    assert bodies[0].startswith("Can we avoid swallowing")
    assert bodies[1].startswith("Agreed")
    # Authors and timestamps are carried through.
    assert root.thread.comments[0].author == "reviewer-alpha"
    assert root.thread.comments[1].author == "reviewer-beta"
    assert root.thread.comments[0].created_at == "2026-01-02T10:00:00Z"


# 3. File path and line map correctly.
def test_file_path_and_line_map():
    threads = _map()
    root = _by_comment_id(threads, "1001")
    assert root.thread.file_path == "service/auth.py"
    assert root.thread.line == 42

    # A line-less review comment yields a line-less thread.
    note = _by_comment_id(threads, "1003")
    assert note is not None
    assert note.thread.file_path is None
    assert note.thread.line is None


# 4. ExternalCommentReference preserves GitHub provenance.
def test_external_reference_preserves_provenance():
    threads = _map()
    root = _by_comment_id(threads, "1001")
    ref = root.external_reference
    assert ref.provider is GitProviderType.GITHUB
    assert ref.repository == REPO
    assert ref.pull_request_number == PR
    assert ref.review_id == "555"
    assert ref.comment_id == "1001"
    assert ref.web_url.endswith("#discussion_r1001")
    # source hint set on the thread itself.
    assert root.thread.source == "github"


# 5. Empty/whitespace body comments are dropped.
def test_empty_body_comment_dropped():
    threads = _map()
    assert _by_comment_id(threads, "1006") is None
    # Default mapping yields exactly: 1001, 1003, 1004, 1007.
    ids = [t.external_reference.comment_id for t in threads]
    assert ids == ["1001", "1003", "1004", "1007"]


# 6. Outdated comments are skipped by default (include_outdated=False).
def test_outdated_skipped_by_default():
    threads = _map()
    assert _by_comment_id(threads, "1005") is None


# 7. Outdated comments can be included with a warning when include_outdated=True.
def test_outdated_included_with_warning():
    threads = _map(include_outdated=True)
    outdated = _by_comment_id(threads, "1005")
    assert outdated is not None
    assert outdated.thread.line is None  # stale anchor -> line dropped
    assert outdated.external_reference.is_outdated is True
    assert any("outdated" in w for w in outdated.warnings)


# 8. Missing-root reply creates a thread and a warning.
def test_missing_root_reply_creates_thread_and_warning():
    threads = _map()
    orphan = _by_comment_id(threads, "1007")
    assert orphan is not None
    assert len(orphan.thread.comments) == 1
    assert any("missing root" in w for w in orphan.warnings)
    assert orphan.thread.line == 60


# 9. Synthetic thread ids are deterministic across repeated calls.
def test_synthetic_thread_ids_are_deterministic():
    first = [t.thread.id for t in _map()]
    second = [t.thread.id for t in _map()]
    assert first == second
    # Readable, stable format.
    root = _by_comment_id(_map(), "1001")
    assert root.thread.id == "github:acme/widgets:7:rc:1001"


# 10. Output conforms to ImportedCommentThread / CommentThread models.
def test_output_conforms_to_models():
    threads = _map(include_outdated=True)
    for imported in threads:
        assert isinstance(imported, ImportedCommentThread)
        assert isinstance(imported.thread, CommentThread)
        assert isinstance(imported.external_reference, ExternalCommentReference)
        # Round-trips through validation cleanly.
        ImportedCommentThread.model_validate(imported.model_dump())
        # Contract invariant: at least one comment, all non-empty.
        assert imported.thread.comments
        assert all(c.body.strip() for c in imported.thread.comments)


# 11. include_resolved=False filters resolved threads.
def test_include_resolved_filters_resolved_threads():
    resolved_default = _by_comment_id(_map(), "1004")
    assert resolved_default is not None
    assert resolved_default.thread.status is CommentThreadStatus.RESOLVED

    filtered = _by_comment_id(_map(include_resolved=False), "1004")
    assert filtered is None


# 12. Mapping requires no network, tokens, or endpoints.
def test_mapper_has_no_network_or_token_surface():
    params = set(inspect.signature(map_github_review_comments_to_threads).parameters)
    assert "token" not in params
    assert "url" not in params
    # An unanchored thread defaults to UNKNOWN status (no resolution info).
    assert _by_comment_id(_map(), "1001").thread.status is CommentThreadStatus.UNKNOWN
    # Empty input is handled without error.
    assert map_github_review_comments_to_threads([]) == []
