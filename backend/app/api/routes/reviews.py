"""Review API routes."""

from fastapi import APIRouter, HTTPException

from app.models.review import ReviewRequest, ReviewResponse
from app.services.knowledge import RetrievalError
from app.services.review_engine import run_review

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/reviews", response_model=ReviewResponse)
def create_review(payload: ReviewRequest) -> ReviewResponse:
    """Run the selected reviewer personas over a diff and return the review.

    When opt-in `knowledgeSources` are provided but point at unsafe/outside/URL-like
    paths, retrieval raises `RetrievalError`, surfaced here as a clear 400 (consistent
    with the other local-only routes).
    """
    try:
        return run_review(payload)
    except RetrievalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
