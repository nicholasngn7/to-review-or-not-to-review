"""Tests for the in-memory KnowledgeIndex and cosine search (v0.4, Phase 3).

Covers index construction, ranking, top-k limiting, deterministic tie-breaking, simple
metadata/source-path filters, graceful empty handling, and result-shape completeness.
In-memory only: no persistence, no network, no review integration.
"""

from __future__ import annotations

from app.models import RetrievalQuery, RetrievalResult
from app.models.knowledge import KnowledgeChunk
from app.services.knowledge import (
    DeterministicLocalEmbeddingProvider,
    KnowledgeIndex,
    build_index,
)


def _chunk(
    chunk_id: str,
    content: str,
    *,
    document_id: str = "doc-1",
    source_path: str = "docs/sample.md",
    heading: str | None = "Section",
    start_line: int = 1,
    end_line: int = 5,
    metadata: dict[str, str] | None = None,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=chunk_id,
        document_id=document_id,
        source_path=source_path,
        heading=heading,
        content=content,
        start_line=start_line,
        end_line=end_line,
        token_estimate=len(content.split()),
        metadata=metadata or {},
    )


def _sample_chunks() -> list[KnowledgeChunk]:
    return [
        _chunk("c-auth", "authentication and authorization session token validation"),
        _chunk("c-db", "database connection pooling and query timeout handling"),
        _chunk("c-ui", "frontend button color spacing and layout tweaks"),
    ]


# 1. build_index stores all chunks and vectors.
def test_build_index_stores_chunks_and_vectors():
    chunks = _sample_chunks()
    index = build_index(chunks)
    assert len(index) == 3
    assert set(index.chunk_ids) == {"c-auth", "c-db", "c-ui"}
    for chunk in chunks:
        assert index.get_chunk(chunk.id) is not None
        vector = index.get_vector(chunk.id)
        assert vector is not None
        assert len(vector) == index.provider.dimensions


# 2. search returns RetrievalResult models.
def test_search_returns_retrieval_results():
    index = build_index(_sample_chunks())
    results = index.search(RetrievalQuery(query="authentication token"))
    assert results
    assert all(isinstance(r, RetrievalResult) for r in results)


# 3. topK limits result count.
def test_top_k_limits_results():
    chunks = [
        _chunk(f"c-{i}", f"database connection pooling variant {i} timeout")
        for i in range(5)
    ]
    index = build_index(chunks)
    results = index.search(RetrievalQuery(query="database connection timeout", top_k=2))
    assert len(results) == 2


# 4. relevant lexical query ranks expected chunk first.
def test_relevant_query_ranks_expected_chunk_first():
    index = build_index(_sample_chunks())
    results = index.search(RetrievalQuery(query="database query timeout pooling"))
    assert results[0].chunk_id == "c-db"


# 5. deterministic tie-breaking works (equal score -> chunk id ascending).
def test_deterministic_tie_breaking():
    chunks = [
        _chunk("c-zeta", "identical shared content tokens here"),
        _chunk("c-alpha", "identical shared content tokens here"),
        _chunk("c-mu", "identical shared content tokens here"),
    ]
    index = build_index(chunks)
    results = index.search(RetrievalQuery(query="identical shared content tokens"))
    ids = [r.chunk_id for r in results]
    scores = [round(r.score, 9) for r in results]
    assert len(set(scores)) == 1  # all tied
    assert ids == ["c-alpha", "c-mu", "c-zeta"]  # ascending id tie-break


# 6. filters work (source_path and metadata).
def test_filters_restrict_candidates():
    chunks = [
        _chunk("c-a", "shared timeout content", source_path="docs/a.md",
               metadata={"category": "backend"}),
        _chunk("c-b", "shared timeout content", source_path="docs/b.md",
               metadata={"category": "frontend"}),
    ]
    index = build_index(chunks)

    by_path = index.search(
        RetrievalQuery(query="shared timeout", filters={"source_path": "docs/a.md"})
    )
    assert [r.chunk_id for r in by_path] == ["c-a"]

    by_meta = index.search(
        RetrievalQuery(query="shared timeout", filters={"category": "frontend"})
    )
    assert [r.chunk_id for r in by_meta] == ["c-b"]

    none_match = index.search(
        RetrievalQuery(query="shared timeout", filters={"category": "nonexistent"})
    )
    assert none_match == []


# 7. search handles no chunks gracefully.
def test_search_empty_index():
    index = KnowledgeIndex()
    assert index.search(RetrievalQuery(query="anything")) == []


# 8. search handles empty/low-signal queries safely.
def test_search_empty_query():
    index = build_index(_sample_chunks())
    assert index.search(RetrievalQuery(query="")) == []
    assert index.search(RetrievalQuery(query="    ")) == []


# 9. results include sourcePath, heading, startLine/endLine, snippet, score, metadata.
def test_result_shape_complete():
    chunk = _chunk(
        "c-1",
        "authentication token validation logic",
        source_path="docs/auth.md",
        heading="Auth",
        start_line=10,
        end_line=20,
        metadata={"category": "backend"},
    )
    index = build_index([chunk])
    result = index.search(RetrievalQuery(query="authentication token"))[0]
    assert result.source_path == "docs/auth.md"
    assert result.heading == "Auth"
    assert result.start_line == 10
    assert result.end_line == 20
    assert result.snippet
    assert result.score > 0.0
    assert result.metadata == {"category": "backend"}

    payload = result.model_dump(by_alias=True)
    assert "sourcePath" in payload
    assert "startLine" in payload
    assert "endLine" in payload


# 10. repeated searches are deterministic.
def test_repeated_searches_deterministic():
    index = build_index(_sample_chunks())
    query = RetrievalQuery(query="authentication session token", top_k=3)
    first = [r.model_dump() for r in index.search(query)]
    second = [r.model_dump() for r in index.search(query)]
    assert first == second


# Extra: build_index accepts an explicit provider instance.
def test_build_index_with_explicit_provider():
    provider = DeterministicLocalEmbeddingProvider(dimensions=64)
    index = build_index(_sample_chunks(), provider=provider)
    assert index.provider is provider
    assert len(index.get_vector("c-auth")) == 64
