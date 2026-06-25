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

## Results dashboard (Phase 6)

- **Shared labels:** `src/lib/reviewLabels.ts` is the single source of truth for
  persona/risk/severity/recommendation labels and canonical ordering. Both
  `PersonaSelector` and the results components consume it (removed the old
  `PERSONA_OPTIONS` export from `PersonaSelector`).
- **Presentational split:** `RiskBadge`, `MergeRecommendationBadge`,
  `FindingCard`, and `ReviewerTabs` are pure presentational components.
  `FindingsPanel` owns the local filter state (reviewer tab + severity), keeping
  filtering state inside the results area.
- **Reviewer tabs double as the persona filter** (an "All" tab plus one per
  persona that ran). Severity is a separate chip group. Tab counts reflect the
  active severity filter so they always match the visible list.
- **Empty states:** review-level "No findings found"; per-reviewer positive
  state when a persona that ran has no findings; and "No findings match the
  current filters." when filters exclude everything.

## Markdown export (Phase 7)

- **Client-side only.** Export builds the Markdown string in the browser
  (`src/lib/exportMarkdown.ts`) and downloads it via a Blob + object URL. No
  backend export endpoint.
- **Title source.** `ReviewResponse` does not carry the MR title, so
  `useReview` now retains the submitted `ReviewRequest`; `App` passes
  `request.title` into `ReviewSummary` -> `ExportMarkdownButton`. Falls back to
  "Untitled merge request" when absent.
- **Full result, not filtered.** The report always reflects every persona and
  finding via `personaReviews`, independent of the UI's reviewer/severity
  filters. Findings are grouped by reviewer in canonical `PERSONA_ORDER`.
- **Filename** is `mr-review-council-report.md`, with a sanitized title slug
  appended when a title is present.
- See `docs/sample-review-export.md` for an example of the output structure.

## Demo mode (Phase 8)

- **Sample diffs** live in `src/samples/sampleDiffs.ts` as plain data
  (`SampleDiff[]`): id, label, title, description, diff text, and recommended
  personas. All content is invented/generic — no proprietary code.
- **Load a demo diff** control sits at the top of the input panel and is clearly
  marked "sample data". Selecting a sample fills title/description/diff and sets
  the recommended personas, but does **not** auto-run — the user still clicks
  "Run Review" (keeps the demo deliberate and matches the normal flow).
- Three samples: low-risk frontend (clean, includes a test update), risky backend
  auth (security/QA/backend/SRE), and mixed full-stack (architect/product/QA).
- The paste/upload workflow is unchanged; demo loading just sets the same form
  state.
