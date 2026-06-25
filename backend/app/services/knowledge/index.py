"""In-memory knowledge index with deterministic cosine search (v0.4, Phase 3).

`KnowledgeIndex` stores `KnowledgeChunk`s and their local lexical embeddings in memory
and answers `RetrievalQuery`s with cosine-similarity ranking. It is **offline and
in-memory only**: no vector DB, no disk index, no external service, no network.

This is retrieval **groundwork** — it is not wired into the review flow, it does not
populate `ReviewFinding.citations` or `ReviewResponse.contextUsed`, and similarity is
lexical (shared tokens), not semantic. See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

import re

from app.models.knowledge import KnowledgeChunk, RetrievalQuery, RetrievalResult

from .embedding import DeterministicLocalEmbeddingProvider, EmbeddingProvider

_WHITESPACE_RE = re.compile(r"\s+")
_SNIPPET_MAX_CHARS = 240

# Filter keys that map to a known chunk field rather than free-form metadata.
_SOURCE_PATH_KEYS = {"source_path", "sourcePath"}
_HEADING_KEYS = {"heading"}


def _make_snippet(content: str, max_chars: int = _SNIPPET_MAX_CHARS) -> str:
    collapsed = _WHITESPACE_RE.sub(" ", content).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars].rstrip() + "…"


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class KnowledgeIndex:
    """An in-memory store of chunks + local embeddings, searchable by cosine similarity."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._provider: EmbeddingProvider = (
            provider if provider is not None else DeterministicLocalEmbeddingProvider()
        )
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._vectors: dict[str, list[float]] = {}

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def chunk_ids(self) -> list[str]:
        return list(self._chunks.keys())

    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        vector = self._provider.embed_chunk(chunk)
        self._chunks[chunk.id] = chunk
        self._vectors[chunk.id] = list(vector.values)

    def add_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        for chunk in chunks:
            self.add_chunk(chunk)

    def get_chunk(self, chunk_id: str) -> KnowledgeChunk | None:
        return self._chunks.get(chunk_id)

    def get_vector(self, chunk_id: str) -> list[float] | None:
        return self._vectors.get(chunk_id)

    def _passes_filters(self, chunk: KnowledgeChunk, filters: dict[str, str]) -> bool:
        for key, expected in filters.items():
            if key in _SOURCE_PATH_KEYS:
                if chunk.source_path != expected:
                    return False
            elif key in _HEADING_KEYS:
                if chunk.heading != expected:
                    return False
            elif chunk.metadata.get(key) != expected:
                return False
        return True

    def search(self, query: RetrievalQuery) -> list[RetrievalResult]:
        """Return up to `query.top_k` results ranked by cosine similarity.

        Ordering is deterministic: score descending, then chunk id ascending. Query text
        with no lexical signal (zero vector) returns no results. Results with a
        non-positive score are excluded so output reflects genuine lexical overlap.
        """
        query_vector = self._provider.embed_text(query.query)
        if not any(query_vector):
            return []

        scored: list[tuple[float, str]] = []
        for chunk_id, chunk in self._chunks.items():
            if query.filters and not self._passes_filters(chunk, query.filters):
                continue
            score = _dot(query_vector, self._vectors[chunk_id])
            if score <= 0.0:
                continue
            scored.append((score, chunk_id))

        scored.sort(key=lambda item: (-item[0], item[1]))
        top = scored[: query.top_k]

        results: list[RetrievalResult] = []
        for score, chunk_id in top:
            chunk = self._chunks[chunk_id]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    source_path=chunk.source_path,
                    heading=chunk.heading,
                    snippet=_make_snippet(chunk.content),
                    score=score,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    metadata=dict(chunk.metadata),
                )
            )
        return results


def build_index(
    chunks: list[KnowledgeChunk], provider: EmbeddingProvider | None = None
) -> KnowledgeIndex:
    """Build an in-memory `KnowledgeIndex` from chunks using a local embedding provider."""
    index = KnowledgeIndex(provider=provider)
    index.add_chunks(chunks)
    return index
