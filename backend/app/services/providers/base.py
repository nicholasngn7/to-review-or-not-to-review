"""Review provider interface.

A `ReviewProvider` turns a parsed diff into per-persona reviews. The mock
provider implements this with deterministic heuristics; a future Bedrock/OpenAI/
Anthropic provider would implement the same method by calling a model.

The review engine (`app.services.review_engine`) owns aggregation (overall risk,
merge recommendation, summary, diff stats) so every provider only has to produce
`PersonaReview` objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.models.diff import ParsedDiff
from app.models.enums import ReviewerPersona
from app.models.review import PersonaReview


class ReviewProvider(ABC):
    """Produces per-persona reviews for a parsed diff."""

    #: Stable provider identifier, e.g. "mock" or "bedrock".
    name: str = "base"

    @abstractmethod
    def review(
        self,
        parsed_diff: ParsedDiff,
        selected_personas: list[ReviewerPersona],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> list[PersonaReview]:
        """Return one `PersonaReview` per selected persona, in the given order.

        Implementations should not aggregate across personas; the review engine
        handles overall risk, recommendation, and summary.
        """
        raise NotImplementedError
