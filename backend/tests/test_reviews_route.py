"""Tests for the POST /api/reviews route."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_DIFF = (
    "diff --git a/app/config.py b/app/config.py\n"
    "--- a/app/config.py\n"
    "+++ b/app/config.py\n"
    "@@ -1,1 +1,2 @@\n"
    " import os\n"
    '+API_TOKEN = "abc123"\n'
)


def test_reviews_returns_camelcase_response():
    resp = client.post(
        "/api/reviews",
        json={"diffText": SAMPLE_DIFF, "selectedPersonas": ["security"]},
    )
    assert resp.status_code == 200
    body = resp.json()

    for key in (
        "overallRisk",
        "mergeRecommendation",
        "summary",
        "diffStats",
        "personaReviews",
        "findings",
    ):
        assert key in body, f"missing key {key}"

    assert body["diffStats"]["filesChanged"] == 1
    assert body["personaReviews"][0]["persona"] == "security"
    assert body["findings"], "expected at least one finding"
    finding = body["findings"][0]
    assert finding["reviewer"] == "security"
    assert "hunkReference" in finding


def test_reviews_empty_diff_is_ok():
    resp = client.post(
        "/api/reviews",
        json={"diffText": "", "selectedPersonas": ["security"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["findings"] == []
    assert body["overallRisk"] == "low"
    assert body["mergeRecommendation"] == "ready"


def test_reviews_non_diff_text_is_graceful():
    resp = client.post(
        "/api/reviews",
        json={"diffText": "just some prose, not a diff", "selectedPersonas": ["qa"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["diffStats"]["filesChanged"] == 0


def test_reviews_missing_diff_text_is_validation_error():
    resp = client.post("/api/reviews", json={"selectedPersonas": ["security"]})
    assert resp.status_code == 422


def test_reviews_invalid_persona_is_validation_error():
    resp = client.post(
        "/api/reviews",
        json={"diffText": SAMPLE_DIFF, "selectedPersonas": ["wizard"]},
    )
    assert resp.status_code == 422
