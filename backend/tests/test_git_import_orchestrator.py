"""Tests for the pure import orchestrator + import/local invariance (v0.3, Phase 5).

Fixture-only and network-free. The orchestrator dispatches an `ImportCommentsRequest`
to the right mapper; the invariance tests prove that, once normalized into
`CommentThread`s, imported threads drive `run_review` identically to local threads.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from app.models.comments import CommentThread, CommentThreadStatus, ThreadComment
from app.models.enums import ReviewerPersona
from app.models.git_import import (
    GitProviderType,
    ImportCommentsRequest,
    ImportCommentsResponse,
)
from app.models.review import ReviewRequest
from app.services.git_import import (
    SOURCE_GITHUB_ISSUE_COMMENTS,
    SOURCE_GITHUB_REVIEW_COMMENTS,
    SOURCE_GITLAB_DISCUSSIONS,
    import_comments,
    map_github_review_comments_to_threads,
)
from app.services.review_engine import run_review

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[dict]:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _request(provider: GitProviderType, payload, source=None) -> ImportCommentsRequest:
    return ImportCommentsRequest(provider=provider, source=source, raw_payload=payload)


# 1. Empty/None payload returns empty response with a warning.
def test_empty_payload_returns_warning():
    for payload in (None, [], {}):
        resp = import_comments(_request(GitProviderType.GITHUB, payload))
        assert resp.threads == []
        assert resp.warnings
        assert any("empty" in w.lower() for w in resp.warnings)


# 2. GitHub review-comments source dispatches to the review-comment mapper.
def test_dispatch_github_review_comments():
    payload = _load("github_pr_review_comments.json")
    resp = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
    )
    expected = map_github_review_comments_to_threads(payload)
    assert [t.thread.id for t in resp.threads] == [t.thread.id for t in expected]
    # Review comments reconstruct a multi-comment root thread (1001 + reply 1002).
    root = next(t for t in resp.threads if t.external_reference.comment_id == "1001")
    assert len(root.thread.comments) == 2


# 3. GitHub issue-comments source dispatches to the issue-comment mapper.
def test_dispatch_github_issue_comments():
    payload = _load("github_pr_issue_comments.json")
    resp = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_ISSUE_COMMENTS)
    )
    # Issue comments are line-less single-comment threads.
    assert resp.threads
    for imported in resp.threads:
        assert imported.thread.file_path is None
        assert imported.thread.line is None
        assert len(imported.thread.comments) == 1


# 4. GitLab discussions source dispatches to the GitLab mapper.
def test_dispatch_gitlab_discussions():
    payload = _load("gitlab_mr_discussions.json")
    resp = import_comments(
        _request(GitProviderType.GITLAB, payload, SOURCE_GITLAB_DISCUSSIONS)
    )
    ids = [t.external_reference.discussion_id for t in resp.threads]
    assert ids == ["disc-1", "disc-2", "disc-4", "disc-5", "disc-6", "disc-8"]


# 5. Unsupported provider/source combinations fail clearly.
def test_unsupported_combinations_raise():
    payload = _load("github_pr_review_comments.json")
    # Source valid but for the wrong provider.
    with pytest.raises(ValueError):
        import_comments(
            _request(GitProviderType.GITLAB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
        )
    # Unknown source string.
    with pytest.raises(ValueError):
        import_comments(_request(GitProviderType.GITHUB, payload, "not_a_source"))


# 6. Missing source with an ambiguous GitHub payload fails rather than guessing.
def test_missing_source_github_is_ambiguous():
    payload = _load("github_pr_review_comments.json")
    with pytest.raises(ValueError):
        import_comments(_request(GitProviderType.GITHUB, payload))

    # GitLab has a single mapper, so omitting source is unambiguous and works.
    gl = _load("gitlab_mr_discussions.json")
    resp = import_comments(_request(GitProviderType.GITLAB, gl))
    assert resp.threads


# 7. Thread-level warnings are surfaced at the top level (and kept intact).
def test_thread_warnings_surfaced():
    payload = _load("github_pr_review_comments.json")
    resp = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
    )
    # Comment 1007 replies to a missing root -> a per-thread warning.
    orphan = next(t for t in resp.threads if t.external_reference.comment_id == "1007")
    assert any("missing root" in w for w in orphan.warnings)
    assert any("missing root" in w for w in resp.warnings)


# 8. Output conforms to ImportCommentsResponse.
def test_output_conforms_to_response_model():
    payload = _load("gitlab_mr_discussions.json")
    resp = import_comments(
        _request(GitProviderType.GITLAB, payload, SOURCE_GITLAB_DISCUSSIONS)
    )
    assert isinstance(resp, ImportCommentsResponse)
    assert resp.provider is GitProviderType.GITLAB
    ImportCommentsResponse.model_validate(resp.model_dump())


# 9. Deterministic output across repeated calls.
def test_deterministic_output():
    payload = _load("github_pr_review_comments.json")
    first = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
    )
    second = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
    )
    assert first.model_dump() == second.model_dump()


# 10. No network/token/endpoint surface.
def test_no_network_or_token_surface():
    params = set(inspect.signature(import_comments).parameters)
    assert params == {"request"}
    assert "token" not in ImportCommentsRequest.model_fields


# --- Invariance: imported threads behave exactly like local threads. ---

DIFF = (
    "diff --git a/app/auth.py b/app/auth.py\n"
    "--- a/app/auth.py\n"
    "+++ b/app/auth.py\n"
    "@@ -1,2 +1,4 @@\n"
    " import os\n"
    "+try:\n"
    "+    do_login()\n"
    "+except Exception:\n"
    "+    pass\n"
)


def test_github_imported_threads_match_local_threads():
    payload = [
        {
            "id": 5001,
            "user": {"login": "rev"},
            "body": "Can we avoid swallowing this exception and add logging?",
            "created_at": "2026-04-01T00:00:00Z",
            "path": "app/auth.py",
            "line": 5,
        }
    ]
    imported = import_comments(
        _request(GitProviderType.GITHUB, payload, SOURCE_GITHUB_REVIEW_COMMENTS)
    )
    imported_threads = [it.thread for it in imported.threads]

    # An independently hand-authored local thread with identical content.
    local_threads = [
        CommentThread(
            id="github:rc:5001",
            file_path="app/auth.py",
            line=5,
            status=CommentThreadStatus.UNKNOWN,
            comments=[
                ThreadComment(
                    id="5001",
                    author="rev",
                    body="Can we avoid swallowing this exception and add logging?",
                    created_at="2026-04-01T00:00:00Z",
                )
            ],
            source="github",
        )
    ]

    personas = [ReviewerPersona.BACKEND, ReviewerPersona.SRE]
    from_import = run_review(
        ReviewRequest(
            diff_text=DIFF, selected_personas=personas, comment_threads=imported_threads
        )
    )
    from_local = run_review(
        ReviewRequest(
            diff_text=DIFF, selected_personas=personas, comment_threads=local_threads
        )
    )

    assert from_import.model_dump() == from_local.model_dump()
    assert from_import.suggested_replies  # replies were actually generated
    assert all(r.needs_human_review for r in from_import.suggested_replies)


def test_gitlab_imported_threads_match_local_threads():
    payload = [
        {
            "id": "d-inv",
            "notes": [
                {
                    "id": 91,
                    "system": False,
                    "author": {"username": "rev"},
                    "body": "Please add a test for token validation.",
                    "created_at": "2026-04-02T00:00:00Z",
                    "position": {"new_path": "app/auth.py", "new_line": 5},
                }
            ],
        }
    ]
    imported = import_comments(
        _request(GitProviderType.GITLAB, payload, SOURCE_GITLAB_DISCUSSIONS)
    )
    imported_threads = [it.thread for it in imported.threads]

    local_threads = [
        CommentThread(
            id="gitlab:disc:d-inv",
            file_path="app/auth.py",
            line=5,
            status=CommentThreadStatus.UNKNOWN,
            comments=[
                ThreadComment(
                    id="91",
                    author="rev",
                    body="Please add a test for token validation.",
                    created_at="2026-04-02T00:00:00Z",
                )
            ],
            source="gitlab",
        )
    ]

    personas = [ReviewerPersona.QA, ReviewerPersona.SECURITY]
    from_import = run_review(
        ReviewRequest(
            diff_text=DIFF, selected_personas=personas, comment_threads=imported_threads
        )
    )
    from_local = run_review(
        ReviewRequest(
            diff_text=DIFF, selected_personas=personas, comment_threads=local_threads
        )
    )

    assert from_import.model_dump() == from_local.model_dump()
    assert from_import.suggested_replies
    assert all(r.needs_human_review for r in from_import.suggested_replies)
