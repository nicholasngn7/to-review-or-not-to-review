"""Review provider registry and factory.

`create_provider()` resolves the configured (or explicitly named) provider and
validates it, so an unknown `REVIEW_PROVIDER` fails with a clear error instead
of silently falling back to the mock.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import get_settings

from .base import ReviewProvider
from .bedrock_provider import BedrockReviewProvider
from .mock_provider import MockReviewProvider

# Registry of known providers keyed by their stable name.
_PROVIDERS: dict[str, type[ReviewProvider]] = {
    MockReviewProvider.name: MockReviewProvider,
    BedrockReviewProvider.name: BedrockReviewProvider,
}


def available_providers() -> list[str]:
    """Sorted list of valid `REVIEW_PROVIDER` values."""
    return sorted(_PROVIDERS)


def create_provider(name: Optional[str] = None) -> ReviewProvider:
    """Instantiate a provider by name, defaulting to the configured one.

    Raises `ValueError` with the valid options if the name is unknown.
    """
    resolved = name if name is not None else get_settings().review_provider
    key = resolved.strip().lower()
    provider_cls = _PROVIDERS.get(key)
    if provider_cls is None:
        raise ValueError(
            f"Unknown review provider '{resolved}'. "
            f"Set REVIEW_PROVIDER to one of: {', '.join(available_providers())}."
        )
    return provider_cls()


__all__ = [
    "ReviewProvider",
    "MockReviewProvider",
    "BedrockReviewProvider",
    "available_providers",
    "create_provider",
]
