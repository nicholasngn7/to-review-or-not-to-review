"""Placeholder Amazon Bedrock review provider.

This is the integration *seam* for a future real LLM provider. It deliberately
does **not** call AWS, import boto3, or read credentials. If selected via
`REVIEW_PROVIDER=bedrock`, it fails loudly so the deferred work is obvious and
the app never silently pretends a model ran.

When implemented, this provider would:
  1. Build a prompt per persona from `app.personas.registry.persona_prompt`.
  2. Send the diff + prompt to a Bedrock model (e.g. Anthropic Claude on Bedrock).
  3. Parse the model output into `ReviewFinding` / `PersonaReview` objects.

Real AI calls are intentionally deferred (no paid API usage, no AWS credentials
required to run locally). See docs/decisions.md.
"""

from __future__ import annotations

from typing import Optional

from app.models.diff import ParsedDiff
from app.models.enums import ReviewerPersona
from app.models.review import PersonaReview
from app.models.tone import ToneProfile

from .base import ReviewProvider

_NOT_IMPLEMENTED_MESSAGE = (
    "The Bedrock review provider is not implemented yet. Real AI/LLM calls are "
    "intentionally deferred. Use the default mock provider by unsetting "
    "REVIEW_PROVIDER or setting REVIEW_PROVIDER=mock."
)


class BedrockReviewProvider(ReviewProvider):
    """Not-yet-implemented provider; raises clearly instead of faking results."""

    name = "bedrock"

    def review(
        self,
        parsed_diff: ParsedDiff,
        selected_personas: list[ReviewerPersona],
        title: Optional[str] = None,
        description: Optional[str] = None,
        tone_profiles: Optional[dict[ReviewerPersona, ToneProfile]] = None,
    ) -> list[PersonaReview]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MESSAGE)
