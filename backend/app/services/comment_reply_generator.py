"""Deterministic, local suggested-reply generation (Phase 15).

Given existing MR/PR comment threads, this drafts **copy-only** replies a human
can review and send. There is no AI/LLM, no GitHub/GitLab integration, and nothing
is ever posted automatically. Generation is fully deterministic: the same threads,
selected personas, and tone always produce identical replies.

Hard invariant: reply generation must never affect diff parsing, detected
findings, finding ids/severity, overall risk, merge recommendation, diff stats, or
provider selection. It only reads the request and produces `SuggestedReply`
objects appended to the response.
"""

from __future__ import annotations

from typing import Optional

from app.models.comments import CommentThread, SuggestedReply
from app.models.diff import ParsedDiff
from app.models.enums import ReviewerPersona
from app.models.tone import DEFAULT_TONE_PROFILE, ToneProfile
from app.personas.registry import get_persona_spec
from app.services.tone_renderer import ToneRenderer

# Deterministic confidence values (independent of tone).
_MATCH_CONFIDENCE = 0.6
_FALLBACK_CONFIDENCE = 0.3

# Persona keyword routing. Order is significant for deterministic output.
_PERSONA_KEYWORDS: list[tuple[ReviewerPersona, tuple[str, ...]]] = [
    (
        ReviewerPersona.QA,
        ("test", "regression", "coverage", "edge case", "assert"),
    ),
    (
        ReviewerPersona.SECURITY,
        ("auth", "token", "secret", "security", "permission", "password",
         "injection", "vulnerab"),
    ),
    (
        ReviewerPersona.BACKEND,
        ("exception", "validation", "validate", "api", "endpoint", "python",
         "service", "backend", "query", "database"),
    ),
    (
        ReviewerPersona.SRE,
        ("logging", "log", "timeout", "retry", "on-call", "oncall", "failure",
         "observability", "metric"),
    ),
    (
        ReviewerPersona.FRONTEND,
        ("component", "ui", "accessibility", "a11y", "react", "css", "render"),
    ),
    (
        ReviewerPersona.ARCHITECT,
        ("scope", "boundary", "architecture", "coupling", "design",
         "abstraction"),
    ),
    (
        ReviewerPersona.PRODUCT,
        ("wording", "ux", "acceptance criteria", "customer", "user impact",
         "copy", "docs"),
    ),
]

# Persona-flavored reply body: (stance, concrete next step / clarification).
_PERSONA_REPLY: dict[ReviewerPersona, tuple[str, str]] = {
    ReviewerPersona.QA: (
        "agreed this needs test coverage",
        "could we add a regression test for this case before merging?",
    ),
    ReviewerPersona.SECURITY: (
        "this looks security-sensitive",
        "can we confirm secrets/permissions are handled safely and nothing is "
        "exposed?",
    ),
    ReviewerPersona.BACKEND: (
        "the service-side handling is worth tightening",
        "could we catch the specific exception and validate inputs explicitly?",
    ),
    ReviewerPersona.SRE: (
        "operational visibility matters here",
        "can we add structured logging (and a timeout/retry where relevant) so "
        "failures stay observable?",
    ),
    ReviewerPersona.FRONTEND: (
        "the UI/component impact is worth a look",
        "could we verify accessibility and state handling for this change?",
    ),
    ReviewerPersona.ARCHITECT: (
        "there may be a boundary/coupling concern",
        "can we confirm this stays within the intended module boundary?",
    ),
    ReviewerPersona.PRODUCT: (
        "this touches user-facing behavior",
        "could we confirm the wording/acceptance criteria with product?",
    ),
}


def _thread_text(thread: CommentThread) -> str:
    return " ".join(c.body for c in thread.comments).lower()


def _matched_keyword(text: str, persona: ReviewerPersona) -> Optional[str]:
    for _persona, keywords in _PERSONA_KEYWORDS:
        if _persona != persona:
            continue
        for kw in keywords:
            if kw in text:
                return kw
    return None


def _relevant_personas(
    text: str, selected: list[ReviewerPersona]
) -> list[tuple[ReviewerPersona, str]]:
    """Selected personas whose keywords appear in the thread, in routing order."""
    matches: list[tuple[ReviewerPersona, str]] = []
    for persona, keywords in _PERSONA_KEYWORDS:
        if persona not in selected:
            continue
        for kw in keywords:
            if kw in text:
                matches.append((persona, kw))
                break
    return matches


def _fallback_persona(
    selected: list[ReviewerPersona],
) -> Optional[ReviewerPersona]:
    if ReviewerPersona.PRODUCT in selected:
        return ReviewerPersona.PRODUCT
    if ReviewerPersona.ARCHITECT in selected:
        return ReviewerPersona.ARCHITECT
    return selected[0] if selected else None


def _reply_body(persona: ReviewerPersona, author: Optional[str]) -> str:
    stance, next_step = _PERSONA_REPLY[persona]
    label = get_persona_spec(persona).display_name
    thanks = "Thanks for the review comment"
    if author:
        thanks = f"Thanks for the review comment, {author}"
    return (
        f"{thanks}. From a {label} standpoint, {stance} — {next_step} "
        "(Draft suggestion; please review before sending.)"
    )


def _make_reply(
    thread: CommentThread,
    persona: ReviewerPersona,
    *,
    matched_keyword: Optional[str],
    tone: ToneProfile,
) -> SuggestedReply:
    label = get_persona_spec(persona).display_name
    author = thread.comments[0].author if thread.comments else None

    body = _reply_body(persona, author)
    rendered = ToneRenderer(tone, persona).render_reply(body)

    if matched_keyword:
        rationale = (
            f"The comment mentions \"{matched_keyword}\", which maps to the "
            f"{label} reviewer."
        )
        confidence = _MATCH_CONFIDENCE
    else:
        rationale = (
            "No persona-specific keywords matched; routing to the "
            f"{label} reviewer as a sensible default."
        )
        confidence = _FALLBACK_CONFIDENCE

    return SuggestedReply(
        id=f"reply-{thread.id}-{persona.value}",
        thread_id=thread.id,
        reviewer=persona,
        suggested_reply=rendered,
        rationale=rationale,
        confidence=confidence,
        needs_human_review=True,
        tone_profile=tone,
    )


def generate_suggested_replies(
    parsed_diff: ParsedDiff,
    comment_threads: Optional[list[CommentThread]],
    selected_personas: list[ReviewerPersona],
    tone_profiles: Optional[dict[ReviewerPersona, ToneProfile]] = None,
) -> list[SuggestedReply]:
    """Draft copy-only replies for each comment thread.

    Returns an empty list when there are no threads or no selected personas.
    ``parsed_diff`` is accepted for future use (e.g. confirming a file changed)
    but never alters detection.
    """
    if not comment_threads or not selected_personas:
        return []

    tone_profiles = tone_profiles or {}
    replies: list[SuggestedReply] = []

    for thread in comment_threads:
        text = _thread_text(thread)
        matches = _relevant_personas(text, selected_personas)

        if matches:
            for persona, keyword in matches:
                tone = tone_profiles.get(persona) or DEFAULT_TONE_PROFILE
                replies.append(
                    _make_reply(
                        thread, persona, matched_keyword=keyword, tone=tone
                    )
                )
        else:
            persona = _fallback_persona(selected_personas)
            if persona is None:
                continue
            tone = tone_profiles.get(persona) or DEFAULT_TONE_PROFILE
            replies.append(
                _make_reply(thread, persona, matched_keyword=None, tone=tone)
            )

    return replies
