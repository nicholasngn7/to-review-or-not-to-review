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

## Provider interface (Phase 9)

- **Provider seam.** Review generation now sits behind a `ReviewProvider` ABC
  (`app/services/providers/base.py`) with a single method:
  `review(parsed_diff, selected_personas, title=None, description=None) -> list[PersonaReview]`.
  The `review_engine` parses the diff, calls the provider, and aggregates overall
  risk / recommendation / summary / diff stats / flattened findings. The API
  response contract is unchanged.
- **Mock stays default.** The existing heuristic logic moved verbatim into
  `MockReviewProvider` (`mock_provider.py`); `mock_review_provider.py` was
  removed. Per-persona risk + summary computation moved with it (it's a
  provider-level concern now that providers return `PersonaReview`). Existing
  parser/engine/route tests pass unchanged.
- **Configuration.** `REVIEW_PROVIDER` (read in `app/core/config.py`,
  default `mock`) selects the provider. Validation lives in the
  `create_provider()` factory so an unknown value raises a `ValueError` listing
  valid options rather than silently falling back. Settings are read at call time
  (no caching) so env overrides work without a restart.
- **Bedrock is a placeholder only.** `BedrockReviewProvider` does not import
  boto3 or touch AWS; selecting it raises `NotImplementedError`. A FastAPI
  exception handler maps that to a `501` with the explanatory message, so the API
  fails clearly instead of returning an opaque `500` or pretending to work. No
  new dependencies were added.
- **Persona registry.** `app/personas/registry.py` holds one `PersonaSpec` per
  persona (display name, description, review focus, output expectations, severity
  guidance) plus a `persona_prompt()` renderer. This is the shared source of
  truth: the mock provider uses it for display names, and a future LLM provider
  can build prompts from it without duplicating persona knowledge.
- **Why defer real AI.** Keeping reviews deterministic and offline means the app
  runs for free with no credentials, tests stay fast and deterministic, and the
  extensibility seam is proven before spending on tokens. The Bedrock provider is
  the obvious, isolated place to add the integration later.
