"""Tests for the v0.4 Phase 1B additive review-contract fields.

Phase 1B adds optional, backward-compatible retrieval fields to the review contract:
`ReviewRequest.knowledge_sources`/`retrieval`, `ReviewFinding.citations`, and
`ReviewResponse.context_used`. They are accepted by the contract but **ignored by
runtime review behavior** in this phase (no ingestion/chunking/embedding/retrieval, no
citation generation). These tests pin down defaults, camelCase round-trips, and
backward compatibility.
"""

from app.models import (
    DiffStats,
    MergeRecommendation,
    ReviewFinding,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
    RetrievalQuery,
    RetrievalResult,
    RetrievedCitation,
    RiskLevel,
)
from app.models.enums import FindingSeverity, ReviewerPersona


def _finding(fid: str = "f1") -> ReviewFinding:
    return ReviewFinding(
        id=fid,
        reviewer=ReviewerPersona.SECURITY,
        severity=FindingSeverity.MEDIUM,
        title="Example",
        explanation="why",
        recommendation="do x",
    )


def _response() -> ReviewResponse:
    return ReviewResponse(
        overall_risk=RiskLevel.LOW,
        merge_recommendation=MergeRecommendation.READY,
        summary=ReviewSummary(headline="ok", details="all good"),
        diff_stats=DiffStats(),
    )


# 1. ReviewRequest accepts knowledgeSources and retrieval.
def test_request_accepts_knowledge_sources_and_retrieval():
    req = ReviewRequest(
        diff_text="diff --git a b",
        knowledge_sources=["docs/architecture.md", "README.md"],
        retrieval=RetrievalQuery(query="auth", top_k=3),
    )
    assert req.knowledge_sources == ["docs/architecture.md", "README.md"]
    assert isinstance(req.retrieval, RetrievalQuery)
    assert req.retrieval.top_k == 3


# 2. ReviewRequest defaults knowledge_sources and retrieval to None.
def test_request_defaults_retrieval_fields_to_none():
    req = ReviewRequest(diff_text="diff --git a b")
    assert req.knowledge_sources is None
    assert req.retrieval is None


# 3. ReviewRequest camelCase round-trip works.
def test_request_camel_case_round_trip():
    req = ReviewRequest(
        diff_text="diff --git a b",
        knowledge_sources=["docs/a.md"],
        retrieval=RetrievalQuery(query="q", file_path="app/x.py"),
    )
    data = req.model_dump(by_alias=True)
    assert data["knowledgeSources"] == ["docs/a.md"]
    assert data["retrieval"]["filePath"] == "app/x.py"
    assert data["retrieval"]["topK"] == 5
    assert "knowledge_sources" not in data

    # Reconstruct from camelCase JSON.
    rebuilt = ReviewRequest.model_validate(data)
    assert rebuilt.knowledge_sources == ["docs/a.md"]
    assert rebuilt.retrieval.file_path == "app/x.py"


# 4. ReviewFinding defaults citations to an empty list.
def test_finding_defaults_citations_empty():
    finding = _finding()
    assert finding.citations == []


# 5. ReviewFinding accepts citations and serializes camelCase nested fields.
def test_finding_accepts_citations_camel_case():
    finding = ReviewFinding(
        id="f1",
        reviewer=ReviewerPersona.SECURITY,
        severity=FindingSeverity.HIGH,
        title="t",
        explanation="e",
        recommendation="r",
        citations=[
            RetrievedCitation(
                source_path="docs/architecture.md",
                heading="Provider abstraction",
                snippet="...",
                score=0.42,
                start_line=10,
                end_line=20,
                chunk_id="docs/architecture.md#3",
            )
        ],
    )
    data = finding.model_dump(by_alias=True)
    assert len(data["citations"]) == 1
    c = data["citations"][0]
    assert c["sourcePath"] == "docs/architecture.md"
    assert c["chunkId"] == "docs/architecture.md#3"
    assert c["startLine"] == 10
    assert c["endLine"] == 20


# 6. ReviewResponse defaults contextUsed to an empty list.
def test_response_defaults_context_used_empty():
    resp = _response()
    assert resp.context_used == []
    assert resp.model_dump(by_alias=True)["contextUsed"] == []


# 7. ReviewResponse accepts contextUsed and serializes camelCase nested fields.
def test_response_accepts_context_used_camel_case():
    resp = _response()
    resp.context_used = [
        RetrievalResult(
            chunk_id="docs/a.md#1",
            document_id="docs/a.md",
            source_path="docs/a.md",
            heading="Intro",
            snippet="hello",
            score=0.9,
            start_line=1,
            end_line=4,
        )
    ]
    data = resp.model_dump(by_alias=True)
    assert len(data["contextUsed"]) == 1
    cu = data["contextUsed"][0]
    assert cu["chunkId"] == "docs/a.md#1"
    assert cu["documentId"] == "docs/a.md"
    assert cu["sourcePath"] == "docs/a.md"
    assert cu["startLine"] == 1


# 8. Backward compatibility: a request without retrieval fields still validates, and a
# response built without retrieval context carries empty defaults (not None) without
# affecting risk/recommendation/findings/suggested replies.
def test_backward_compatibility_defaults_present_and_inert():
    req = ReviewRequest(
        diff_text="diff --git a b",
        selected_personas=[ReviewerPersona.SECURITY],
    )
    req_data = req.model_dump(by_alias=True)
    assert req_data["knowledgeSources"] is None
    assert req_data["retrieval"] is None

    resp = ReviewResponse(
        overall_risk=RiskLevel.HIGH,
        merge_recommendation=MergeRecommendation.NEEDS_HUMAN_REVIEW,
        summary=ReviewSummary(headline="h", details="d"),
        diff_stats=DiffStats(),
        findings=[_finding()],
    )
    data = resp.model_dump(by_alias=True)
    # New fields are present as empty defaults; existing behavior is unchanged.
    assert data["contextUsed"] == []
    assert data["findings"][0]["citations"] == []
    assert data["suggestedReplies"] == []
    assert data["overallRisk"] == "high"
    assert data["mergeRecommendation"] == "needs_human_review"
    assert len(data["findings"]) == 1


# 9. No shared mutable defaults for citations / context_used.
def test_no_shared_mutable_defaults():
    f1, f2 = _finding("a"), _finding("b")
    f1.citations.append(
        RetrievedCitation(snippet="s", score=0.1, chunk_id="c1")
    )
    assert f2.citations == []
    assert f1.citations is not f2.citations

    r1, r2 = _response(), _response()
    r1.context_used.append(
        RetrievalResult(chunk_id="c1", document_id="d1", snippet="s", score=0.1)
    )
    assert r2.context_used == []
    assert r1.context_used is not r2.context_used


# 10. The new request fields accept camelCase aliases on construction.
def test_request_accepts_camel_case_aliases_on_construction():
    req = ReviewRequest.model_validate(
        {
            "diffText": "diff --git a b",
            "knowledgeSources": ["docs/a.md"],
            "retrieval": {"query": "q", "topK": 2},
        }
    )
    assert req.knowledge_sources == ["docs/a.md"]
    assert req.retrieval.top_k == 2
