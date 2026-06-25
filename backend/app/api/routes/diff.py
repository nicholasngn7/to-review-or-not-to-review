"""Diff-related API routes."""

from fastapi import APIRouter

from app.models.base import CamelModel
from app.models.diff import ParsedDiff
from app.services.diff_parser import parse_diff

router = APIRouter(prefix="/api", tags=["diff"])


class ParseDiffRequest(CamelModel):
    """Request body for `POST /api/parse-diff`."""

    diff_text: str


@router.post("/parse-diff", response_model=ParsedDiff)
def parse_diff_endpoint(payload: ParseDiffRequest) -> ParsedDiff:
    """Parse raw unified diff text into the structured `ParsedDiff` model."""
    return parse_diff(payload.diff_text)
