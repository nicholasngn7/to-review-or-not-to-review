# MR Review Council

A multi-persona AI merge-request reviewer. MR Review Council reviews GitLab/GitHub
merge request diffs through different engineering perspectives — Architect, QA,
Security, Frontend, Backend, SRE, and Product/Maintainability — and returns a
structured review with an overall risk level, a merge recommendation, and
per-persona findings.

The MVP runs entirely locally with no AWS credentials or paid APIs. AI reviews are
produced by a deterministic mock provider that sits behind a pluggable interface,
so a real Bedrock/OpenAI/Anthropic provider can drop in later without changing the
API or UI.

## Tech Stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** Python + FastAPI + Pydantic
- **Future:** AWS (API Gateway/Lambda or ECS, DynamoDB, S3, Amazon Bedrock)

## Repository Layout

```text
.
├── backend/    # FastAPI app (Python)
├── frontend/   # React + TypeScript + Vite app
├── docs/       # Architecture notes and project docs
└── README.md
```

## Local Setup

You need **Node.js 18+** and **Python 3.11+** installed.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is then available at `http://localhost:8000`. Health check:
`http://localhost:8000/health`.

Reviews run through a pluggable provider chosen by the `REVIEW_PROVIDER`
environment variable (default `mock`, fully offline). The `bedrock` value is a
placeholder seam that intentionally returns a clear `501` until a real provider
is implemented. See [`backend/README.md`](backend/README.md#review-providers).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` to the backend
at `http://localhost:8000`.

## Demo Walkthrough

The app ships with built-in sample diffs so you can show it off without a real
merge request.

1. Start the backend and frontend (see [Local Setup](#local-setup)):
   - Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
   - Frontend: `cd frontend && npm run dev`, then open `http://localhost:5173`.
2. In the **Merge request** panel, use **Load a demo diff** (marked *sample data*)
   and pick a sample. It fills in the title, description, diff, and a recommended
   set of personas. Nothing runs automatically.
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

To export, click **Export Markdown** in the results panel to download a `.md`
report you can paste into a GitLab/GitHub comment.

The paste-your-own and `.diff`/`.patch` upload workflows still work as before.

## Current MVP Scope

This is an incremental build. What exists today (scaffold step):

- [x] Monorepo structure (`frontend/`, `backend/`, `docs/`)
- [x] Backend `GET /health` returning `{ "status": "ok" }`
- [x] Frontend landing page with project name, description, and a "Start Review" placeholder
- [x] Shared review contract models (backend Pydantic + frontend TypeScript)
- [x] Diff parsing (files / hunks / lines) via `POST /api/parse-diff`
- [x] Mock review engine + persona findings
- [x] `POST /api/reviews` endpoint
- [x] Review flow UI (diff input, persona selector, summary, finding cards)
- [x] Results dashboard (risk/recommendation badges, stats, reviewer tabs, severity/persona filtering, empty states)
- [x] Export review to Markdown (client-side download)
- [x] Built-in demo sample diffs ("Load a demo diff")
- [x] Pluggable review provider interface (`REVIEW_PROVIDER`: `mock` default, `bedrock` placeholder)

No AI integration is wired up yet.
