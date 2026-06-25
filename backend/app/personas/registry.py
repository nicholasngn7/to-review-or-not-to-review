"""Persona registry: the single source of truth for reviewer personas.

Each persona is described declaratively (focus, output expectations, severity
guidance). This registry is provider-agnostic:

- The **mock provider** uses it for display names, summaries, and to guarantee a
  heuristic handler exists for every registered persona.
- A future **LLM provider** (Bedrock / OpenAI / Anthropic) can turn each
  `PersonaSpec` into a system/instruction prompt via `persona_prompt()` without
  duplicating persona knowledge.

Keep the persona ids in sync with `app.models.enums.ReviewerPersona` and
`frontend/src/lib/reviewLabels.ts`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import ReviewerPersona


@dataclass(frozen=True)
class PersonaSpec:
    """Declarative description of a reviewer persona."""

    id: ReviewerPersona
    display_name: str
    description: str
    review_focus: tuple[str, ...] = field(default_factory=tuple)
    output_expectations: str = ""
    severity_guidance: str = ""


PERSONA_REGISTRY: dict[ReviewerPersona, PersonaSpec] = {
    ReviewerPersona.ARCHITECT: PersonaSpec(
        id=ReviewerPersona.ARCHITECT,
        display_name="Architect",
        description="Guards structure, boundaries, and long-term maintainability.",
        review_focus=(
            "MR scope and size",
            "Coupling across layers (frontend/backend/config)",
            "Separation of concerns and module boundaries",
        ),
        output_expectations=(
            "Flag MRs that are too large or mix unrelated concerns, and call out "
            "risky cross-layer coupling. Prefer a few high-signal findings over noise."
        ),
        severity_guidance=(
            "medium: large change sets, many files, or frontend+backend coupling; "
            "low: mixing multiple concerns in one MR."
        ),
    ),
    ReviewerPersona.QA: PersonaSpec(
        id=ReviewerPersona.QA,
        display_name="QA / Test",
        description="Protects against regressions and gaps in test coverage.",
        review_focus=(
            "Whether production changes ship with tests",
            "Deleted or weakened tests",
            "Edge cases and regression risk",
        ),
        output_expectations=(
            "Identify production code that changes without matching test updates and "
            "any reduction in coverage. Be concrete about what to test."
        ),
        severity_guidance=(
            "high: deleted tests or large untested changes; "
            "medium: production code changed with no test updates."
        ),
    ),
    ReviewerPersona.SECURITY: PersonaSpec(
        id=ReviewerPersona.SECURITY,
        display_name="Security",
        description="Looks for secrets and unsafe patterns introduced by the diff.",
        review_focus=(
            "Hardcoded secrets / tokens / keys",
            "Dangerous calls (eval, shell=True, subprocess)",
            "Insecure transport and unsafe input handling",
        ),
        output_expectations=(
            "Surface added lines that look like secrets or unsafe operations. Treat "
            "findings as leads worth a closer look; note possible false positives."
        ),
        severity_guidance=(
            "high: eval(), shell=True, private keys; "
            "medium: tokens/passwords/secrets; low: insecure http:// URLs."
        ),
    ),
    ReviewerPersona.FRONTEND: PersonaSpec(
        id=ReviewerPersona.FRONTEND,
        display_name="Frontend",
        description="Reviews UI code for correctness, state, and accessibility.",
        review_focus=(
            "Unsafe DOM access / innerHTML",
            "React effect and state pitfalls",
            "Accessibility (e.g. image alt text)",
        ),
        output_expectations=(
            "Comment on risky DOM usage, effect correctness, oversized components, and "
            "a11y gaps in changed frontend files only."
        ),
        severity_guidance=(
            "medium: innerHTML/XSS risk; low: direct DOM manipulation, missing alt "
            "text, large components; info: useEffect changes."
        ),
    ),
    ReviewerPersona.BACKEND: PersonaSpec(
        id=ReviewerPersona.BACKEND,
        display_name="Backend",
        description="Reviews API/service code for validation and robustness.",
        review_focus=(
            "Input validation on handlers",
            "Broad exception handling",
            "Unsafe SQL string construction",
            "Unfinished work (TODO/FIXME)",
        ),
        output_expectations=(
            "Flag broad exception handling, possible SQL injection, and changed "
            "handlers that may lack validation in changed backend files only."
        ),
        severity_guidance=(
            "high: SQL built via string formatting; medium: broad except handlers; "
            "low: TODO/FIXME; info: route/handler changes to double-check."
        ),
    ),
    ReviewerPersona.SRE: PersonaSpec(
        id=ReviewerPersona.SRE,
        display_name="SRE / On-call",
        description="Protects observability and runtime reliability.",
        review_focus=(
            "Removed logging / reduced observability",
            "Network calls without timeouts",
            "Swallowed exceptions",
        ),
        output_expectations=(
            "Call out reduced observability, missing timeouts, and silently swallowed "
            "errors that would hurt on-call debugging."
        ),
        severity_guidance=(
            "medium: removed logging, network calls without timeouts, swallowed "
            "exceptions."
        ),
    ),
    ReviewerPersona.PRODUCT: PersonaSpec(
        id=ReviewerPersona.PRODUCT,
        display_name="Product",
        description="Watches clarity, scope, and user-facing impact.",
        review_focus=(
            "Unfinished work markers (TODO/FIXME)",
            "Changes to user-facing copy/labels",
        ),
        output_expectations=(
            "Highlight incomplete behavior and user-facing text changes that need "
            "product/docs follow-up."
        ),
        severity_guidance=(
            "low: TODO/FIXME markers; info: user-facing copy/label changes."
        ),
    ),
}

# Canonical ordering used wherever personas are iterated for display.
PERSONA_ORDER: tuple[ReviewerPersona, ...] = tuple(PERSONA_REGISTRY.keys())


def get_persona_spec(persona: ReviewerPersona) -> PersonaSpec:
    """Return the spec for a persona, raising if it is somehow unregistered."""
    try:
        return PERSONA_REGISTRY[persona]
    except KeyError:  # pragma: no cover - guards against enum/registry drift
        raise KeyError(f"No persona spec registered for '{persona}'.") from None


def persona_prompt(spec: PersonaSpec) -> str:
    """Render a persona spec into an instruction prompt for an LLM provider.

    Not used by the mock provider, but defined here so a future Bedrock/OpenAI
    provider builds prompts from the same source of truth.
    """
    focus = "\n".join(f"- {item}" for item in spec.review_focus)
    return (
        f"You are the {spec.display_name} reviewer on a merge-request review "
        f"council.\n"
        f"Role: {spec.description}\n\n"
        f"Focus your review on:\n{focus}\n\n"
        f"Output expectations: {spec.output_expectations}\n"
        f"Severity guidance: {spec.severity_guidance}\n"
    )
