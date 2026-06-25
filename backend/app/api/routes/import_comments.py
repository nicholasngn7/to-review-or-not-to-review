"""Local-only Git comment-import API route (v0.3, Phase 6).

`POST /api/import-comments` normalizes a **caller-supplied**, fixture-shaped
GitHub/GitLab comment payload into the existing `CommentThread` contract via the pure
`import_comments(...)` orchestrator. It exists to exercise and demo the normalization
boundary.

Strictly:

* no outbound network I/O (it never contacts GitHub/GitLab),
* no tokens, no OAuth, no URL fetching,
* no posting of comments anywhere.
"""

from fastapi import APIRouter, HTTPException

from app.models.git_import import ImportCommentsRequest, ImportCommentsResponse
from app.services.git_import import import_comments

router = APIRouter(prefix="/api", tags=["import"])


@router.post("/import-comments", response_model=ImportCommentsResponse)
def create_import(payload: ImportCommentsRequest) -> ImportCommentsResponse:
    """Normalize a caller-supplied provider comment payload. Local-only, no network."""
    try:
        return import_comments(payload)
    except ValueError as exc:
        # Unsupported or ambiguous provider/source -> clear 400 (matches API style).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
