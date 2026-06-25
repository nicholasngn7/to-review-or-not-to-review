"""Application configuration.

Settings are read from the environment at call time (no caching) so tests and
local runs can override them with `monkeypatch.setenv` / a shell export without
restarting a long-lived process.

The only setting today is which review provider backs `POST /api/reviews`:

    REVIEW_PROVIDER=mock      # default, fully offline deterministic provider
    REVIEW_PROVIDER=bedrock   # placeholder seam for a future Amazon Bedrock provider

Validation of the value lives in the provider factory
(`app.services.providers.create_provider`) so an unknown value fails with a
clear, actionable error instead of silently falling back.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_REVIEW_PROVIDER = "mock"

# Environment variable name, exported for docs/tests to reference in one place.
REVIEW_PROVIDER_ENV = "REVIEW_PROVIDER"


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    review_provider: str


def get_settings() -> Settings:
    """Build a `Settings` snapshot from the current environment."""
    raw = os.getenv(REVIEW_PROVIDER_ENV, DEFAULT_REVIEW_PROVIDER)
    normalized = raw.strip().lower() or DEFAULT_REVIEW_PROVIDER
    return Settings(review_provider=normalized)
