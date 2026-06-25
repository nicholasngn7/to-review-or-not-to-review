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

## Final MVP decisions (Phase 10)

These are the deliberate scope boundaries for the MVP. Each is a documented
non-goal, not an oversight — chosen to keep the project clonable, free to run,
and focused on demonstrating the review pipeline and its architecture.

- **Local-first MVP.** The whole app runs on `localhost` with only Node + Python.
  No cloud services, accounts, or credentials are required to clone and demo it.
- **Mock provider first.** Reviews are produced by deterministic heuristics so the
  full product flow is real and demoable without an LLM. Same input ⇒ same output.
- **Provider abstraction before real AI.** The `ReviewProvider` seam (+ Bedrock
  placeholder) was built first so a real model is an isolated future change, not a
  refactor. Architecture is proven before any token spend.
- **No real AI / paid API calls yet.** `REVIEW_PROVIDER=bedrock` intentionally
  returns a clear `501`; there are no boto3 / OpenAI / Anthropic dependencies.
- **No auth / OAuth yet.** No GitLab/GitHub login or diff-fetch-by-URL; diffs are
  pasted, uploaded, or loaded from samples. Keeps the surface area small and the
  demo frictionless.
- **No database / persistence yet.** Reviews are computed on demand and not
  stored. Markdown export is the way to keep a result. DynamoDB/S3 are designed-for
  but unimplemented.
- **Demo diffs included.** Built-in sample diffs (`frontend/src/samples/`) make
  the app demoable without a real MR and give repeatable "clean" vs "risky"
  reviews for screenshots and walkthroughs.
- **Docs as a deliverable.** README (portfolio-oriented), `architecture.md` (flow
  + Mermaid + where AWS fits), this decision log, and `review-contract.md` are
  treated as part of the MVP, not an afterthought.
- **Polish over new features.** Phase 10 was scoped to validation, docs, and
  cleanup (no unused imports; consistent route names `GET /health`,
  `POST /api/parse-diff`, `POST /api/reviews`); no new large features were added.

## v0.2 planning decisions (reviewer tone & suggested replies)

Planning-only decisions for the next iteration (full design in
[`v0.2-plan-reviewer-tone-and-comment-replies.md`](v0.2-plan-reviewer-tone-and-comment-replies.md)).
No code is implemented yet.

- **Tone is presentation/framing, not detection.** Tone profiles (tone,
  strictness, verbosity, custom instructions) only change finding *wording* and
  recommendation framing. They must **not** change which findings are produced,
  their severities, `overallRisk`, or `mergeRecommendation`. This is enforced
  architecturally (a `ToneRenderer` runs *after* the provider, and aggregation
  reads only raw severities) and by a planned tone-invariance test.
- **Strictness affects emphasis, not thresholds.** Strictness is the easiest thing
  to accidentally leak into detection; it is explicitly scoped to recommendation
  phrasing ("consider" vs "must"), never severity thresholds.
- **Tone fields are additive and optional.** `ReviewRequest` gains optional tone
  fields with sensible defaults; omitting them reproduces today's behavior exactly
  (backward compatible).
- **Comment replies start local and copy-only.** Suggested replies are generated
  by the deterministic mock from pasted threads and are framed as *drafts*. They
  are copied/exported by the user — never posted back automatically.
- **GitHub/GitLab import comes after the local model works.** Prove tone rendering
  and reply generation on deterministic input first; importing real threads adds
  tokens/scopes/SSRF/rate-limit surface that shouldn't gate the core feature.
- **Auto-posting is intentionally deferred.** Writing comments back to real MRs is
  high-risk (wrong/noisy comments, permissions) and would require auth and
  guardrails. Keeping replies copy-only keeps a human in the loop; auto-posting,
  if ever, is a separate gated phase after import.
- **Reuse the existing seams.** Tone uses the persona registry (prompt helpers for
  a future LLM provider) and the `ReviewProvider` boundary; replies get their own
  endpoint but the same mock-first, provider-agnostic approach. No real AI in
  v0.2.

## Tone rendering decisions (Phase 13A)

Implements the tone contract from Phase 12 in the deterministic mock provider.

- **Tone rendering is deterministic and local.** `app/services/tone_renderer.py`
  is a small, table-driven renderer (fixed prefixes/suffixes, first-sentence
  trimming). Given the same profile, persona, and text, output is always
  identical. No NLG/LLM is involved; real AI-driven tone is still deferred.
- **Tone reaches the provider via a resolved map, not the whole request.** The
  engine resolves tone per persona (override → global → default) and passes
  `tone_profiles: dict[ReviewerPersona, ToneProfile]` to
  `ReviewProvider.review(...)`. This keeps providers easy to test and avoids
  coupling them to `ReviewRequest`. The argument is optional and defaults to the
  built-in tone, so existing provider callers keep working.
- **Rendering happens after detection.** Findings (ids, severity, file/hunk refs,
  confidence) and per-persona risk are computed first; the renderer only rewrites
  `explanation`, `recommendation`, and `summary` afterwards via `model_copy`.
  Aggregation reads raw severities, so tone cannot move risk or recommendation.
- **The default profile is an exact no-op.** `direct` / `medium` / `normal` with
  no custom instructions reproduces the pre-tone output byte-for-byte, verified by
  a regression test — backward compatibility is preserved.
- **Tone UI is still future work (Phase 13B).** Only the backend renders tone for
  now; there is no way to *set* tone from the UI yet.

## Reviewer tone UI decisions (Phase 13B)

Adds the "Reviewer voice" controls; no backend or detection changes.

- **The default voice sends nothing.** The form starts at `direct` / `medium` /
  `normal` with empty custom instructions. `toneProfile` is included only when the
  global voice is customized (`isDefaultTone` check), so an untouched form
  produces the exact same payload as before tone existed (backward compatible).
- **Overrides are scoped to selected personas.** Override toggles render only for
  currently-selected personas, and the request builder emits `personaToneProfiles`
  only for personas that are still selected. An override left enabled for a
  later-deselected persona is silently ignored rather than sent.
- **Per-persona overrides win over the global voice.** This mirrors the backend
  resolution order; the UI states it explicitly in helper text and seeds a new
  override from the current global voice as a convenient starting point.
- **Never send blank custom instructions.** `toRequestTone` trims and drops
  empty/whitespace-only custom instructions before they reach the wire.
- **Kept off the main flow.** Tone lives in a collapsible `<details>` panel with a
  "Default / Customized" indicator so it doesn't crowd the primary input, and a
  reusable `ToneProfileEditor` backs both the global and per-persona editors.
- **Tone never auto-runs a review.** Changing tone only updates local state; the
  user still explicitly clicks "Run Review".

## Comment-thread contract decisions (Phase 14)

Adds the contract and local input foundation for existing MR/PR comment threads;
no reply generation, no Git provider integration, no auto-posting.

- **Threads are structured input, not an integration.** Comment threads are typed
  in locally via a small `CommentThreadsInput` form. There is no GitHub/GitLab
  import and nothing is ever posted back — replies (Phase 15) will be copy-only
  drafts a human sends.
- **`suggestedReplies` is reserved now, empty until Phase 15.** Adding the field
  to `ReviewResponse` as a default-empty list keeps the contract stable and
  backward-compatible; the frontend can build reply UI against a known shape
  before generation exists. `SuggestedReply.needsHumanReview` defaults to `true`.
- **Validation lives in two layers.** The backend rejects empty comment bodies and
  comment-less threads (Pydantic validators, surfaced as HTTP 422); the frontend
  also drops empty rows and trims bodies before sending, so only meaningful
  threads reach the wire.
- **Threads never affect detection.** `commentThreads` is accepted and validated
  but does not touch parsing, findings, risk, or recommendation — verified by a
  test asserting the response (minus `suggestedReplies`) is identical with and
  without threads.
- **Optional and out of the way.** The input is an optional, collapsible
  `<details>` panel; a review runs fine with no threads, preserving the existing
  flow exactly.

## Suggested-reply generation decisions (Phase 15)

Generates deterministic, local, copy-only draft replies for comment threads.

- **Replies ride on `/api/reviews`, not a new endpoint.** Since replies are
  derived from the same request and returned alongside the review, adding a
  separate `POST /api/comment-replies` endpoint was unnecessary. The generator
  runs in `run_review` *after* aggregation and only appends `suggestedReplies`.
- **Generation is deterministic keyword routing — no AI.** A fixed, ordered
  persona→keywords table routes each thread to relevant **selected** personas;
  each match yields one reply. This keeps output reproducible and explainable
  (the rationale names the matched keyword).
- **Clear fallback.** When nothing matches, a single reply is routed to Product or
  Architect (if selected), else the first selected persona, with a lower fixed
  confidence (0.3 vs 0.6) to signal the weaker match.
- **Tone affects wording only.** Replies reuse the `ToneRenderer` (`render_reply`)
  with the resolved per-persona tone. Tone never changes reviewer selection,
  reply count, or confidence — locked in by a test.
- **Generation never touches detection.** It reads the request and produces
  replies; findings, severities, risk, recommendation, and diff stats are
  identical with or without threads (asserted by tests).
- **Copy-only, human-in-the-loop, deferred posting.** `needsHumanReview` is always
  `true`; the UI frames replies as drafts with a copy button and an explicit "no
  comments are posted anywhere" note. Real AI, GitHub/GitLab import, and
  auto-posting remain out of scope.
