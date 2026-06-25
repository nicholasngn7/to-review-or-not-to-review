"""Local-only retrieval service (v0.4, Phase 4).

`retrieve_context(...)` composes the earlier phases end to end —
ingest (allow-listed) → chunk → build an in-memory index → cosine search — and returns
`RetrievalResult`s. It is a thin, deterministic orchestrator with **no persistence** and
**no hidden global state**: each call builds a fresh index.

Strictly offline and local:

* no network, no URL fetching (URL-like inputs are rejected, never fetched),
* no tokens, no OAuth,
* no neural/semantic models (similarity is lexical via the Phase 3 local embedder),
* **no review integration** — this never touches `review_engine`, and never populates
  `ReviewFinding.citations` or `ReviewResponse.context_used`.

See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from app.models.knowledge import (
    KnowledgeSourceType,
    RetrievalQuery,
    RetrievalResult,
)

from .chunking import chunk_document
from .embedding import EmbeddingProvider
from .index import build_index
from .ingestion import IngestionError, ingest_local_file

PathLike = Union[str, Path]

# A conservative "looks like a URL / remote ref" guard. We never fetch — these inputs
# are rejected so it's obvious the service is local-files-only.
_URL_LIKE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
_REMOTE_PREFIXES = ("git@", "ssh://", "//")


class RetrievalError(ValueError):
    """Raised when retrieval cannot proceed (bad/outside/URL-like/missing source)."""


def _looks_url_like(raw: str) -> bool:
    candidate = raw.strip()
    if _URL_LIKE_RE.match(candidate):
        return True
    return candidate.startswith(_REMOTE_PREFIXES)


def retrieve_context(
    query: RetrievalQuery,
    *,
    source_paths: list[PathLike],
    repo_root: PathLike | None = None,
    allowed_roots: list[PathLike] | None = None,
    provider: EmbeddingProvider | None = None,
    max_chars: int = 1200,
    source_type: KnowledgeSourceType = KnowledgeSourceType.REPO_DOC,
) -> list[RetrievalResult]:
    """Retrieve locally relevant chunks for `query` from allow-listed `source_paths`.

    Ingests each path (enforcing the ingestion allow-list / traversal / binary checks),
    chunks each document, builds a fresh in-memory index, and runs cosine search.
    Deterministic: identical files + query yield identical, identically ordered results.

    Args:
        query: The retrieval query (text, `top_k`, optional `filters`).
        source_paths: Local files to ingest (absolute or relative to `repo_root`).
        repo_root: Root that relative paths / `allowed_roots` resolve against.
        allowed_roots: Allow-listed roots (defaults to ingestion's `README.md` + `docs/`).
        provider: Embedding provider to reuse (defaults to the deterministic local one).
        max_chars: Max chunk size passed to chunking.
        source_type: Source type tag applied to ingested documents.

    Returns:
        A list of `RetrievalResult` (possibly empty for empty inputs / low-signal query).

    Raises:
        RetrievalError: if a path is URL-like, outside the allow-list, missing, a
            directory, or otherwise not ingestible as local text.
    """
    chunks = []
    for raw_path in source_paths:
        as_str = str(raw_path)
        if _looks_url_like(as_str):
            raise RetrievalError(
                f"URL-like sources are not supported (local files only): {as_str!r}."
            )
        try:
            document = ingest_local_file(
                raw_path,
                repo_root=repo_root,
                allowed_roots=allowed_roots,
                source_type=source_type,
            )
        except IngestionError as exc:
            # Re-wrap as a service-level error with a stable, clear type.
            raise RetrievalError(str(exc)) from exc
        chunks.extend(chunk_document(document, max_chars=max_chars))

    index = build_index(chunks, provider=provider)
    return index.search(query)
