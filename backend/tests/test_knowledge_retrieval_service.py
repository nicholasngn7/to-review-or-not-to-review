"""Tests for the local-only retrieval service (v0.4, Phase 4).

Exercises `retrieve_context` end to end (ingest → chunk → index → search) over temp
fixture docs. Offline, deterministic, lexical; no network, URL fetching, or review
integration. Uses a temporary repo root + allow-list so tests never depend on real files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import RetrievalQuery, RetrievalResult
from app.services.knowledge import RetrievalError, retrieve_context


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "database.md").write_text(
        "# Database\n\n"
        "Connection pooling and query timeout handling for the database layer.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "frontend.md").write_text(
        "# Frontend\n\nButton color, spacing, and layout tweaks in the UI.\n",
        encoding="utf-8",
    )
    (tmp_path / "secrets.txt").write_text("api_key=should-not-be-readable", encoding="utf-8")
    return tmp_path


# 1. End-to-end ingest -> chunk -> index -> search over temp fixture docs.
def test_end_to_end_retrieval(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(query="database connection timeout"),
        source_paths=["docs/database.md", "docs/frontend.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert results
    assert all(isinstance(r, RetrievalResult) for r in results)


# 2. Relevant lexical query returns the expected source/chunk first.
def test_relevant_query_ranks_expected_source_first(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(query="database query pooling timeout"),
        source_paths=["docs/database.md", "docs/frontend.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert results[0].source_path == "docs/database.md"


# 3. Deterministic results across repeated calls.
def test_deterministic_results(tmp_path: Path):
    repo = _make_repo(tmp_path)
    query = RetrievalQuery(query="layout spacing button")
    args = dict(
        source_paths=["docs/database.md", "docs/frontend.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    first = [r.model_dump() for r in retrieve_context(query, **args)]
    second = [r.model_dump() for r in retrieve_context(query, **args)]
    assert first == second


# 4. topK is respected.
def test_top_k_respected(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir()
    for i in range(4):
        (repo / "docs" / f"doc{i}.md").write_text(
            f"# Doc {i}\n\nshared retrieval timeout token content variant {i}.\n",
            encoding="utf-8",
        )
    results = retrieve_context(
        RetrievalQuery(query="shared retrieval timeout token", top_k=2),
        source_paths=[f"docs/doc{i}.md" for i in range(4)],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert len(results) == 2


# 5. filters pass through to index search.
def test_filters_pass_through(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(
            query="database frontend layout pooling",
            filters={"source_path": "docs/frontend.md"},
        ),
        source_paths=["docs/database.md", "docs/frontend.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert results
    assert all(r.source_path == "docs/frontend.md" for r in results)


# 6. Empty source_paths returns [] (chosen behavior).
def test_empty_source_paths_returns_empty(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(query="anything"),
        source_paths=[],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert results == []


# 7. Low-signal query returns [].
def test_low_signal_query_returns_empty(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(query="   "),
        source_paths=["docs/database.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    assert results == []


# 8. Outside-root path rejected with a clear RetrievalError.
def test_outside_root_rejected(tmp_path: Path):
    repo = _make_repo(tmp_path)
    with pytest.raises(RetrievalError):
        retrieve_context(
            RetrievalQuery(query="api key"),
            source_paths=["secrets.txt"],
            repo_root=repo,
            allowed_roots=["docs"],
        )


# 9. URL-like path rejected (and never fetched).
def test_url_like_path_rejected(tmp_path: Path):
    repo = _make_repo(tmp_path)
    for url in [
        "https://example.com/docs/database.md",
        "http://localhost/x.md",
        "git@github.com:org/repo.git",
        "ssh://host/repo",
    ]:
        with pytest.raises(RetrievalError):
            retrieve_context(
                RetrievalQuery(query="database"),
                source_paths=[url],
                repo_root=repo,
                allowed_roots=["docs"],
            )


# 10. Result objects conform to RetrievalResult with expected fields.
def test_results_conform_to_model(tmp_path: Path):
    repo = _make_repo(tmp_path)
    results = retrieve_context(
        RetrievalQuery(query="database connection timeout"),
        source_paths=["docs/database.md"],
        repo_root=repo,
        allowed_roots=["docs"],
    )
    result = results[0]
    assert result.chunk_id
    assert result.document_id
    assert result.source_path == "docs/database.md"
    assert result.snippet
    assert result.score > 0.0
    payload = result.model_dump(by_alias=True)
    assert "sourcePath" in payload
    assert "chunkId" in payload


# 11. No review behavior changes: review engine is untouched by retrieval, and the
#     additive review-contract fields still default to empty (no citations/contextUsed).
def test_no_review_behavior_changes():
    import app.services.review_engine as review_engine
    from app.models import ReviewFinding, ReviewRequest, ReviewResponse

    with open(review_engine.__file__, encoding="utf-8") as handle:
        source = handle.read()
    for ref in ("retrieve_context", "KnowledgeIndex", "build_index", "knowledge"):
        assert ref not in source

    # Additive retrieval fields still default to empty/None (placeholders only).
    assert ReviewFinding.model_fields["citations"].default_factory() == []
    assert ReviewResponse.model_fields["context_used"].default_factory() == []
    assert ReviewRequest.model_fields["retrieval"].default is None
    assert ReviewRequest.model_fields["knowledge_sources"].default is None


# 12. Missing file rejected with a clear RetrievalError.
def test_missing_file_rejected(tmp_path: Path):
    repo = _make_repo(tmp_path)
    with pytest.raises(RetrievalError):
        retrieve_context(
            RetrievalQuery(query="database"),
            source_paths=["docs/missing.md"],
            repo_root=repo,
            allowed_roots=["docs"],
        )
