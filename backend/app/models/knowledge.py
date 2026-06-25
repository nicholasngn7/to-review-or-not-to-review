"""Contract models for future local RAG-style retrieval (v0.4, Phase 1A).

These are **contracts only**. They define the shapes a future, local retrieval
pipeline would produce — ingest → chunk → embed → retrieve → cite — without any
behavior. As of this phase there is:

* no ingestion,
* no chunking,
* no embedding,
* no retrieval,
* no endpoints,
* no frontend/UI changes,
* and **no** changes to the review contract (`ReviewRequest`/`ReviewFinding`/
  `ReviewResponse` are untouched).

Positioning: the planned default embedding provider is a **deterministic local**
(lexical) provider — not a semantic/neural model. A Bedrock/live embedding provider is
an **optional future path** only; the enum value reserved for it here implies no
integration. See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from .base import CamelModel


class KnowledgeSourceType(str, Enum):
    """What kind of source a knowledge document was derived from."""

    REPO_DOC = "repo_doc"
    ARCHITECTURE_NOTE = "architecture_note"
    DIFF = "diff"
    MANUAL_NOTE = "manual_note"


class EmbeddingProviderType(str, Enum):
    """Which embedding provider produced a vector.

    `DETERMINISTIC_LOCAL` is the planned default (a local, lexical, deterministic
    provider). `BEDROCK_OPTIONAL_FUTURE` is a **reserved name only** — there is no
    Bedrock/live integration in this or the current shipped product.
    """

    DETERMINISTIC_LOCAL = "deterministic_local"
    BEDROCK_OPTIONAL_FUTURE = "bedrock_optional_future"


class KnowledgeDocument(CamelModel):
    """A selected source document before chunking."""

    id: str = Field(description="Stable identifier for this document.")
    title: str = Field(description="Human-readable title (e.g. first H1 or filename).")
    source_type: KnowledgeSourceType = Field(
        description="What kind of source this document came from."
    )
    source_path: Optional[str] = Field(
        default=None, description="Repo-relative path, when the source is a file."
    )
    content: str = Field(description="Raw text content of the document.")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form string metadata."
    )


class KnowledgeChunk(CamelModel):
    """A retrievable unit produced by (future) chunking of a document."""

    id: str = Field(description="Stable identifier for this chunk.")
    document_id: str = Field(description="Id of the parent KnowledgeDocument.")
    source_path: Optional[str] = Field(
        default=None, description="Repo-relative path of the source, when known."
    )
    heading: Optional[str] = Field(
        default=None, description="Nearest heading the chunk falls under, if any."
    )
    content: str = Field(description="The chunk's text.")
    start_line: Optional[int] = Field(
        default=None, description="Start line in the source, when known."
    )
    end_line: Optional[int] = Field(
        default=None, description="End line in the source, when known."
    )
    token_estimate: Optional[int] = Field(
        default=None, description="Rough token count estimate, when computed."
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form string metadata."
    )


class EmbeddingVector(CamelModel):
    """A provider-tagged embedding for a single chunk.

    `dimensions` must equal `len(values)` so a vector is internally consistent.
    """

    chunk_id: str = Field(description="Id of the chunk this vector represents.")
    provider: EmbeddingProviderType = Field(
        description="Which embedding provider produced this vector."
    )
    dimensions: int = Field(ge=0, description="Number of dimensions; must equal len(values).")
    values: list[float] = Field(description="The embedding values.")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form string metadata."
    )

    @model_validator(mode="after")
    def _check_dimensions_match_values(self) -> "EmbeddingVector":
        if self.dimensions != len(self.values):
            raise ValueError(
                f"dimensions ({self.dimensions}) must equal len(values) "
                f"({len(self.values)})."
            )
        return self


class RetrievalQuery(CamelModel):
    """A request to retrieve relevant chunks for some review context."""

    query: str = Field(description="Query text to retrieve context for.")
    top_k: int = Field(default=5, ge=1, description="Max number of results to return.")
    persona: Optional[str] = Field(
        default=None, description="Optional persona hint for the query."
    )
    file_path: Optional[str] = Field(
        default=None, description="Optional file the query relates to."
    )
    diff_summary: Optional[str] = Field(
        default=None, description="Optional short summary of the diff under review."
    )
    filters: dict[str, str] = Field(
        default_factory=dict, description="Optional string filters/scoping hints."
    )


class RetrievalResult(CamelModel):
    """A single ranked result from a (future) retrieval call."""

    chunk_id: str = Field(description="Id of the retrieved chunk.")
    document_id: str = Field(description="Id of the chunk's parent document.")
    source_path: Optional[str] = Field(
        default=None, description="Repo-relative path of the source, when known."
    )
    heading: Optional[str] = Field(
        default=None, description="Nearest heading for the chunk, if any."
    )
    snippet: str = Field(description="Short, display-ready excerpt of the chunk.")
    score: float = Field(description="Similarity score (provider-relative).")
    start_line: Optional[int] = Field(
        default=None, description="Start line in the source, when known."
    )
    end_line: Optional[int] = Field(
        default=None, description="End line in the source, when known."
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form string metadata."
    )


class RetrievedCitation(CamelModel):
    """Provenance attached to a grounded review point (display-ready).

    Citations are provenance only; they are designed never to change review behavior.
    """

    source_path: Optional[str] = Field(
        default=None, description="Repo-relative path of the cited source, when known."
    )
    heading: Optional[str] = Field(
        default=None, description="Nearest heading for the cited chunk, if any."
    )
    snippet: str = Field(description="Short, display-ready excerpt for the citation.")
    score: float = Field(description="Similarity score (provider-relative).")
    start_line: Optional[int] = Field(
        default=None, description="Start line in the source, when known."
    )
    end_line: Optional[int] = Field(
        default=None, description="End line in the source, when known."
    )
    chunk_id: str = Field(description="Id of the cited chunk.")


class RetrievalEvaluationCase(CamelModel):
    """One fixture case for (future) deterministic retrieval evaluation."""

    id: str = Field(description="Stable identifier for this evaluation case.")
    query: str = Field(description="Query text to evaluate.")
    expected_chunk_ids: list[str] = Field(
        default_factory=list, description="Gold chunk ids a correct retriever should return."
    )
    expected_source_paths: list[str] = Field(
        default_factory=list, description="Gold source paths a correct retriever should return."
    )
    minimum_top_k_hit_count: int = Field(
        default=1,
        ge=1,
        description="Minimum number of expected items that must appear in top-k.",
    )
