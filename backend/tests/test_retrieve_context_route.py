"""Tests for the local-only `POST /api/retrieve-context` route (v0.4, Phase 4).

The route runs the local retrieval service over the project's own allow-listed docs
(`README.md` + `docs/`), pinned server-side. It performs no network I/O, accepts no
tokens, and is not connected to review generation.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.retrieve_context import RetrieveContextResponse

client = TestClient(app)


# 1. Success response with camelCase fields.
def test_success_camel_case():
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "review merge request diff", "topK": 5},
            "sourcePaths": ["README.md"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert "warnings" in body
    assert body["results"], "expected at least one lexical match in README"
    first = body["results"][0]
    assert "chunkId" in first
    assert "sourcePath" in first
    assert "startLine" in first
    # snake_case must not leak.
    assert "chunk_id" not in first
    assert "source_path" not in first


# 2. Outside-root request returns 400.
def test_outside_root_returns_400():
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "anything"},
            "sourcePaths": ["backend/app/main.py"],
        },
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


# 3. URL-like source path returns 400.
def test_url_like_source_returns_400():
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "anything"},
            "sourcePaths": ["https://example.com/docs/x.md"],
        },
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


# 4a. Empty/low-signal query returns empty results.
def test_low_signal_query_returns_empty_results():
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "   "},
            "sourcePaths": ["README.md"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["results"] == []


# 4b. No sourcePaths returns empty results with a warning.
def test_no_source_paths_returns_warning():
    resp = client.post(
        "/api/retrieve-context",
        json={"query": {"query": "review"}, "sourcePaths": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
    assert body["warnings"]


# 5. No token field is required or exposed by the contract.
def test_no_token_field_required_or_exposed():
    schema = app.openapi()
    request_schema = schema["components"]["schemas"]["RetrieveContextRequest"]
    assert "token" not in request_schema.get("properties", {})

    # A stray token field is simply ignored.
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "review"},
            "sourcePaths": ["README.md"],
            "token": "should-be-ignored",
        },
    )
    assert resp.status_code == 200


# 6. Route response validates against RetrieveContextResponse.
def test_response_validates_against_model():
    resp = client.post(
        "/api/retrieve-context",
        json={
            "query": {"query": "review merge request", "topK": 3},
            "sourcePaths": ["README.md"],
        },
    )
    assert resp.status_code == 200
    model = RetrieveContextResponse.model_validate(resp.json())
    assert len(model.results) <= 3
