"""Deterministic, offline retrieval evaluation (v0.4, Phase 6).

Pure helpers to score the **local lexical** retriever against fixed
`RetrievalEvaluationCase`s and produce reproducible hit@k / precision@k / recall@k
metrics. These are **regression checks** for the deterministic retriever — they do
**not** measure semantic quality, and the retriever makes no semantic claims.

Everything here is offline and fixture-driven: no network, no embeddings beyond the
existing local hashing provider, no endpoints, and no review-flow changes. Evaluation is
never wired into production routes.

Metric definitions (per case, over the top-`k` results):

* An expected item is a `expected_chunk_ids` entry matched by a result's `chunk_id`, or
  an `expected_source_paths` entry matched by a result's `source_path`.
* **hit_count** = number of *distinct expected items* found in the top-k.
* **hit@k** = `hit_count >= 1`.
* **recall@k** = `hit_count / (#expected items)`.
* **precision@k** = `(# top-k results that match any expected item) / (#top-k results)`.
* **passed** = `hit_count >= minimum_top_k_hit_count`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from pydantic import Field

from app.models.base import CamelModel
from app.models.knowledge import (
    RetrievalEvaluationCase,
    RetrievalQuery,
    RetrievalResult,
)

from .index import KnowledgeIndex

PathLike = Union[str, Path]


class RetrievalEvaluationResult(CamelModel):
    """Per-case retrieval metrics (all deterministic)."""

    case_id: str
    k: int
    expected_count: int = Field(description="Number of distinct expected items.")
    returned_count: int = Field(description="Number of results considered (≤ k).")
    hit_count: int = Field(description="Distinct expected items found in the top-k.")
    relevant_returned: int = Field(
        description="Top-k results that match any expected item."
    )
    hit_at_k: bool
    precision_at_k: float
    recall_at_k: float
    passed: bool


class RetrievalEvaluationReport(CamelModel):
    """Aggregate report across all evaluated cases."""

    k: int
    total_cases: int
    passed_cases: int
    hit_rate: float = Field(description="Fraction of cases with hit@k.")
    mean_precision_at_k: float
    mean_recall_at_k: float
    results: list[RetrievalEvaluationResult] = Field(default_factory=list)


def load_evaluation_cases(path: PathLike) -> list[RetrievalEvaluationCase]:
    """Load fixed evaluation cases (camelCase JSON) into `RetrievalEvaluationCase`s."""
    with Path(path).open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return [RetrievalEvaluationCase.model_validate(item) for item in raw]


def evaluate_case(
    case: RetrievalEvaluationCase,
    results: list[RetrievalResult],
    *,
    k: int = 5,
) -> RetrievalEvaluationResult:
    """Score a single case's results against its expected chunk ids / source paths."""
    top = results[:k]

    expected_chunk_ids = set(case.expected_chunk_ids)
    expected_source_paths = set(case.expected_source_paths)
    expected_count = len(expected_chunk_ids) + len(expected_source_paths)

    found_chunk_ids = {r.chunk_id for r in top} & expected_chunk_ids
    found_source_paths = {r.source_path for r in top if r.source_path is not None} & (
        expected_source_paths
    )
    hit_count = len(found_chunk_ids) + len(found_source_paths)

    relevant_returned = sum(
        1
        for r in top
        if r.chunk_id in expected_chunk_ids
        or (r.source_path is not None and r.source_path in expected_source_paths)
    )

    returned_count = len(top)
    precision = relevant_returned / returned_count if returned_count else 0.0
    recall = hit_count / expected_count if expected_count else 0.0

    return RetrievalEvaluationResult(
        case_id=case.id,
        k=k,
        expected_count=expected_count,
        returned_count=returned_count,
        hit_count=hit_count,
        relevant_returned=relevant_returned,
        hit_at_k=hit_count >= 1,
        precision_at_k=precision,
        recall_at_k=recall,
        passed=hit_count >= case.minimum_top_k_hit_count,
    )


def evaluate_retrieval(
    cases: list[RetrievalEvaluationCase],
    results_by_case: dict[str, list[RetrievalResult]],
    *,
    k: int = 5,
) -> RetrievalEvaluationReport:
    """Score all cases (in order) and aggregate into a deterministic report.

    `results_by_case` maps a case id to its retrieved results. Missing entries are
    treated as empty result lists (a safe, explicit no-hit).
    """
    results: list[RetrievalEvaluationResult] = [
        evaluate_case(case, results_by_case.get(case.id, []), k=k) for case in cases
    ]

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    hits = sum(1 for r in results if r.hit_at_k)
    mean_precision = sum(r.precision_at_k for r in results) / total if total else 0.0
    mean_recall = sum(r.recall_at_k for r in results) / total if total else 0.0
    hit_rate = hits / total if total else 0.0

    return RetrievalEvaluationReport(
        k=k,
        total_cases=total,
        passed_cases=passed,
        hit_rate=hit_rate,
        mean_precision_at_k=mean_precision,
        mean_recall_at_k=mean_recall,
        results=results,
    )


def run_cases_against_index(
    cases: list[RetrievalEvaluationCase],
    index: KnowledgeIndex,
    *,
    k: int = 5,
) -> dict[str, list[RetrievalResult]]:
    """Run each case's query against a prebuilt `KnowledgeIndex` (top-k), deterministically."""
    return {
        case.id: index.search(RetrievalQuery(query=case.query, top_k=k))
        for case in cases
    }
