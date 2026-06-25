"""Tests for the deterministic local lexical embedding provider (v0.4, Phase 3).

These pin down determinism, fixed dimensionality, L2 normalization, empty-text behavior,
and the (lexical, not semantic) similarity property. No network, model downloads, or
external dependencies are involved.
"""

import math

from app.models import EmbeddingProviderType, EmbeddingVector
from app.models.knowledge import KnowledgeChunk
from app.services.knowledge import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
)


def _chunk(content: str, chunk_id: str = "doc-1#chunk-0") -> KnowledgeChunk:
    return KnowledgeChunk(
        id=chunk_id,
        document_id="doc-1",
        source_path="docs/sample.md",
        heading="Section",
        content=content,
    )


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# 1. Same text produces same vector across repeated calls.
def test_same_text_same_vector():
    provider = DeterministicLocalEmbeddingProvider()
    text = "deterministic local lexical embedding"
    assert provider.embed_text(text) == provider.embed_text(text)


# 2. Vector dimensions are fixed.
def test_fixed_dimensions():
    provider = DeterministicLocalEmbeddingProvider()
    assert provider.dimensions == DEFAULT_EMBEDDING_DIMENSIONS
    assert len(provider.embed_text("hello world")) == DEFAULT_EMBEDDING_DIMENSIONS
    assert len(provider.embed_text("")) == DEFAULT_EMBEDDING_DIMENSIONS

    custom = DeterministicLocalEmbeddingProvider(dimensions=64)
    assert len(custom.embed_text("hello world")) == 64


# 3. EmbeddingVector dimensions match len(values).
def test_embedding_vector_dimensions_match_values():
    provider = DeterministicLocalEmbeddingProvider()
    vector = provider.embed_chunk(_chunk("some content here"))
    assert isinstance(vector, EmbeddingVector)
    assert vector.dimensions == len(vector.values)
    assert vector.dimensions == DEFAULT_EMBEDDING_DIMENSIONS


# 4. Non-empty text produces a normalized vector (L2 norm == 1).
def test_non_empty_text_is_l2_normalized():
    provider = DeterministicLocalEmbeddingProvider()
    values = provider.embed_text("authentication and authorization checks")
    norm = math.sqrt(sum(v * v for v in values))
    assert math.isclose(norm, 1.0, rel_tol=1e-9, abs_tol=1e-9)


# 5. Empty/whitespace-only text returns a safe zero vector.
def test_empty_text_returns_zero_vector():
    provider = DeterministicLocalEmbeddingProvider()
    for text in ["", "   ", "\n\t  "]:
        values = provider.embed_text(text)
        assert len(values) == DEFAULT_EMBEDDING_DIMENSIONS
        assert all(v == 0.0 for v in values)


# 6. Similar lexical text has higher cosine similarity than unrelated text.
def test_lexical_similarity_ranking():
    provider = DeterministicLocalEmbeddingProvider()
    base = provider.embed_text("database connection pool timeout error handling")
    similar = provider.embed_text("database connection pool timeout retry logic")
    unrelated = provider.embed_text("frontend button color and spacing tweaks")
    assert _cosine(base, similar) > _cosine(base, unrelated)


# 7. embed_chunk returns an EmbeddingVector with provider deterministic_local and chunkId.
def test_embed_chunk_metadata():
    provider = DeterministicLocalEmbeddingProvider()
    vector = provider.embed_chunk(_chunk("content", chunk_id="doc-x#chunk-3"))
    assert vector.provider is EmbeddingProviderType.DETERMINISTIC_LOCAL
    assert vector.chunk_id == "doc-x#chunk-3"
    payload = vector.model_dump(by_alias=True)
    assert payload["chunkId"] == "doc-x#chunk-3"
    assert payload["provider"] == "deterministic_local"


# 8. No network/dependency behavior: provider relies only on the stdlib + our models.
def test_offline_stdlib_only():
    import app.services.knowledge.embedding as embedding_module

    source = embedding_module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    for forbidden in ("requests", "httpx", "urllib", "socket", "boto3", "openai"):
        assert forbidden not in text

    # The provider structurally satisfies the EmbeddingProvider protocol.
    assert isinstance(DeterministicLocalEmbeddingProvider(), EmbeddingProvider)


# Extra: embed_chunks maps over chunks deterministically.
def test_embed_chunks_batch():
    provider = DeterministicLocalEmbeddingProvider()
    chunks = [_chunk("alpha beta", "c-0"), _chunk("gamma delta", "c-1")]
    vectors = provider.embed_chunks(chunks)
    assert [v.chunk_id for v in vectors] == ["c-0", "c-1"]
    assert vectors[0].values == provider.embed_text("alpha beta")
