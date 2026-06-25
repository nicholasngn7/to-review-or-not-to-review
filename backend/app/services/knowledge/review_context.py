"""Opt-in review grounding helpers (v0.4, Phase 5).

Glue between the review flow and the local retrieval service. Everything here is
**provenance-only**: it decides whether to retrieve, derives a deterministic retrieval
query when the caller didn't supply one, and attaches retrieved context to findings as
`RetrievedCitation`s. It never changes a finding's detection, severity, confidence, or
any aggregation — it only copies findings with a populated `citations` list.

Retrieval itself stays local, offline, deterministic, and lexical (see `retrieval.py`).
This is not semantic search and not production RAG.
"""

from __future__ import annotations

from app.models.diff import ParsedDiff
from app.models.knowledge import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedCitation,
)
from app.models.review import ReviewFinding, ReviewRequest

from .embedding import tokenize

# Max citations attached to a single finding (kept small and deterministic).
MAX_CITATIONS_PER_FINDING = 2

# Short/common tokens that should not, on their own, justify a citation match.
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "this", "that", "from", "into", "your", "you",
        "are", "was", "were", "will", "would", "should", "could", "have", "has",
        "not", "but", "all", "any", "can", "may", "use", "used", "using", "via",
        "per", "its", "it", "is", "of", "to", "in", "on", "or", "as", "be", "by",
        "an", "a", "if", "no", "do", "does", "when", "where", "which", "what",
    }
)
_MIN_TOKEN_LEN = 3


def should_retrieve(request: ReviewRequest) -> bool:
    """Retrieval is opt-in: it runs only when local `knowledge_sources` are provided.

    `retrieval` alone (without sources) carries no files to read, so it does not by
    itself trigger retrieval.
    """
    return bool(request.knowledge_sources)


def _diff_summary(parsed: ParsedDiff) -> str:
    paths: list[str] = []
    for file in parsed.files:
        path = file.new_path or file.old_path
        if path:
            paths.append(path)
    return " ".join(paths)


def resolve_retrieval_query(request: ReviewRequest, parsed: ParsedDiff) -> RetrievalQuery:
    """Use the caller's `retrieval` query if present; otherwise derive one deterministically.

    When `retrieval.query` is blank/absent, the query text is derived from the MR title,
    description, and changed file paths (a stable "diff summary"). Any caller-provided
    `top_k`/`filters`/etc. on `retrieval` are preserved.
    """
    provided = request.retrieval
    if provided is not None and provided.query and provided.query.strip():
        return provided

    parts: list[str] = []
    if request.title:
        parts.append(request.title)
    if request.description:
        parts.append(request.description)
    summary = _diff_summary(parsed)
    if summary:
        parts.append(summary)
    derived_text = " ".join(parts).strip()

    if provided is not None:
        return provided.model_copy(update={"query": derived_text})
    return RetrievalQuery(query=derived_text)


def _meaningful_tokens(text: str) -> set[str]:
    return {
        token
        for token in tokenize(text)
        if len(token) >= _MIN_TOKEN_LEN and token not in _STOPWORDS
    }


def _finding_tokens(finding: ReviewFinding) -> set[str]:
    blob = " ".join(
        part
        for part in (
            finding.title,
            finding.explanation,
            finding.recommendation,
            finding.file_path or "",
        )
        if part
    )
    return _meaningful_tokens(blob)


def _result_tokens(result: RetrievalResult) -> set[str]:
    blob = " ".join(
        part
        for part in (result.snippet, result.heading or "", result.source_path or "")
        if part
    )
    return _meaningful_tokens(blob)


def _to_citation(result: RetrievalResult) -> RetrievedCitation:
    return RetrievedCitation(
        source_path=result.source_path,
        heading=result.heading,
        snippet=result.snippet,
        score=result.score,
        start_line=result.start_line,
        end_line=result.end_line,
        chunk_id=result.chunk_id,
    )


def attach_citations(
    findings: list[ReviewFinding], results: list[RetrievalResult]
) -> list[ReviewFinding]:
    """Return copies of `findings` with provenance-only citations attached.

    Mapping rule (deterministic): a retrieved result is cited by a finding when their
    *meaningful* tokens (length ≥ 3, excluding common stopwords) lexically overlap, taken
    from the finding's title/explanation/recommendation/file path and the result's
    snippet/heading/source path. Results are considered in retrieval-rank order and capped
    at `MAX_CITATIONS_PER_FINDING` per finding. Citations are provenance only: they never
    change finding content, severity, confidence, or any aggregation. If `results` is
    empty (or nothing overlaps), findings are returned unchanged (no citations).
    """
    if not results:
        return findings

    result_token_sets = [(r, _result_tokens(r)) for r in results]

    updated: list[ReviewFinding] = []
    for finding in findings:
        finding_tokens = _finding_tokens(finding)
        citations: list[RetrievedCitation] = []
        for result, result_tokens in result_token_sets:
            if finding_tokens & result_tokens:
                citations.append(_to_citation(result))
                if len(citations) >= MAX_CITATIONS_PER_FINDING:
                    break
        if citations:
            updated.append(finding.model_copy(update={"citations": citations}))
        else:
            updated.append(finding)
    return updated
