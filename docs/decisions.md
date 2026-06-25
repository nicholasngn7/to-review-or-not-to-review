# Decisions & Assumptions

A running log of notable choices made during the build.

## Scaffold step

- **Monorepo layout** with `frontend/`, `backend/`, and `docs/` at the root.
- **Package manager:** npm for the frontend (no lockfile committed yet until first install).
- **Backend `/health`** is mounted at the root path (`GET /health`), not under
  `/api`. The Vite proxy rewrites `/api/*` for application endpoints; the health
  check is reachable directly at `http://localhost:8000/health`.
- **CORS** is enabled for `localhost:5173` so the frontend can also call the
  backend directly if needed, in addition to the dev proxy.
- **Pinned dependency versions** in `requirements.txt` and `package.json` for
  reproducible local setup.
- **No AI integration** in this step, per scope. The review flow button is a
  disabled placeholder.

## Frontend review flow (Phase 5)

- **Vite proxy no longer rewrites `/api`.** Backend application routes are
  namespaced under `/api` (`/api/parse-diff`, `/api/reviews`), so the proxy
  forwards the path unchanged. The earlier rewrite (`/api` -> ``) was removed
  because it would have turned `/api/reviews` into `/reviews` at the backend.
- **Component split:** `DiffInputPanel` owns the form state (title, description,
  diff, personas, file upload); `App` owns the request lifecycle via the
  `useReview` hook; `ReviewSummary` renders idle/loading/error/success states.
- **Default personas:** architect, qa, security, backend, sre.
- **Validation:** Run is disabled when the trimmed diff is empty or no personas
  are selected; diff text is trimmed before sending.
