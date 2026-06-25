# Project case study — MR Review Council

A neutral engineering overview of *MR Review Council* (repo:
`to-review-or-not-to-review`): what it does, the architecture and the decisions
behind it, how it is tested and demoed, and where its boundaries are. For the
detailed flow and decision log, see [`architecture.md`](architecture.md) and
[`decisions.md`](decisions.md).

## Overview

MR Review Council turns a unified diff into a structured, multi-perspective code
review. Seven specialized personas — Architect, QA, Security, Frontend, Backend,
SRE, and Product — each produce findings that aggregate into one overall risk level
and a merge recommendation, exportable as Markdown for an MR/PR comment.

The project is **local-first**: review generation runs through a deterministic,
offline mock provider behind a `ReviewProvider` abstraction, so the full
diff → review → verdict flow is exercised end to end without external services. It
is delivered in three runnable, tagged milestones: `v0.1.0`, `v0.2.0`, and `v0.3.0`.

## Architecture and key decisions

- **Contract-first boundary.** Pydantic v2 models are the source of truth and
  serialize to camelCase JSON mirrored by TypeScript types, so the frontend/backend
  contract is explicit and type-safe.
- **Separation of concerns.** A pure unified-diff parser produces structured
  files/hunks/lines/stats; a review engine only aggregates; providers only produce
  per-persona reviews; import mappers are pure functions. Each piece is small and
  independently testable.
- **Provider abstraction.** All review generation sits behind a single
  `ReviewProvider.review(...)` method, selected by the `REVIEW_PROVIDER` environment
  variable through a validating factory. The default is a deterministic mock; a
  `bedrock` placeholder returns an explicit `501` rather than fabricating a review,
  marking exactly where a real model would integrate.
- **Centralized persona knowledge.** Persona focus, output expectations, and
  severity guidance live once in a registry, so the mock provider and any future
  provider build from the same source of truth.
- **Normalized comment-thread contract.** Existing discussions are represented by a
  single comment-thread shape. Whether a thread is entered locally or normalized from
  provider-shaped JSON, it flows through the same review/reply path; the engine does
  not depend on where the data came from.

## Milestones

- **v0.1.0 — core review.** Unified-diff parsing, the multi-persona mock review
  engine, the aggregated verdict (risk + merge recommendation), the results
  dashboard (reviewer tabs, severity filters, finding cards), and client-side
  Markdown export.
- **v0.2.0 — reviewer tone and suggested replies.** Tone profiles that change the
  wording and framing of feedback only (never findings, severities, overall risk, or
  the recommendation; the default voice is an exact no-op), plus deterministic,
  copy-only suggested replies for existing comment threads, routed to relevant
  personas and included in the Markdown export.
- **v0.3.0 — local fixture-based comment import.** Pure mappers that normalize
  provider-shaped GitHub/GitLab comment JSON (GitHub PR review comments, GitHub PR
  issue comments, GitLab MR discussions) into the comment-thread contract, a
  local-only `POST /api/import-comments` endpoint, and a frontend import panel driven
  by bundled synthetic sample payloads.

## Testing

- **Backend (pytest):** unified-diff parser, review engine, providers, routes, tone
  rendering, suggested-reply generation, and the Git-import mappers/orchestrator,
  including fixture-based mapper tests.
- **Invariance tests** assert that imported threads drive the review/reply pipeline
  identically to locally-entered threads, pinning down "import is a pure input
  adapter" as an enforced property.
- **Frontend (Vitest + React Testing Library):** components, API client behavior,
  Markdown export, and import-panel normalization.
- **Type checking + build:** `tsc -b` and `vite build`.

## Demo automation

Screenshots and short videos are captured from the running app by Playwright specs
under `frontend/demo/`, using only built-in sample diffs and bundled synthetic
import payloads. For exact-version assets, the historical app is started from its tag
worktree and the current harness is pointed at it via the `DEMO_BASE_URL` environment
variable (older tags predate the demo scripts). See
[`../frontend/demo/README.md`](../frontend/demo/README.md) and
[`demo-automation-plan.md`](demo-automation-plan.md) for the workflow.

## Limitations and out of scope

These are current, intentional boundaries:

- **Deterministic mock, not AI.** Findings come from deterministic heuristics; the
  app does not call an LLM and does not "understand" code. `REVIEW_PROVIDER=bedrock`
  is a placeholder that returns a `501`.
- **No live GitHub/GitLab integration.** Diffs and comments are pasted, uploaded, or
  loaded from bundled synthetic samples — there is no API fetch, no OAuth, and no
  token handling. Provider-shaped payloads are synthetic and local.
- **No comment posting.** Suggested replies are copy-only; nothing is posted back to
  a PR/MR.
- **No persistence.** Reviews are computed on demand; there is no database. Markdown
  export is the way to keep a result.
- **No production deployment.** The project runs locally; it is not hosted and has no
  users.

A real `BedrockReviewProvider`, live provider fetching of diffs/comments, persistence,
and deployment are future work behind the existing seams — see
[`future-git-provider-import.md`](future-git-provider-import.md) and
[`future-git-provider-comment-import.md`](future-git-provider-comment-import.md).

## Planned work

- **v0.4 — RAG-style grounded review context (in progress).** A design plan to ingest
  selected local docs, chunk and embed them behind an embedding-provider abstraction (a
  deterministic local provider first), retrieve relevant context before a review, and
  attach citations to findings. So far the **contract models** (Phase 1A), **additive
  review-contract fields** (Phase 1B), **local offline ingestion + deterministic
  chunking** (Phase 2), a **deterministic local lexical embedding provider + in-memory
  cosine index** (Phase 3), a **local-only retrieval service + `POST
  /api/retrieve-context` endpoint** (Phase 4), and **opt-in, provenance-only review
  grounding** (Phase 5 — populating `contextUsed` and per-finding `citations` by lexical
  overlap, with detection/risk/recommendation kept invariant), **offline retrieval
  evaluation fixtures + regression metrics** (Phase 6 — deterministic hit@k/precision@k/
  recall@k over a fixed synthetic corpus), and **frontend visibility for opt-in grounding**
  (Phase 7 — an optional local context-sources input, a read-only “Retrieved local context”
  panel, secondary per-finding “Cited context”, and an optional Markdown “Context used”
  block, all hidden when absent and worded as local/lexical/provenance-only) are implemented
  and tested. It is scoped as a local **RAG architecture
  demo** with lexical/deterministic retrieval — not semantic search, not production-grade
  RAG, and with no live/Bedrock embedding calls unless a real provider is later
  implemented and tested. Full plan:
  [`v0.4-plan-rag-grounded-review.md`](v0.4-plan-rag-grounded-review.md).
