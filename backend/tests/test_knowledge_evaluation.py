"""Tests for deterministic, offline retrieval evaluation (v0.4, Phase 6).

Builds a fixed synthetic corpus into an in-memory index, runs fixed evaluation cases,
and asserts hit@k / precision@k / recall@k and pass/fail behavior. Fixture-based and
offline: no network, no endpoints, no review-flow changes. These metrics are regression
checks for the lexical retriever and do not measure semantic quality.
"""

from __future__ import annotations

from pathlib import Path

from app.models.knowledge import (
    RetrievalEvaluationCase,
    RetrievalResult,
)
from app.services.knowledge import (
    build_index,
    chunk_document,
    evaluate_case,
    evaluate_retrieval,
    ingest_local_file,
    load_evaluation_cases,
    run_cases_against_index,
)

FIXTURES = Path(__file__).parent / "fixtures" / "knowledge"
CASES_PATH = FIXTURES / "retrieval_cases.json"
DOC_PATHS = [
    "docs/authentication.md",
    "docs/retrieval.md",
    "docs/frontend.md",
    "docs/reliability.md",
    "docs/security.md",
]


def _build_corpus_index():
    chunks = []
    for rel in DOC_PATHS:
        document = ingest_local_file(rel, repo_root=FIXTURES, allowed_roots=["docs"])
        chunks.extend(chunk_document(document))
    return build_index(chunks)


def _result(chunk_id: str, source_path: str | None, score: float = 0.5) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-x",
        source_path=source_path,
        snippet="snippet",
        score=score,
    )


# 1. Evaluation cases load into RetrievalEvaluationCase models.
def test_cases_load_into_models():
    cases = load_evaluation_cases(CASES_PATH)
    assert cases
    assert all(isinstance(c, RetrievalEvaluationCase) for c in cases)
    by_id = {c.id for c in cases}
    assert {"auth-1", "retrieval-1", "frontend-1", "reliability-1", "security-1"} <= by_id
    # camelCase aliases were parsed.
    auth = next(c for c in cases if c.id == "auth-1")
    assert auth.expected_source_paths == ["docs/authentication.md"]
    assert auth.minimum_top_k_hit_count == 1


# 2. Synthetic corpus ingests/chunks/indexes deterministically.
def test_corpus_indexes_deterministically():
    first = _build_corpus_index()
    second = _build_corpus_index()
    assert len(first) == len(second)
    assert first.chunk_ids == second.chunk_ids
    assert len(first) >= len(DOC_PATHS)  # at least one chunk per doc


# 3. Query cases retrieve expected source paths in top k.
def test_topic_queries_retrieve_expected_sources():
    index = _build_corpus_index()
    cases = [c for c in load_evaluation_cases(CASES_PATH) if c.id != "no-hit-1"]
    results_by_case = run_cases_against_index(cases, index, k=5)
    for case in cases:
        top_sources = [r.source_path for r in results_by_case[case.id]]
        assert case.expected_source_paths[0] == top_sources[0], (
            f"{case.id}: expected {case.expected_source_paths[0]} first, got {top_sources}"
        )


# 4. hit@k is computed correctly.
def test_hit_at_k():
    case = RetrievalEvaluationCase(
        id="c", query="q", expected_source_paths=["docs/a.md"], minimum_top_k_hit_count=1
    )
    hit = evaluate_case(case, [_result("a#0", "docs/a.md")], k=5)
    assert hit.hit_at_k is True
    assert hit.hit_count == 1

    miss = evaluate_case(case, [_result("b#0", "docs/b.md")], k=5)
    assert miss.hit_at_k is False
    assert miss.hit_count == 0


# 5. precision@k is computed correctly.
def test_precision_at_k():
    case = RetrievalEvaluationCase(
        id="c", query="q", expected_source_paths=["docs/a.md"], minimum_top_k_hit_count=1
    )
    # 1 of 2 returned results is relevant -> precision 0.5.
    res = evaluate_case(
        case, [_result("a#0", "docs/a.md"), _result("b#0", "docs/b.md")], k=5
    )
    assert res.relevant_returned == 1
    assert res.returned_count == 2
    assert res.precision_at_k == 0.5


# 6. recall@k is computed correctly.
def test_recall_at_k():
    case = RetrievalEvaluationCase(
        id="c",
        query="q",
        expected_source_paths=["docs/a.md", "docs/b.md"],
        minimum_top_k_hit_count=1,
    )
    # 1 of 2 expected items found -> recall 0.5.
    res = evaluate_case(case, [_result("a#0", "docs/a.md")], k=5)
    assert res.expected_count == 2
    assert res.hit_count == 1
    assert res.recall_at_k == 0.5


# 7. minimumTopKHitCount pass/fail is honored.
def test_minimum_hit_count_pass_fail():
    case = RetrievalEvaluationCase(
        id="c",
        query="q",
        expected_source_paths=["docs/a.md", "docs/b.md"],
        minimum_top_k_hit_count=2,
    )
    one_hit = evaluate_case(case, [_result("a#0", "docs/a.md")], k=5)
    assert one_hit.passed is False  # only 1 hit, needs 2

    two_hits = evaluate_case(
        case, [_result("a#0", "docs/a.md"), _result("b#0", "docs/b.md")], k=5
    )
    assert two_hits.passed is True


# 8. Metrics are reproducible across repeated runs.
def test_metrics_reproducible():
    cases = load_evaluation_cases(CASES_PATH)
    index = _build_corpus_index()
    first = evaluate_retrieval(cases, run_cases_against_index(cases, index, k=5), k=5)
    second = evaluate_retrieval(cases, run_cases_against_index(cases, index, k=5), k=5)
    assert first.model_dump() == second.model_dump()


# 9. A no-hit case produces expected failed metrics.
def test_no_hit_case_fails():
    cases = load_evaluation_cases(CASES_PATH)
    index = _build_corpus_index()
    report = evaluate_retrieval(cases, run_cases_against_index(cases, index, k=5), k=5)
    no_hit = next(r for r in report.results if r.case_id == "no-hit-1")
    assert no_hit.hit_at_k is False
    assert no_hit.hit_count == 0
    assert no_hit.recall_at_k == 0.0
    assert no_hit.passed is False
    # The five topic cases all pass.
    topic = [r for r in report.results if r.case_id != "no-hit-1"]
    assert all(r.passed for r in topic)
    assert report.passed_cases == len(topic)


# 10. Evaluation handles empty results safely.
def test_empty_results_safe():
    case = RetrievalEvaluationCase(
        id="c", query="q", expected_source_paths=["docs/a.md"], minimum_top_k_hit_count=1
    )
    res = evaluate_case(case, [], k=5)
    assert res.returned_count == 0
    assert res.precision_at_k == 0.0
    assert res.recall_at_k == 0.0
    assert res.hit_at_k is False
    assert res.passed is False

    # A missing case id in results_by_case is treated as empty.
    report = evaluate_retrieval([case], {}, k=5)
    assert report.total_cases == 1
    assert report.passed_cases == 0
    assert report.hit_rate == 0.0


# 11. Evaluation remains offline and fixture-based (no network/URL imports).
def test_evaluation_is_offline():
    import app.services.knowledge.evaluation as evaluation_module

    with open(evaluation_module.__file__, encoding="utf-8") as handle:
        source = handle.read()
    for forbidden in ("requests", "httpx", "urllib", "socket", "boto3", "openai"):
        assert forbidden not in source


# 12. Aggregate report shape and camelCase serialization.
def test_report_camel_case_and_aggregates():
    cases = load_evaluation_cases(CASES_PATH)
    index = _build_corpus_index()
    report = evaluate_retrieval(cases, run_cases_against_index(cases, index, k=5), k=5)
    payload = report.model_dump(by_alias=True)
    assert "meanPrecisionAtK" in payload
    assert "meanRecallAtK" in payload
    assert "hitRate" in payload
    assert payload["results"][0]["caseId"]
    # Five of six cases hit.
    assert report.hit_rate == 5 / 6
