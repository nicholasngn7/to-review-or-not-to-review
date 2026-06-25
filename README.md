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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` to the backend
at `http://localhost:8000`.

## Current MVP Scope

This is an incremental build. What exists today (scaffold step):

- [x] Monorepo structure (`frontend/`, `backend/`, `docs/`)
- [x] Backend `GET /health` returning `{ "status": "ok" }`
- [x] Frontend landing page with project name, description, and a "Start Review" placeholder
- [x] Shared review contract models (backend Pydantic + frontend TypeScript)
- [x] Diff parsing (files / hunks / lines) via `POST /api/parse-diff`
- [ ] Mock review engine + persona findings
- [ ] `POST /api/review` endpoint
- [ ] Results UI (summary, risk score, reviewer tabs, finding cards)
- [ ] Export to Markdown

No AI integration is wired up yet.
