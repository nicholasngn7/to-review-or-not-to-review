"""Local, offline knowledge services for v0.4 RAG-style retrieval.

* Phase 2: **ingestion** (read allow-listed local text files into `KnowledgeDocument`s)
  and **chunking** (split documents into stable `KnowledgeChunk`s).
* Phase 3: a **deterministic local lexical embedding provider** and an **in-memory
  `KnowledgeIndex`** with cosine search.
* Phase 4: a **local-only retrieval service** (`retrieve_context`) composing
  ingest → chunk → index → search.

Everything here is offline and deterministic: no network, no URL/token/OAuth, no neural/
semantic models, no external dependencies, no persistence, and **no** review integration
(retrieval is not wired into review and never populates `citations`/`contextUsed`).
"""

from .chunking import chunk_document
from .embedding import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
    tokenize,
)
from .evaluation import (
    RetrievalEvaluationReport,
    RetrievalEvaluationResult,
    evaluate_case,
    evaluate_retrieval,
    load_evaluation_cases,
    run_cases_against_index,
)
from .index import KnowledgeIndex, build_index
from .ingestion import (
    DEFAULT_ALLOWED_ROOTS,
    IngestionError,
    ingest_local_file,
)
from .retrieval import RetrievalError, retrieve_context

__all__ = [
    "ingest_local_file",
    "IngestionError",
    "DEFAULT_ALLOWED_ROOTS",
    "chunk_document",
    "EmbeddingProvider",
    "DeterministicLocalEmbeddingProvider",
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "tokenize",
    "KnowledgeIndex",
    "build_index",
    "retrieve_context",
    "RetrievalError",
    "load_evaluation_cases",
    "evaluate_case",
    "evaluate_retrieval",
    "run_cases_against_index",
    "RetrievalEvaluationResult",
    "RetrievalEvaluationReport",
]
