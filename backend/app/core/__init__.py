"""Core application configuration and cross-cutting concerns."""

from .config import DEFAULT_REVIEW_PROVIDER, Settings, get_settings

__all__ = ["DEFAULT_REVIEW_PROVIDER", "Settings", "get_settings"]
