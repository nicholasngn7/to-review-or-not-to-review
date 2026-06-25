# Architecture

MR Review Council is a multi-persona AI merge-request reviewer. This document
captures the high-level design that the incremental build follows.

## System overview

```text
Frontend (React/TS/Vite)            Backend (FastAPI/Pydantic)
┌───────────────────────┐           ┌──────────────────────────────┐
│ MR input + personas   │  POST     │ /api/review                  │
│ Risk / summary / tabs │ ───/api──►│   diff_parser                │
│ Finding cards         │           │   review_engine              │
│ Export to Markdown    │ ◄──JSON── │   ReviewProvider (interface) │
└───────────────────────┘           │     MockReviewProvider       │
                                     │     (later) Bedrock/OpenAI   │
                                     └──────────────────────────────┘
```

The frontend posts a diff plus the selected personas. The backend parses the
unified diff into files/hunks/lines, runs each persona through a review provider,
and returns a structured response (overall risk, merge recommendation, summary,
per-persona findings).

## Extensibility seam

All AI behavior lives behind a `ReviewProvider` interface. The MVP ships a
deterministic `MockReviewProvider` driven by simple diff heuristics so the full
product flow works offline. A real provider (Amazon Bedrock, OpenAI, Anthropic)
implements the same interface and is selected via backend config — no API or UI
changes required.

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
