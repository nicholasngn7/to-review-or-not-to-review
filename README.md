# To Review or Not To Review

> **Product / demo name:** MR Review Council — a multi-persona merge-request review assistant.

MR Review Council reviews a Git merge-request / pull-request diff through several
distinct engineering perspectives — **Architect, QA, Security, Frontend, Backend,
SRE, and Product** — and returns a structured review: an overall risk level, a
merge recommendation, and per-persona findings you can filter, read, and export
to Markdown.

The entire MVP runs **locally with no AWS credentials and no paid APIs**. Reviews
are produced by a deterministic *mock* provider that sits behind a clean,
pluggable interface, so a real Amazon Bedrock / OpenAI / Anthropic provider can
drop in later **without changing the API or the UI**.

---

## Why this project exists

Code review is where a lot of engineering judgment lives, but a single reviewer
rarely holds every lens at once — security, testing, reliability, architecture,
product. This project explores what an automated "review council" could look
like: many specialized reviewers over one diff, each with a clear focus, rolled
up into a single risk/recommendation verdict.

It's also a deliberate portfolio piece. The goal was to design the *architecture*
of an AI-assisted reviewer — a clean diff → review → aggregation pipeline behind a
provider seam — and prove the full product flow end to end **before** spending a
cent on tokens or standing up cloud infrastructure. The mock provider keeps the
app free, fast, deterministic, and easy for anyone to clone and run.

## Key features

- **Multi-persona review** — 7 reviewer personas, each with its own focus,
  output expectations, and severity guidance (`backend/app/personas/registry.py`).
- **Real unified-diff parsing** — raw `diff`/`patch` text → structured files /
  hunks / lines / stats (`backend/app/services/diff_parser.py`).
- **Deterministic mock review engine** — credible, repeatable findings from
  heuristics; no AI, no flakiness.
- **Aggregated verdict** — overall risk level + a merge recommendation
  (`ready` → `needs human review`) derived from all findings.
- **Pluggable provider interface** — `REVIEW_PROVIDER` selects the backend;
  a Bedrock placeholder shows exactly where a real model plugs in.
- **Polished review dashboard** — risk/recommendation badges, diff stats,
  reviewer tabs, severity filters, and detailed finding cards.
- **Diff input three ways** — paste, upload a `.diff`/`.patch`, or load a
  built-in demo sample.
- **Markdown export** — download the full review as a clean `.md` report to paste
  into a GitLab MR / GitHub PR comment.
- **Tested** — backend parser/engine/provider/route tests; type-checked frontend.

## Tech stack

- **Frontend:** React + TypeScript + Vite (plain CSS, no UI framework)
- **Backend:** Python + FastAPI + Pydantic v2
- **Tests:** pytest (backend), `tsc` type-check + `vite build` (frontend)
- **Future / designed-for:** AWS (Amazon Bedrock for reviews; API Gateway/Lambda
  or ECS for hosting; DynamoDB + S3 for persistence)

## Architecture overview

```text
Frontend (React/TS/Vite)                 Backend (FastAPI/Pydantic)
┌─────────────────────────┐  POST /api   ┌────────────────────────────────────────┐
│ Diff input (paste/upload │ ──/reviews─► │ diff_parser   → ParsedDiff             │
│   /demo) + persona pick  │              │ review_engine → aggregates results     │
│ Risk/verdict dashboard   │ ◄──JSON───── │   create_provider(REVIEW_PROVIDER)     │
│ Tabs · filters · cards   │              │     ReviewProvider (interface)         │
│ Export to Markdown       │              │       MockReviewProvider  (default)    │
└─────────────────────────┘              │       BedrockReviewProvider (placeholder)│
                                          │ personas/registry → PersonaSpec(s)     │
                                          └────────────────────────────────────────┘
```

The frontend POSTs a diff plus the selected personas. The backend parses the
unified diff, asks the configured `ReviewProvider` for one review per persona,
and aggregates a structured response (overall risk, merge recommendation,
summary, diff stats, per-persona findings, flattened findings). The API contract
is identical regardless of which provider runs.

See [`docs/architecture.md`](docs/architecture.md) for the detailed flow and a
Mermaid diagram, and [`docs/decisions.md`](docs/decisions.md) for the decision
log.

### Repository layout

```text
.
├── backend/    # FastAPI app: parser, review engine, providers, personas, tests
├── frontend/   # React + TypeScript + Vite app
├── docs/       # Architecture, decisions, review contract, samples
└── README.md
```

## Local setup

You need **Node.js 18+** and **Python 3.11+** installed.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is then available at `http://localhost:8000` (health check:
`http://localhost:8000/health`, interactive docs: `http://localhost:8000/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` to the backend
at `http://localhost:8000`.

### API endpoints

| Method | Path              | Description                                    |
| ------ | ----------------- | ---------------------------------------------- |
| GET    | `/health`         | Liveness probe, returns `{"status":"ok"}`      |
| POST   | `/api/parse-diff` | Parse unified diff text into a `ParsedDiff`     |
| POST   | `/api/reviews`    | Run selected personas, return a `ReviewResponse` |

## Demo walkthrough

The app ships with built-in sample diffs so you can show it off without a real
merge request.

1. Start the backend and frontend (see [Local setup](#local-setup)).
2. Open `http://localhost:5173`. In the **Merge request** panel, use **Load a
   demo diff** (marked *sample data*) and pick a sample. It fills in the title,
   description, diff, and a recommended set of personas — **nothing runs
   automatically**.
3. Click **Run Review**.

Which sample to use:

- **Low-risk frontend change** — a small React component tweak *with* a matching
  test update. Produces a mostly clean review (good for showing the "looks clean"
  states and a `ready` recommendation).
- **Risky backend auth change** — a Python auth endpoint with secret handling,
  `eval`/`subprocess`/`shell=True`, a swallowed exception, a no-timeout network
  call, and no tests. Triggers Security (incl. high), QA, Backend, and SRE
  findings and a `needs human review` recommendation.
- **Mixed full-stack change** — touches frontend, backend, config, and docs in
  one MR. Triggers Architect (scope/boundaries) and Product/QA feedback.

Then explore the results: switch **reviewer tabs**, apply **severity filters**,
read the finding cards, and click **Export Markdown**. The paste-your-own and
`.diff`/`.patch` upload workflows work exactly the same way.

## Demo video

> _A recorded walkthrough (60–90s) can be added here later — link the video or
> embed a GIF in [`docs/assets/`](docs/assets/)._

A ready-to-record script, narration, timing guide, and recording checklist live
in [`docs/demo-script.md`](docs/demo-script.md).

## Running tests and builds

Backend tests (parser, review engine, providers, routes, and edge cases):

```bash
cd backend && source .venv/bin/activate
python -m pytest -q
```

Frontend tests (Vitest + React Testing Library) and the production build:

```bash
cd frontend
npm test           # run the Vitest suite once
npm run test:watch # watch mode
npm run build      # type-check (`tsc -b`) + production build (`vite build`)
```

## Provider architecture

Review generation lives behind a single `ReviewProvider` interface
(`backend/app/services/providers/base.py`):

```python
review(parsed_diff, selected_personas, title=None, description=None) -> list[PersonaReview]
```

The provider is chosen by the `REVIEW_PROVIDER` environment variable, resolved by
a small factory (`create_provider`) that validates the value:

| `REVIEW_PROVIDER` | Behavior                                                          |
| ----------------- | ----------------------------------------------------------------- |
| `mock` *(default)*| Deterministic, offline heuristics. No AI, no credentials.         |
| `bedrock`         | Placeholder seam. Returns a clear **501**, not a fake review.     |
| *anything else*   | Fails fast with a `ValueError` listing the valid options.         |

```bash
# Default — fully local, deterministic:
uvicorn app.main:app --reload --port 8000

# Explicit:
REVIEW_PROVIDER=mock uvicorn app.main:app --reload --port 8000

# Placeholder — /api/reviews responds 501 with an explanatory message:
REVIEW_PROVIDER=bedrock uvicorn app.main:app --reload --port 8000
```

Persona knowledge (display name, review focus, output expectations, severity
guidance) lives once in `backend/app/personas/registry.py`, so the mock provider
and any future LLM provider build from the same source of truth.

**Why real AI calls are intentionally deferred:** keeping reviews deterministic
and offline means the app runs for free with no credentials, the test suite stays
fast and deterministic, and the extensibility seam is proven before spending on
tokens. Adding Bedrock later is an isolated change inside `BedrockReviewProvider`.

## Markdown export

From the results panel, **Export Markdown** downloads a `.md` report built
entirely client-side (`frontend/src/lib/exportMarkdown.ts`). The report always
reflects the **full review** — every persona and every finding — independent of
the reviewer/severity filters applied in the UI. It includes an overview
(risk, recommendation, diff stats), the council summary, and findings grouped by
reviewer with file/location/confidence. See
[`docs/sample-review-export.md`](docs/sample-review-export.md) for an example.

## Screenshots

> **Note:** the images below are placeholders — capture them locally and drop the
> PNGs into [`docs/assets/`](docs/assets/) using the exact filenames shown. See
> [`docs/assets/README.md`](docs/assets/README.md) for sizes and the app state to
> set up for each shot. (Until then, the image links render as their captions.)

### Main review input

![Main review input screen — diff input with a demo loaded and personas selected](docs/assets/main-review-input.png)

*The input panel: load a built-in demo diff (or paste/upload your own), pick
reviewer personas, and run a review. Shown here with the low-risk frontend demo
loaded, before running.*

### Risky backend review dashboard

![Risky backend review dashboard — high risk verdict, stats, reviewer tabs, and finding cards](docs/assets/risky-review-dashboard.png)

*The results dashboard for the risky backend demo: overall risk and merge
recommendation badges, diff stats, reviewer tabs, severity filtering, and
detailed finding cards from the Security/QA/Backend/SRE personas.*

### Markdown export

![Markdown export output — the exported report rendered as Markdown](docs/assets/markdown-export.png)

*The downloaded `.md` report (rendered): overview with risk/recommendation/stats,
the council summary, and findings grouped by reviewer — the full review,
independent of any UI filters.*

## Portfolio notes

Positioning material — project summary, resume bullet variants, a LinkedIn/GitHub
blurb, and interview talking points — lives in
[`docs/portfolio-notes.md`](docs/portfolio-notes.md). Design notes for a future
GitHub/GitLab MR/PR diff import (adapters, security, proposed `POST /api/import-diff`)
are in [`docs/future-git-provider-import.md`](docs/future-git-provider-import.md).
Both are documentation only — no GitHub/GitLab integration, OAuth, or AI calls are
implemented.

## Known limitations

- **No real AI.** Findings come from heuristics, so they're approximate and can
  produce false positives/negatives. `BedrockReviewProvider` is a stub.
- **No authentication and no GitLab/GitHub integration.** Diffs are pasted,
  uploaded, or loaded from samples — there is no OAuth or API fetch.
- **No persistence.** Reviews are computed on demand and not stored; there is no
  database. Export to Markdown is the only way to keep a result.
- **Heuristic scope.** The parser targets common unified-diff output; unusual or
  malformed diffs may parse partially.
- **Single-request flow.** No batching, history, or multi-MR comparison.

## Future enhancements

- Implement `BedrockReviewProvider` (prompt-per-persona from the registry, parse
  model output into findings) behind the existing seam.
- Add GitLab/GitHub integration to fetch MR/PR diffs by URL.
- Persist reviews (DynamoDB) and store exports/artifacts (S3); add review history.
- Authentication and per-user/org configuration.
- CI integration: post the review as an MR/PR comment automatically.
- Richer findings (inline diff annotations, dedupe/ranking, confidence tuning).
- Deployment automation (API Gateway/Lambda or ECS) with infrastructure-as-code.

## Next iteration: v0.2 (planned)

> These are **planned/future** capabilities, not current MVP behavior. They do not
> add real AI, GitHub/GitLab integration, or any auto-posting. Full design:
> [`docs/v0.2-plan-reviewer-tone-and-comment-replies.md`](docs/v0.2-plan-reviewer-tone-and-comment-replies.md).

- **Reviewer voice/tone profiles** — configure each persona's communication style
  (tone: direct / supportive / educational / strict / curious / executive;
  strictness; verbosity; optional custom instructions). Tone changes *wording and
  framing only* — it will **not** change risk detection, severities, or the merge
  recommendation.
- **Suggested replies to existing MR/PR comments** — paste existing comment
  threads and generate *draft* replies from selected reviewer perspectives.
  Copy-only: replies are never posted back automatically; you review and post them
  yourself.

Both will continue to run locally on the deterministic mock provider. GitHub/GitLab
comment import and any auto-posting are intentionally deferred until the local
model is proven (see the plan doc).

> **v0.2 progress:** reviewer tone is now end-to-end. The **"Reviewer voice" UI**
> lets you pick a global tone (style / strictness / verbosity + optional custom
> instructions) and optional per-reviewer overrides before running a review; the
> deterministic mock provider rewords finding explanations, recommendations, and
> persona summaries accordingly (see [`docs/review-contract.md`](docs/review-contract.md)).
> Tone is **presentation only** — findings, severities, overall risk, and the
> merge recommendation are unchanged, the default voice is an exact no-op, and
> per-reviewer overrides win over the global voice.
>
> **Suggested replies** are now generated too: capture existing MR/PR **comment
> threads** (an optional local input) and the review returns deterministic,
> **copy-only** draft replies, routed to relevant selected personas and framed in
> the resolved tone. Each reply is **self-contained** — it carries the source
> thread's `filePath`/`line` for context. They appear in a grouped "Suggested
> replies" panel with per-reply copy and a "copy all replies for this thread"
> action, and are included in the Markdown export. Every reply is marked
> "needs human review" and **nothing is posted anywhere** — there is no
> GitHub/GitLab integration and no auto-posting. Real AI-driven output remains
> deferred.
