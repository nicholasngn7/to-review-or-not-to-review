"""Tests for the local-only `POST /api/import-comments` route (v0.3, Phase 6).

The route normalizes a caller-supplied, fixture-shaped payload via the pure
orchestrator. It performs no network I/O and accepts no tokens.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.git_import import ImportCommentsResponse

client = TestClient(app)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return json.load(handle)


# 1. GitHub review comments -> normalized threads.
def test_github_review_comments_returns_threads():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "github",
            "source": "github_review_comments",
            "rawPayload": _load("github_pr_review_comments.json"),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "github"
    ids = [t["externalReference"]["commentId"] for t in body["threads"]]
    assert ids == ["1001", "1003", "1004", "1007"]
    # Root thread reconstructed with its reply.
    root = next(t for t in body["threads"] if t["externalReference"]["commentId"] == "1001")
    assert len(root["thread"]["comments"]) == 2


# 2. GitHub issue comments -> line-less single-comment threads.
def test_github_issue_comments_returns_line_less_threads():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "github",
            "source": "github_issue_comments",
            "rawPayload": _load("github_pr_issue_comments.json"),
        },
    )
    assert resp.status_code == 200
    threads = resp.json()["threads"]
    assert threads
    for imported in threads:
        assert imported["thread"]["filePath"] is None
        assert imported["thread"]["line"] is None
        assert len(imported["thread"]["comments"]) == 1


# 3. GitLab discussions -> normalized threads.
def test_gitlab_discussions_returns_threads():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "gitlab",
            "source": "gitlab_discussions",
            "rawPayload": _load("gitlab_mr_discussions.json"),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    ids = [t["externalReference"]["discussionId"] for t in body["threads"]]
    assert ids == ["disc-1", "disc-2", "disc-4", "disc-5", "disc-6", "disc-8"]


# 4. Empty payload -> 200 with empty threads and a warning.
def test_empty_payload_returns_empty_with_warning():
    resp = client.post("/api/import-comments", json={"provider": "github"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["threads"] == []
    assert body["warnings"]
    assert any("empty" in w.lower() for w in body["warnings"])


# 5. Ambiguous GitHub request without source -> 400.
def test_ambiguous_github_without_source_returns_400():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "github",
            "rawPayload": _load("github_pr_review_comments.json"),
        },
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


# 6. Unsupported provider/source combination -> 400.
def test_unsupported_provider_source_returns_400():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "gitlab",
            "source": "github_review_comments",
            "rawPayload": _load("github_pr_review_comments.json"),
        },
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


# 7. Response uses camelCase fields throughout.
def test_response_is_camel_case():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "github",
            "source": "github_review_comments",
            "rawPayload": _load("github_pr_review_comments.json"),
        },
    )
    body = resp.json()
    root = next(t for t in body["threads"] if t["externalReference"]["commentId"] == "1001")
    ref = root["externalReference"]
    assert "externalReference" in root
    assert "pullRequestNumber" in ref
    assert "reviewId" in ref
    assert "isOutdated" in ref
    # snake_case must not leak.
    assert "external_reference" not in root
    assert "pull_request_number" not in ref

    gl = client.post(
        "/api/import-comments",
        json={
            "provider": "gitlab",
            "source": "gitlab_discussions",
            "rawPayload": _load("gitlab_mr_discussions.json"),
        },
    ).json()
    gl_ref = gl["threads"][0]["externalReference"]
    assert "mergeRequestIid" in gl_ref
    assert "projectId" in gl_ref
    assert "discussionId" in gl_ref


# 8. The endpoint exposes no token handling.
def test_no_token_field_required_or_accepted():
    schema = app.openapi()
    request_schema = schema["components"]["schemas"]["ImportCommentsRequest"]
    assert "token" not in request_schema.get("properties", {})

    # A stray token field is simply ignored (extra input not part of the contract).
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "github",
            "source": "github_review_comments",
            "token": "should-be-ignored",
            "rawPayload": _load("github_pr_review_comments.json"),
        },
    )
    assert resp.status_code == 200


# 9. Response validates against ImportCommentsResponse.
def test_response_validates_against_model():
    resp = client.post(
        "/api/import-comments",
        json={
            "provider": "gitlab",
            "source": "gitlab_discussions",
            "rawPayload": _load("gitlab_mr_discussions.json"),
        },
    )
    assert resp.status_code == 200
    model = ImportCommentsResponse.model_validate(resp.json())
    assert model.threads
    assert all(t.thread.comments for t in model.threads)
