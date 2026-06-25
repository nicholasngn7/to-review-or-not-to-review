"""Tests for the review provider interface, factory, and configuration."""

import pytest

from app.core.config import DEFAULT_REVIEW_PROVIDER, get_settings
from app.models.enums import ReviewerPersona
from app.models.review import ReviewRequest
from app.services.providers import (
    BedrockReviewProvider,
    MockReviewProvider,
    available_providers,
    create_provider,
)
from app.services.review_engine import run_review

RISKY_DIFF = """\
diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,1 +1,4 @@
 import os
+API_TOKEN = "sk_live_secret"
+result = eval(payload)
+subprocess.run(cmd, shell=True)
"""


def _request(diff: str, personas: list[ReviewerPersona]) -> ReviewRequest:
    return ReviewRequest(diff_text=diff, selected_personas=personas)


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.delenv("REVIEW_PROVIDER", raising=False)
    assert get_settings().review_provider == DEFAULT_REVIEW_PROVIDER == "mock"
    provider = create_provider()
    assert isinstance(provider, MockReviewProvider)
    assert provider.name == "mock"


def test_explicit_mock_provider(monkeypatch):
    monkeypatch.setenv("REVIEW_PROVIDER", "mock")
    assert isinstance(create_provider(), MockReviewProvider)


def test_provider_selection_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("REVIEW_PROVIDER", "  MOCK ")
    assert get_settings().review_provider == "mock"
    assert isinstance(create_provider(), MockReviewProvider)


def test_unknown_provider_fails_clearly(monkeypatch):
    monkeypatch.setenv("REVIEW_PROVIDER", "definitely-not-real")
    with pytest.raises(ValueError) as exc:
        create_provider()
    message = str(exc.value)
    assert "definitely-not-real" in message
    # Lists the valid options.
    for name in available_providers():
        assert name in message


def test_bedrock_provider_does_not_silently_succeed():
    provider = create_provider("bedrock")
    assert isinstance(provider, BedrockReviewProvider)
    with pytest.raises(NotImplementedError) as exc:
        provider.review(
            parse_empty(), [ReviewerPersona.SECURITY], title=None, description=None
        )
    assert "not implemented" in str(exc.value).lower()


def test_bedrock_selected_via_engine_raises(monkeypatch):
    monkeypatch.setenv("REVIEW_PROVIDER", "bedrock")
    with pytest.raises(NotImplementedError):
        run_review(_request(RISKY_DIFF, [ReviewerPersona.SECURITY]))


def test_mock_provider_returns_findings_for_risky_diff():
    resp = run_review(
        _request(
            RISKY_DIFF,
            [ReviewerPersona.SECURITY, ReviewerPersona.QA, ReviewerPersona.BACKEND],
        )
    )
    assert resp.findings, "expected the mock provider to produce findings"
    reviewers = {f.reviewer for f in resp.findings}
    assert ReviewerPersona.SECURITY in reviewers


def test_injected_provider_is_used():
    # Passing a provider explicitly bypasses configuration entirely.
    resp = run_review(
        _request(RISKY_DIFF, [ReviewerPersona.SECURITY]),
        provider=MockReviewProvider(),
    )
    assert resp.findings


def parse_empty():
    """Tiny helper: a parsed empty diff for provider-level unit calls."""
    from app.services.diff_parser import parse_diff

    return parse_diff("")
