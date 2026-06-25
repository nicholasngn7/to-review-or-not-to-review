"""Reviewer tone profile contract (v0.2 groundwork).

A `ToneProfile` configures *how* a reviewer communicates — wording, explanation
style, and recommendation framing. Per the v0.2 architectural rule, tone is
presentation only: it must never change which findings are detected, their
severity, the overall risk, the merge recommendation, diff parsing, or provider
selection.

Phase 12 adds the models and resolution helper only. No wording is changed yet;
the review engine accepts these fields and ignores them for now (fully
backward-compatible).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import Field

from .base import CamelModel
from .enums import ReviewerPersona

if TYPE_CHECKING:  # avoid a runtime import cycle (review.py imports tone.py)
    from .review import ReviewRequest


class ToneStyle(str, Enum):
    """The communication style a reviewer adopts."""

    DIRECT = "direct"
    SUPPORTIVE = "supportive"
    EDUCATIONAL = "educational"
    STRICT = "strict"
    CURIOUS = "curious"
    EXECUTIVE = "executive"


class ToneStrictness(str, Enum):
    """How forcefully recommendations are framed (framing only, not severity)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToneVerbosity(str, Enum):
    """How much explanatory detail the wording includes."""

    BRIEF = "brief"
    NORMAL = "normal"
    DETAILED = "detailed"


class ToneProfile(CamelModel):
    """A reviewer's communication style. Presentation/framing only."""

    style: ToneStyle = Field(default=ToneStyle.DIRECT)
    strictness: ToneStrictness = Field(default=ToneStrictness.MEDIUM)
    verbosity: ToneVerbosity = Field(default=ToneVerbosity.NORMAL)
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional free-form wording guidance. Affects phrasing only.",
    )


# The default tone applied when neither a per-persona nor a global profile is set.
DEFAULT_TONE_PROFILE = ToneProfile()


def resolve_tone_profile(
    persona: ReviewerPersona, request: "ReviewRequest"
) -> ToneProfile:
    """Resolve the effective tone for a persona.

    Resolution order: per-persona override -> global `tone_profile` -> default.
    This is intentionally behavior-neutral in Phase 12 (callers may compute it but
    it does not yet alter wording).
    """
    overrides = request.persona_tone_profiles
    if overrides and persona in overrides:
        return overrides[persona]
    if request.tone_profile is not None:
        return request.tone_profile
    return DEFAULT_TONE_PROFILE
