"""Tests for the mock review engine."""

from app.models.enums import (
    FindingSeverity,
    MergeRecommendation,
    ReviewerPersona,
    RiskLevel,
)
from app.models.review import ReviewRequest
from app.services.review_engine import run_review

SECURITY_DIFF = """\
diff --git a/app/config.py b/app/config.py
--- a/app/config.py
+++ b/app/config.py
@@ -1,1 +1,3 @@
 import os
+API_TOKEN = "abc123"
+result = eval(user_input)
"""

# Backend production code change, no test files touched.
PROD_NO_TESTS_DIFF = """\
diff --git a/app/service.py b/app/service.py
--- a/app/service.py
+++ b/app/service.py
@@ -1,2 +1,3 @@
 def run():
-    return 1
+    return compute()
+    return None
"""

HIGH_RISK_DIFF = """\
diff --git a/app/secrets.py b/app/secrets.py
--- a/app/secrets.py
+++ b/app/secrets.py
@@ -1,1 +1,2 @@
 import os
+private_key = "xxx"
"""

LOW_RISK_DIFF = """\
diff --git a/app/util.py b/app/util.py
--- a/app/util.py
+++ b/app/util.py
@@ -1,1 +1,2 @@
 import os
+# TODO: clean this up later
"""


def _request(diff: str, personas: list[ReviewerPersona]) -> ReviewRequest:
    return ReviewRequest(diff_text=diff, selected_personas=personas)


def test_only_selected_personas_run():
    resp = run_review(
        _request(SECURITY_DIFF, [ReviewerPersona.SECURITY, ReviewerPersona.QA])
    )
    personas = [pr.persona for pr in resp.persona_reviews]
    assert personas == [ReviewerPersona.SECURITY, ReviewerPersona.QA]
    # No other personas leak into the output.
    assert ReviewerPersona.ARCHITECT not in personas


def test_security_flags_suspicious_changes():
    resp = run_review(_request(SECURITY_DIFF, [ReviewerPersona.SECURITY]))
    sec_findings = [f for f in resp.findings if f.reviewer == ReviewerPersona.SECURITY]
    assert sec_findings, "expected security findings"
    titles = " ".join(f.title.lower() for f in sec_findings)
    assert "token" in titles
    assert "eval" in titles
    # eval() is treated as high severity.
    assert any(f.severity == FindingSeverity.HIGH for f in sec_findings)
    # Findings carry file path and hunk reference.
    assert all(f.file_path == "app/config.py" for f in sec_findings)
    assert all(f.hunk_reference is not None for f in sec_findings)


def test_qa_flags_production_change_without_tests():
    resp = run_review(_request(PROD_NO_TESTS_DIFF, [ReviewerPersona.QA]))
    qa_findings = [f for f in resp.findings if f.reviewer == ReviewerPersona.QA]
    assert any("without test" in f.title.lower() for f in qa_findings)


def test_overall_risk_increases_with_severity():
    high = run_review(_request(HIGH_RISK_DIFF, [ReviewerPersona.SECURITY]))
    low = run_review(_request(LOW_RISK_DIFF, [ReviewerPersona.BACKEND]))
    assert high.overall_risk == RiskLevel.HIGH
    assert low.overall_risk == RiskLevel.LOW
    # A security-sensitive high finding requires human review.
    assert high.merge_recommendation == MergeRecommendation.NEEDS_HUMAN_REVIEW
    assert low.merge_recommendation == MergeRecommendation.READY_WITH_FOLLOWUPS


def test_flattened_findings_match_persona_findings():
    resp = run_review(_request(SECURITY_DIFF, [ReviewerPersona.SECURITY]))
    grouped = [f.id for pr in resp.persona_reviews for f in pr.findings]
    flattened = [f.id for f in resp.findings]
    assert sorted(grouped) == sorted(flattened)


def test_empty_diff_is_graceful():
    resp = run_review(_request("", [ReviewerPersona.SECURITY, ReviewerPersona.QA]))
    assert resp.findings == []
    assert resp.overall_risk == RiskLevel.LOW
    assert resp.merge_recommendation == MergeRecommendation.READY
    assert resp.diff_stats.files_changed == 0


def test_deterministic_output():
    a = run_review(_request(SECURITY_DIFF, [ReviewerPersona.SECURITY]))
    b = run_review(_request(SECURITY_DIFF, [ReviewerPersona.SECURITY]))
    assert a.model_dump() == b.model_dump()
