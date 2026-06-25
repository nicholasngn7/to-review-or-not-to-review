"""Local-only retrieval API route (v0.4, Phase 4).

`POST /api/retrieve-context` runs the local retrieval service over the project's own
allow-listed docs (`README.md` + `docs/`) and returns ranked `RetrievalResult`s.

Deliberately constrained for safety and honesty:

* the repo root and allow-list are **pinned server-side** (the caller cannot point this
  at arbitrary filesystem paths),
* **no** outbound network, URL fetching, tokens, or OAuth,
* **no** review integration — this never populates `citations`/`contextUsed`.

Similarity is lexical (local hashing embedder), not semantic. This is not production RAG.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.base import CamelModel
from app.models.knowledge import RetrievalQuery, RetrievalResult
from app.services.knowledge import RetrievalError, retrieve_context

router = APIRouter(prefix="/api", tags=["retrieval"])

# Pinned project root: .../<repo>/backend/app/api/routes/retrieve_context.py
# parents[4] is the repository root that contains README.md and docs/.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class RetrieveContextRequest(CamelModel):
    """Local retrieval request: a query plus project-relative doc paths."""

    query: RetrievalQuery
    source_paths: list[str] = []


class RetrieveContextResponse(CamelModel):
    """Ranked retrieval results plus any non-fatal warnings."""

    results: list[RetrievalResult] = []
    warnings: list[str] = []


@router.post("/retrieve-context", response_model=RetrieveContextResponse)
def post_retrieve_context(payload: RetrieveContextRequest) -> RetrieveContextResponse:
    """Retrieve locally relevant doc chunks. Local-only, allow-listed, no network."""
    warnings: list[str] = []
    if not payload.source_paths:
        warnings.append("No sourcePaths provided; nothing to retrieve.")
        return RetrieveContextResponse(results=[], warnings=warnings)

    try:
        results = retrieve_context(
            payload.query,
            source_paths=list(payload.source_paths),
            repo_root=_REPO_ROOT,
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RetrieveContextResponse(results=results, warnings=warnings)
