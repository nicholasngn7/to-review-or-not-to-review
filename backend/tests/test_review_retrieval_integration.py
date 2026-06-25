"""Tests for opt-in retrieval grounding in the review flow (v0.4, Phase 5).

Covers three things:

* **Invariance**: with retrieval off *and* on, detection/risk/recommendation/tone/
  suggested replies are unchanged — retrieval only adds provenance.
* **Opt-in behavior**: `contextUsed` and provenance-only `citations` are populated only
  when `knowledgeSources` are provided, and serialize as camelCase.
* **Error/no-op**: unsafe/outside/URL-like sources are rejected; no results -> normal
  review with empty context/citations; repeated runs are deterministic.

Retrieval is local, offline, deterministic, and lexical. No network/Bedrock/LLM.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import FindingSeverity, ReviewerPersona
from app.models.knowledge import RetrievalQuery, RetrievalResult
from app.models.review import ReviewFinding, ReviewRequest
from app.models.tone import ToneProfile
from app.services import review_engine
from app.services.knowledge import RetrievalError
from app.services.knowledge.review_context import (
    attach_citations,
    resolve_retrieval_query,
)
from app.services.review_engine import run_review

client = TestClient(app)

# Triggers a Security finding (token) and a Backend finding (@router. handler).
API_DIFF = """\
diff --git a/app/api/routes/users.py b/app/api/routes/users.py
--- a/app/api/routes/users.py
+++ b/app/api/routes/users.py
@@ -1,2 +1,4 @@
 import os
+API_TOKEN = "abc123"
+@router.get("/users")
+def list_users():
"""

_PERSONAS = [ReviewerPersona.SECURITY, ReviewerPersona.BACKEND]
# A query that strongly overlaps the project README so retrieval returns results.
_README_QUERY = RetrievalQuery(query="review merge request diff findings personas")


def _request(**kwargs) -> ReviewRequest:
    base = dict(diff_text=API_DIFF, selected_personas=_PERSONAS)
    base.update(kwargs)
    return ReviewRequest(**base)


def _findings_without_citations(resp) -> list[dict]:
    dumps = []
    for finding in resp.findings:
        data = finding.model_dump()
        data["citations"] = []
        dumps.append(data)
    return dumps


# ---------------------------------------------------------------------------
# No-retrieval invariance
# ---------------------------------------------------------------------------


# 1. A normal request without knowledge fields matches prior behavior (no context).
def test_no_knowledge_fields_no_context():
    resp = run_review(_request())
    assert resp.context_used == []
    assert all(f.citations == [] for f in resp.findings)
    assert resp.findings  # sanity: the diff does produce findings


# 2. Retrieval service is NOT called when knowledge fields are absent.
def test_retrieval_not_called_without_knowledge(monkeypatch):
    def _boom(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("retrieve_context must not be called without knowledge")

    monkeypatch.setattr(review_engine, "retrieve_context", _boom)
    resp = run_review(_request())
    assert resp.context_used == []


# ---------------------------------------------------------------------------
# Opt-in retrieval
# ---------------------------------------------------------------------------


# 3. A request with knowledgeSources/retrieval populates contextUsed.
def test_opt_in_populates_context_used():
    resp = run_review(_request(knowledge_sources=["README.md"], retrieval=_README_QUERY))
    assert resp.context_used
    assert all(isinstance(r, RetrievalResult) for r in resp.context_used)


# 4. Retrieved context serializes as camelCase contextUsed.
def test_context_used_camel_case():
    resp = run_review(_request(knowledge_sources=["README.md"], retrieval=_README_QUERY))
    payload = resp.model_dump(by_alias=True)
    assert "contextUsed" in payload
    assert payload["contextUsed"]
    item = payload["contextUsed"][0]
    for key in ("chunkId", "documentId", "sourcePath", "startLine", "endLine"):
        assert key in item
    assert "chunk_id" not in item


# 5. Findings can include citations when the deterministic mapping applies (unit-level).
def test_attach_citations_deterministic_mapping():
    finding = ReviewFinding(
        id="backend-1",
        reviewer=ReviewerPersona.BACKEND,
        severity=FindingSeverity.MEDIUM,
        title="Database connection pooling",
        explanation="The database connection pooling timeout handling looks risky.",
        recommendation="Review the database pooling timeout configuration.",
    )
    matching = RetrievalResult(
        chunk_id="doc-1#chunk-0",
        document_id="doc-1",
        source_path="docs/database.md",
        heading="Database",
        snippet="Database connection pooling and query timeout handling.",
        score=0.9,
        start_line=1,
        end_line=5,
    )
    unrelated = RetrievalResult(
        chunk_id="doc-2#chunk-0",
        document_id="doc-2",
        source_path="docs/frontend.md",
        heading="Frontend",
        snippet="Button color spacing layout tweaks.",
        score=0.2,
    )
    [updated] = attach_citations([finding], [matching, unrelated])
    assert [c.chunk_id for c in updated.citations] == ["doc-1#chunk-0"]
    # Provenance only: nothing else about the finding changed.
    assert updated.model_copy(update={"citations": []}) == finding


# 6. Citations serialize with sourcePath, chunkId, startLine/endLine, snippet, score.
def test_citation_serialization_fields():
    finding = ReviewFinding(
        id="f1",
        reviewer=ReviewerPersona.BACKEND,
        severity=FindingSeverity.LOW,
        title="t",
        explanation="database pooling timeout",
        recommendation="review database pooling timeout",
    )
    result = RetrievalResult(
        chunk_id="doc-1#chunk-0",
        document_id="doc-1",
        source_path="docs/database.md",
        heading="Database",
        snippet="database connection pooling timeout",
        score=0.75,
        start_line=3,
        end_line=8,
    )
    [updated] = attach_citations([finding], [result])
    citation = updated.citations[0].model_dump(by_alias=True)
    assert citation["sourcePath"] == "docs/database.md"
    assert citation["chunkId"] == "doc-1#chunk-0"
    assert citation["startLine"] == 3
    assert citation["endLine"] == 8
    assert citation["snippet"]
    assert citation["score"] == 0.75


# ---------------------------------------------------------------------------
# Invariance with retrieval enabled
# ---------------------------------------------------------------------------


def test_retrieval_preserves_findings_and_aggregation():
    baseline = run_review(_request())
    grounded = run_review(
        _request(knowledge_sources=["README.md"], retrieval=_README_QUERY)
    )

    # 7. Finding identity/metadata unchanged (ignoring only the additive citations).
    assert _findings_without_citations(grounded) == _findings_without_citations(baseline)
    # 8. overallRisk unchanged.
    assert grounded.overall_risk == baseline.overall_risk
    # 9. mergeRecommendation unchanged.
    assert grounded.merge_recommendation == baseline.merge_recommendation
    # 10. suggestedReplies unchanged.
    assert grounded.suggested_replies == baseline.suggested_replies
    # summary unchanged too.
    assert grounded.summary == baseline.summary


# 11. Tone behavior unchanged: with the same tone, explanations/recommendations match.
def test_tone_behavior_unchanged_with_retrieval():
    tone = ToneProfile(style="supportive", strictness="high", verbosity="detailed")
    baseline = run_review(_request(tone_profile=tone))
    grounded = run_review(
        _request(
            tone_profile=tone,
            knowledge_sources=["README.md"],
            retrieval=_README_QUERY,
        )
    )
    base_text = [(f.explanation, f.recommendation) for f in baseline.findings]
    grounded_text = [(f.explanation, f.recommendation) for f in grounded.findings]
    assert grounded_text == base_text


# ---------------------------------------------------------------------------
# Error / no-op
# ---------------------------------------------------------------------------


# 12. Unsafe/outside knowledge source is rejected clearly (engine raises RetrievalError).
def test_outside_source_rejected():
    with pytest.raises(RetrievalError):
        run_review(
            _request(knowledge_sources=["backend/app/main.py"], retrieval=_README_QUERY)
        )


# 12b. The /api/reviews route surfaces that as a 400.
def test_outside_source_route_returns_400():
    resp = client.post(
        "/api/reviews",
        json={
            "diffText": API_DIFF,
            "selectedPersonas": ["security"],
            "knowledgeSources": ["backend/app/main.py"],
            "retrieval": {"query": "review"},
        },
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


# 13. URL-like knowledge source is rejected clearly.
def test_url_like_source_rejected():
    with pytest.raises(RetrievalError):
        run_review(
            _request(
                knowledge_sources=["https://example.com/docs/x.md"],
                retrieval=_README_QUERY,
            )
        )


# 14. Retrieval with no results still returns normal output and empty context/citations.
def test_no_results_is_noop(monkeypatch):
    baseline = run_review(_request())

    # Retrieval is requested and runs, but the index returns nothing for this query.
    monkeypatch.setattr(review_engine, "retrieve_context", lambda *a, **k: [])
    grounded = run_review(_request(knowledge_sources=["README.md"], retrieval=_README_QUERY))

    assert grounded.context_used == []
    assert all(f.citations == [] for f in grounded.findings)
    assert _findings_without_citations(grounded) == _findings_without_citations(baseline)
    assert grounded.overall_risk == baseline.overall_risk
    assert grounded.merge_recommendation == baseline.merge_recommendation


# 15. Repeated retrieval-enabled reviews are deterministic.
def test_repeated_retrieval_reviews_deterministic():
    args = dict(knowledge_sources=["README.md"], retrieval=_README_QUERY)
    first = run_review(_request(**args)).model_dump(by_alias=True)
    second = run_review(_request(**args)).model_dump(by_alias=True)
    assert first == second


# Extra: query derivation falls back to title/description/diff summary deterministically.
def test_resolve_retrieval_query_derives_when_blank():
    from app.services.diff_parser import parse_diff

    parsed = parse_diff(API_DIFF)
    request = _request(title="Add users route", description="New endpoint")
    derived = resolve_retrieval_query(request, parsed)
    assert "Add users route" in derived.query
    assert "New endpoint" in derived.query
    assert "users.py" in derived.query
    # Explicit query is preserved as-is.
    explicit = resolve_retrieval_query(
        _request(retrieval=RetrievalQuery(query="explicit q")), parsed
    )
    assert explicit.query == "explicit q"
