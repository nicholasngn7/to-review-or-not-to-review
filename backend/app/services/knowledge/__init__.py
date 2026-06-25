"""Local, offline knowledge services for v0.4 RAG-style retrieval.

Phase 2 provides **ingestion** (read allow-listed local text files into
`KnowledgeDocument`s) and **chunking** (split documents into stable `KnowledgeChunk`s).
Everything here is offline and deterministic: no network, no URL/token/OAuth, no
embeddings, no vector similarity, and no retrieval/search (those land in later phases).
"""

from .chunking import chunk_document
from .ingestion import (
    DEFAULT_ALLOWED_ROOTS,
    IngestionError,
    ingest_local_file,
)

__all__ = [
    "ingest_local_file",
    "IngestionError",
    "DEFAULT_ALLOWED_ROOTS",
    "chunk_document",
]
