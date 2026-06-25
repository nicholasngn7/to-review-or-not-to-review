"""Deterministic, offline local embeddings (v0.4, Phase 3).

This module provides a **lexical hashing** vectorizer — explicitly *not* a neural or
semantic embedding model. It is fully deterministic, uses only the Python standard
library, and performs **no** network calls, model downloads, Bedrock/live-provider
calls, or token/OAuth handling. It exists to support a future local, in-memory
retrieval index; there is no review integration here.

The approach (feature hashing / "hashing trick"):

* normalize text (lowercase, unicode-normalized),
* tokenize into word tokens deterministically,
* hash each token (SHA-1) into a fixed-size bucket with a signed contribution,
* weight by term frequency,
* L2-normalize the vector.

Because hashing uses `hashlib` (not Python's salted `hash()`), vectors are stable
across processes and runs. See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from typing import Protocol, runtime_checkable

from app.models.knowledge import (
    EmbeddingProviderType,
    EmbeddingVector,
    KnowledgeChunk,
)

DEFAULT_EMBEDDING_DIMENSIONS = 128

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for components that turn text/chunks into embedding vectors."""

    @property
    def provider_type(self) -> EmbeddingProviderType: ...

    @property
    def dimensions(self) -> int: ...

    def embed_text(self, text: str) -> list[float]: ...

    def embed_chunk(self, chunk: KnowledgeChunk) -> EmbeddingVector: ...

    def embed_chunks(self, chunks: list[KnowledgeChunk]) -> list[EmbeddingVector]: ...


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def tokenize(text: str) -> list[str]:
    """Deterministic word tokenization used by the local embedder."""
    return _TOKEN_RE.findall(_normalize(text))


def _bucket_and_sign(token: str, dimensions: int) -> tuple[int, float]:
    """Map a token to a (bucket, sign) using a stable SHA-1 digest."""
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % dimensions
    sign = 1.0 if (digest[8] & 1) == 0 else -1.0
    return bucket, sign


class DeterministicLocalEmbeddingProvider:
    """A deterministic, offline lexical hashing embedder.

    Not a semantic/neural model: similarity reflects shared tokens, not meaning.
    """

    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be a positive integer.")
        self._dimensions = dimensions

    @property
    def provider_type(self) -> EmbeddingProviderType:
        return EmbeddingProviderType.DETERMINISTIC_LOCAL

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_text(self, text: str) -> list[float]:
        """Return an L2-normalized vector for `text`.

        Empty/whitespace-only (or token-less) text yields a zero vector of the
        provider's dimensionality (handled safely, never an error).
        """
        vector = [0.0] * self._dimensions
        tokens = tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            bucket, sign = _bucket_and_sign(token, self._dimensions)
            vector[bucket] += sign  # term frequency accumulates naturally

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            # Signed collisions can cancel out; treat as a zero (low-signal) vector.
            return [0.0] * self._dimensions
        return [value / norm for value in vector]

    def embed_chunk(self, chunk: KnowledgeChunk) -> EmbeddingVector:
        values = self.embed_text(chunk.content)
        return EmbeddingVector(
            chunk_id=chunk.id,
            provider=self.provider_type,
            dimensions=self._dimensions,
            values=values,
        )

    def embed_chunks(self, chunks: list[KnowledgeChunk]) -> list[EmbeddingVector]:
        return [self.embed_chunk(chunk) for chunk in chunks]
