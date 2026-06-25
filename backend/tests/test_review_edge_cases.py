"""Edge-case tests for the review API and engine.

Covers request edge cases (empty diff, no personas, invalid persona), personas
that legitimately produce nothing, provider failures surfacing as useful errors,
and how duplicate security terms on a line are handled.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.diff import ParsedDiff
from app.models.enums import ReviewerPersona
from app.models.review import PersonaReview, ReviewRequest
from app.services.providers.base import ReviewProvider
from app.services.review_engine import run_review

client = TestClient(app)

# A clean diff that no persona heuristic should flag.
CLEAN_DIFF = (
    "diff --git a/notes.txt b/notes.txt\n"
    "--- a/notes.txt\n"
    "+++ b/notes.txt\n"
    "@@ -1,1 +1,2 @@\n"
    " hello\n"
    "+world\n"
)


def _request(diff: str, personas: list[ReviewerPersona]) -> ReviewRequest:
    return ReviewRequest(diff_text=diff, selected_personas=personas)


# ---- Request edge cases (HTTP) ---------------------------------------------


def test_empty_diff_text_is_ok():
    resp = client.post(
        "/api/reviews", json={"diffText": "", "selectedPersonas": ["security"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["findings"] == []
    assert body["overallRisk"] == "low"
    assert body["mergeRecommendation"] == "ready"
    assert body["diffStats"]["filesChanged"] == 0


def test_no_selected_personas_returns_empty_review():
    # selectedPersonas omitted -> defaults to empty list -> no reviewers run.
    resp = client.post("/api/reviews", json={"diffText": CLEAN_DIFF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["personaReviews"] == []
    assert body["findings"] == []
    assert body["overallRisk"] == "low"
    assert body["mergeRecommendation"] == "ready"


def test_invalid_persona_is_validation_error():
    resp = client.post(
        "/api/reviews",
        json={"diffText": CLEAN_DIFF, "selectedPersonas": ["wizard"]},
    )
    assert resp.status_code == 422


def test_selected_persona_with_no_findings():
    resp = client.post(
        "/api/reviews",
        json={"diffText": CLEAN_DIFF, "selectedPersonas": ["security"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    # The persona still runs and is reported, just with no findings.
    assert len(body["personaReviews"]) == 1
    assert body["personaReviews"][0]["persona"] == "security"
    assert body["personaReviews"][0]["findings"] == []
    assert body["personaReviews"][0]["riskLevel"] == "low"
    assert body["findings"] == []


# ---- Provider failures ------------------------------------------------------


def test_bedrock_provider_failure_returns_clear_501(monkeypatch):
    monkeypatch.setenv("REVIEW_PROVIDER", "bedrock")
    resp = client.post(
        "/api/reviews",
        json={"diffText": CLEAN_DIFF, "selectedPersonas": ["security"]},
    )
    assert resp.status_code == 501
    assert "not implemented" in resp.json()["detail"].lower()


def test_engine_does_not_swallow_provider_errors():
    class FailingProvider(ReviewProvider):
        name = "failing"

        def review(
            self,
            parsed_diff: ParsedDiff,
            selected_personas,
            title=None,
            description=None,
            tone_profiles=None,
        ) -> list[PersonaReview]:
            raise RuntimeError("provider exploded")

    with pytest.raises(RuntimeError, match="provider exploded"):
        run_review(
            _request(CLEAN_DIFF, [ReviewerPersona.SECURITY]),
            provider=FailingProvider(),
        )


# ---- Duplicate security terms ----------------------------------------------


def test_repeated_security_term_on_one_line_is_deduped():
    # The same term appearing multiple times on a single added line should yield
    # exactly one finding (deduped per term + file + line).
    diff = (
        "diff --git a/app/config.py b/app/config.py\n"
        "--- a/app/config.py\n"
        "+++ b/app/config.py\n"
        "@@ -1,1 +1,2 @@\n"
        " import os\n"
        '+token = get_token("token", default_token="token")\n'
    )
    resp = run_review(_request(diff, [ReviewerPersona.SECURITY]))
    sec = [f for f in resp.findings if f.reviewer == ReviewerPersona.SECURITY]
    token_findings = [f for f in sec if "token" in f.title.lower()]
    assert len(token_findings) == 1


def test_same_term_on_separate_lines_yields_separate_findings():
    # Documents the dedup boundary: dedup is per (term, file, line), so the same
    # term on two different lines is reported twice.
    diff = (
        "diff --git a/app/config.py b/app/config.py\n"
        "--- a/app/config.py\n"
        "+++ b/app/config.py\n"
        "@@ -1,1 +1,3 @@\n"
        " import os\n"
        '+token = "a"\n'
        '+token = "b"\n'
    )
    resp = run_review(_request(diff, [ReviewerPersona.SECURITY]))
    token_findings = [
        f
        for f in resp.findings
        if f.reviewer == ReviewerPersona.SECURITY and "token" in f.title.lower()
    ]
    assert len(token_findings) == 2
