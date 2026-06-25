"""Backend services for MR Review Council."""

from .diff_parser import parse_diff
from .review_engine import run_review

__all__ = ["parse_diff", "run_review"]
