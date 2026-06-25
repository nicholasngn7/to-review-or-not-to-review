"""Review API routes."""

from fastapi import APIRouter

from app.models.review import ReviewRequest, ReviewResponse
from app.services.review_engine import run_review

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/reviews", response_model=ReviewResponse)
def create_review(payload: ReviewRequest) -> ReviewResponse:
    """Run the selected reviewer personas over a diff and return the review."""
    return run_review(payload)
