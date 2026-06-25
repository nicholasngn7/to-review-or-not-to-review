# Architecture

MR Review Council is a multi-persona AI merge-request reviewer. This document
captures the high-level design that the incremental build follows.

## System overview

```text
Frontend (React/TS/Vite)            Backend (FastAPI/Pydantic)
┌───────────────────────┐           ┌────────────────────────────────────┐
│ MR input + personas   │  POST     │ /api/reviews                       │
│ Risk / summary / tabs │ ───/api──►│   diff_parser                      │
│ Finding cards         │           │   review_engine (aggregation)      │
│ Export to Markdown    │ ◄──JSON── │     create_provider(REVIEW_PROVIDER)│
└───────────────────────┘           │       ReviewProvider (interface)   │
                                     │         MockReviewProvider (default)│
                                     │         BedrockReviewProvider (stub)│
                                     │   personas/registry (PersonaSpec)  │
                                     └────────────────────────────────────┘
```

The frontend posts a diff plus the selected personas. The backend parses the
unified diff into files/hunks/lines, asks the configured `ReviewProvider` for one
`PersonaReview` per persona, and aggregates a structured response (overall risk,
merge recommendation, summary, per-persona findings).

## Extensibility seam

All review generation lives behind a `ReviewProvider` interface
(`app/services/providers/base.py`):

```python
review(parsed_diff, selected_personas, title=None, description=None) -> list[PersonaReview]
```

- **`MockReviewProvider` (default).** Deterministic heuristics so the full
  product flow works offline with no credentials or paid API calls.
- **`BedrockReviewProvider` (placeholder).** The seam for a future Amazon
  Bedrock model. It does not import boto3 or call AWS; if selected it raises
  `NotImplementedError`, surfaced by the API as a clear `501`.

The provider is chosen by the `REVIEW_PROVIDER` env var (`mock` | `bedrock`,
default `mock`) via `create_provider()`, which validates the value and fails
fast on anything unknown. Aggregation, the API contract, and the UI are all
provider-independent.

Persona knowledge (display name, review focus, output expectations, severity
guidance) lives once in `app/personas/registry.py` so both the mock provider and
a future LLM provider build from the same source of truth.

Real AI calls are **intentionally deferred**: it keeps the MVP free to run, avoids
requiring AWS credentials, and lets the architecture (the seam) be proven before
spending on tokens.

## Key data models (planned)

- **Enums:** `Persona`, `RiskLevel`, `MergeRecommendation`, `Severity`
- **Diff:** `DiffLine`, `Hunk`, `DiffFile`, `ParsedDiff`
- **Review:** `ReviewRequest`, `Finding`, `PersonaReview`, `ReviewResponse`

The Pydantic models on the backend are the source of truth; the frontend mirrors
them in TypeScript.

## Implementation phases

1. **Backend foundation** — FastAPI skeleton, enums + diff models, diff parser, `/health`.
2. **Review engine** — provider interface, mock provider, aggregation, `POST /api/review`.
3. **Frontend foundation** — TS types, API client, MR input panel, persona selector.
4. **Results UI** — summary, risk badge, reviewer tabs, finding cards.
5. **Export + polish** — Markdown export, loading/error states, docs.

## Current status

Scaffold complete: monorepo structure, backend `/health`, and a landing page.
No AI integration yet.
