"""Persona definitions shared by all review providers."""

from .registry import (
    PERSONA_REGISTRY,
    PersonaSpec,
    get_persona_spec,
    persona_prompt,
)

__all__ = [
    "PERSONA_REGISTRY",
    "PersonaSpec",
    "get_persona_spec",
    "persona_prompt",
]
