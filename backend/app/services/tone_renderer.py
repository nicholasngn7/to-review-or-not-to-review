"""Deterministic tone rendering for the mock provider (Phase 13A).

Tone is **presentation only**. This renderer rewords/reframes three text fields:

* a finding's ``explanation``
* a finding's ``recommendation``
* a persona's ``summary``

It must never touch detection outputs (finding ids, reviewer, severity, file
path, hunk reference, confidence, title) or any aggregate (overall risk, merge
recommendation, diff stats, provider selection).

Determinism: given the same `ToneProfile`, persona, and input text, the output is
always identical. There is no NLG/LLM here -- just fixed, table-driven framing.

Backward compatibility: the default profile (``direct`` / ``medium`` / ``normal``
with no custom instructions) is an exact no-op, so existing output is unchanged.
"""

from __future__ import annotations

from app.models.enums import ReviewerPersona
from app.models.tone import (
    ToneProfile,
    ToneStrictness,
    ToneStyle,
    ToneVerbosity,
)
from app.personas.registry import get_persona_spec

# Style sets the leading framing. ``direct`` is the baseline (no prefix) so the
# default profile renders identically to the pre-tone output. Each non-direct
# style has a distinct, deterministic prefix.
_STYLE_PREFIX: dict[ToneStyle, str] = {
    ToneStyle.DIRECT: "",
    ToneStyle.SUPPORTIVE: "To keep things smooth: ",
    ToneStyle.EDUCATIONAL: "For context: ",
    ToneStyle.STRICT: "Required before merge: ",
    ToneStyle.CURIOUS: "Open question: ",
    ToneStyle.EXECUTIVE: "Business impact: ",
}

# Strictness adjusts emphasis on the *recommendation* only (never severity).
# ``medium`` is the baseline (no change).
_STRICTNESS_SUFFIX: dict[ToneStrictness, str] = {
    ToneStrictness.LOW: " (lower priority)",
    ToneStrictness.MEDIUM: "",
    ToneStrictness.HIGH: " This should be resolved before merge.",
}


def _first_sentence(text: str) -> str:
    """Return the first sentence of ``text`` (used for brief verbosity)."""
    stripped = text.strip()
    for i, ch in enumerate(stripped):
        if ch == "." and (i + 1 >= len(stripped) or stripped[i + 1] == " "):
            return stripped[: i + 1]
    return stripped


class ToneRenderer:
    """Applies a `ToneProfile` to a single persona's text fields."""

    def __init__(self, tone: ToneProfile, persona: ReviewerPersona) -> None:
        self.tone = tone
        self.persona = persona

    @property
    def _label(self) -> str:
        return get_persona_spec(self.persona).display_name

    def render_explanation(self, text: str) -> str:
        """Verbosity controls explanation detail (not which findings exist)."""
        if self.tone.verbosity == ToneVerbosity.BRIEF:
            return _first_sentence(text)
        if self.tone.verbosity == ToneVerbosity.DETAILED:
            return (
                f"{text} (Flagged by the {self._label} reviewer; verify against "
                "the referenced lines in context.)"
            )
        return text

    def render_recommendation(self, text: str) -> str:
        """Style framing + strictness emphasis applied to the suggested action."""
        prefix = _STYLE_PREFIX[self.tone.style]
        suffix = _STRICTNESS_SUFFIX[self.tone.strictness]
        return f"{prefix}{text}{suffix}"

    def render_summary(self, text: str) -> str:
        """Style framing applied to the persona summary, plus any custom note."""
        prefix = _STYLE_PREFIX[self.tone.style]
        rendered = f"{prefix}{text}"
        custom = (self.tone.custom_instructions or "").strip()
        if custom:
            rendered = f"{rendered} [reviewer note: {custom}]"
        return rendered
