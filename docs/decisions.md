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
- **Docs as a deliverable.** The README, `architecture.md` (flow + Mermaid + where
  AWS fits), this decision log, and `review-contract.md` are treated as part of the
  MVP, not an afterthought.
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

## Suggested-reply polish decisions (Phase 16)

Makes replies self-contained and easier to use in a demo; no behavior changes.

- **`SuggestedReply` carries its own `filePath`/`line`.** Copied from the source
  thread at generation time, so the UI and Markdown export no longer re-join
  replies against the request to show where they belong. This is purely additive
  context — it never affects routing, reviewer selection, confidence, tone, or
  detection (asserted by a test).
- **Copy-all per thread.** Each thread group has a "Copy all replies for this
  thread" action that concatenates the replies with reviewer labels (e.g.
  `Security: …`) so a pasted block is readable. The per-reply copy still copies
  only that reply's text.
- **Honest empty states.** No suggested-replies section appears unless the user
  submitted comment threads; if threads were submitted but nothing matched, an
  explicit "No suggested replies were generated…" message is shown instead of a
  blank/confusing area.

## Git provider comment-import decisions (Phase 17, design-only)

- **GitHub/GitLab comment import is intentionally deferred** until the local
  comment-thread model is stable. The `CommentThread` / `SuggestedReply` contract is
  new (Phases 14–16); we want a fixed, proven target before building adapters
  against real provider data. The design ([`future-git-provider-comment-import.md`](future-git-provider-comment-import.md))
  normalizes provider PR/MR threads into the **existing** `CommentThread` contract —
  import is an input adapter only, so detection, routing, tone, and reply generation
  never change. No API calls, OAuth, or token input are implemented in v0.2.
- **Auto-posting remains out of scope** until authentication, permissioning, a human
  preview/confirm step, auditability, and duplicate-prevention safeguards exist.
  Posting to real PRs/MRs is high-risk and effectively irreversible, so replies stay
  copy-only and `needsHumanReview: true`. If ever built, posting would be a
  deliberate, separate, gated phase *after* import — never bundled with it.
- **Normalize provider comments through fixture-tested pure mappers before adding
  live API integration.** The next planned technical phase (see
  [`v0.3-plan-git-comment-import-mappers.md`](v0.3-plan-git-comment-import-mappers.md))
  introduces import **contracts** (`GitProviderType`, `ExternalCommentReference`,
  `ImportedCommentThread`, `ImportCommentsRequest`/`Response`) and **pure mapper
  functions** that convert recorded GitHub/GitLab comment JSON into the existing
  `CommentThread` contract. This is deliberately **network-free and fixture-only**:
  it nails the riskiest correctness work (threading, file/line, resolved/outdated
  state) with deterministic, offline tests, keeps provider schemas as tolerant
  `dict` access (flagging assumptions to verify against official docs), and adds no
  security surface (no tokens/SSRF/rate limits) until the mapping layer is proven.
- **Ship the import contracts before any logic (v0.3 Phase 1).** Added
  `app/models/git_import.py` (`GitProviderType`, `ExternalCommentReference`,
  `ImportedCommentThread`, `ImportCommentsRequest`, `ImportCommentsResponse`) and
  contract tests — and nothing else. `ImportCommentsRequest` intentionally has **no
  token field** and performs **no** network access; future phases pass
  already-fetched JSON via `rawPayload`. Provider-native ids live in
  `ExternalCommentReference` so the core `CommentThread` contract stays clean. This
  locks the target shape (and camelCase serialization) before mappers/fixtures land.
- **GitHub review-comment mapping is pure and fixture-tested first (v0.3 Phase 2).**
  Added `app/services/git_import/` (shared helpers + `map_github_review_comments_to_threads`)
  that turns already-parsed GitHub-style dicts into `ImportedCommentThread`s — no
  network, tokens, HTTP clients, or endpoints. Parsing is deliberately tolerant
  (defensive `.get`, multiple key spellings) because the synthetic GitHub shape used
  in `backend/tests/fixtures/github_pr_review_comments.json` **must be verified
  against official GitHub API docs before any live call**. Mapping is deterministic
  (first-seen root order, readable synthetic ids) so re-imports are idempotent, and
  it never affects detection, routing, tone, or reply behavior.
- **PR issue comments map to line-less single-comment threads (v0.3 Phase 3).**
  GitHub PR *conversation* comments have no file/line and no native threading, so
  `map_github_issue_comments_to_threads` maps each non-empty comment to its own
  `CommentThread` (`filePath`/`line` `None`, status `unknown`, ids tagged `ic`),
  keeping review/thread-only provenance fields (`reviewId`, `discussionId`,
  `isOutdated`) `None`. Same guardrails as Phase 2: pure, tolerant parsing,
  deterministic, fixture-only, and **the synthetic shape must be verified against
  official GitHub docs before live integration**.
- **GitLab discussions map one discussion → one thread (v0.3 Phase 4).**
  `map_gitlab_discussions_to_threads` turns ordered, non-system, non-empty notes into
  ordered `ThreadComment`s; system notes (`system: true`) and empty bodies are
  dropped, and a discussion with no usable notes is dropped entirely. File/line come
  from `position.new_*` (fallback `old_*`); non-positional discussions are line-less.
  Resolution is derived from notes' `resolvable`/`resolved` and mapped to the existing
  `CommentThreadStatus`; outdated positions are handled conservatively (skipped by
  default; line nulled + warning when explicitly included). Same guardrails: pure,
  tolerant parsing, deterministic, fixture-only, and **the synthetic GitLab shape
  must be verified against official GitLab docs before live integration**.
- **A pure orchestrator dispatches imports; never guesses a mapper (v0.3 Phase 5).**
  `import_comments(request)` routes by `source` (validated against the provider) and
  only infers the source when a provider has a single mapper (GitLab); ambiguous
  GitHub or unsupported provider/source combinations raise a clear `ValueError`
  rather than silently picking a mapper. Empty payloads return an empty response with
  a single warning; per-thread warnings are preserved and also surfaced at the top
  level. **Invariance is now tested**: imported threads, once normalized into
  `CommentThread`, drive `run_review` byte-identically to hand-authored local
  threads — proving Git import is purely an input adapter that downstream
  review/reply behavior is oblivious to. Live provider integration remains deferred.
- **A local-only import endpoint exposes the normalization boundary (v0.3 Phase 6).**
  `POST /api/import-comments` runs the pure orchestrator over a **caller-supplied**
  payload and returns a camelCase `ImportCommentsResponse`. It deliberately does
  **no** outbound network I/O, accepts **no** tokens/OAuth/URLs, and posts nothing —
  it exists purely to exercise and demo the mapping layer. Orchestrator `ValueError`
  maps to `400 { "detail": ... }` (matching the existing API error style) and empty
  payloads return `200` with an explanatory warning. Live GitHub/GitLab fetching and
  auth remain deferred.
- **The frontend import UI is a local fixture-based demo (v0.3 Phase 7).** The
  "Import comments (local demo)" panel pastes provider-shaped JSON, validates it
  client-side (`JSON.parse`) before calling `POST /api/import-comments`, previews the
  normalized threads + warnings, and loads them into the existing `commentThreads`
  flow. It deliberately has **no** URL input, token field, OAuth, live provider call,
  or posting — and the copy says so. `DiffInputPanel` owns `importedThreads`
  separately from manual threads and merges them de-duped by id
  (`[...importedThreads, ...manualThreads]`) when building the request, so existing
  behavior is unchanged when nothing is imported. Imported threads are read-only this
  phase (faithful to multi-comment threads); inline editing and any live provider
  integration remain deferred.
- **Bundled synthetic sample payloads ship with the import demo (v0.3 Phase 8).** To
  make the demo usable without hand-pasting JSON, `frontend/src/fixtures/importSamples.ts`
  carries three fabricated payloads (GitHub review comments, GitHub issue comments,
  GitLab discussions) and the panel renders a "Load sample payload" button per sample.
  A sample click only sets the provider/source and pretty-prints the JSON into the
  textarea — the user still clicks **Normalize comments** — so it stays explicit that
  the app normalizes supplied JSON rather than fetching anything. All sample data is
  synthetic (no real repos/people/tokens, `example.test` URLs); nothing is fetched,
  posted, and there is still no URL/token/OAuth input.
- **v0.3 stops at a local fixture-based import demo before live provider integration.**
  The whole v0.3 path — contracts, mappers, orchestrator, local endpoint, frontend
  panel, and bundled samples — is intentionally a demo of the *normalization
  boundary*. It proves imported threads behave identically to locally-entered ones,
  without taking on the cost/risk of live GitHub/GitLab fetching, OAuth, token
  storage, rate limits, or auto-posting. Those remain **deferred** with design-only
  sketches in `docs/future-git-provider-import.md` and
  `docs/future-git-provider-comment-import.md`. Release readiness is tracked in
  `docs/release-checklist-v0.3.md`.
- **The bundled sample payloads exist only for demo repeatability.** They are
  synthetic, version-controlled JSON so the demo and tests can run the import flow
  deterministically without a real provider; they are not, and should not be
  presented as, captured production data.

## v0.4 — RAG-style grounded review context (planned, not implemented)

- **v0.4 is a planning-phase design only.** No ingestion, embedding, retrieval, or
  citation code exists yet; no new dependencies and no tests were added. The shipped
  product is unchanged. Full plan: `docs/v0.4-plan-rag-grounded-review.md`.
- **Embedding sits behind a provider abstraction, mirroring `ReviewProvider`.** The
  planned `EmbeddingProvider.embed()` is selected by an `EMBEDDING_PROVIDER` env var via
  a validating factory. The default is a **deterministic local embedding provider**
  (lexical hashing vectorizer, cosine similarity, top-k); Bedrock/OpenAI embedding
  providers are an **optional future path**, disabled unless explicitly configured.
- **Retrieval is additive and provenance-only.** When a review has no knowledge sources,
  behavior is unchanged (an invariance requirement). Citations annotate findings and the
  response (`context_used`) but must not change findings, severities, overall risk, or
  the merge recommendation — the same provenance-not-behavior rule used for v0.3's
  `ExternalCommentReference`.
- **Honest positioning is mandatory.** It is a local **RAG architecture demo** with a
  deterministic, **lexical** retriever — not production-grade RAG and not semantic search.
  Wording like “production-grade RAG”, “semantic retrieval”, “Bedrock-powered”, or
  “LLM-generated findings” must not be used until a real provider is implemented and
  tested. Ingestion is local, allow-listed files only — no URL fetching, tokens, or OAuth.
- **Phase 1A ships contracts only.** `backend/app/models/knowledge.py` adds
  `KnowledgeSourceType`, `EmbeddingProviderType`, `KnowledgeDocument`, `KnowledgeChunk`,
  `EmbeddingVector`, `RetrievalQuery`, `RetrievalResult`, `RetrievedCitation`, and
  `RetrievalEvaluationCase` (CamelModel; camelCase JSON), with small deterministic
  validations (`EmbeddingVector.dimensions == len(values)`; `RetrievalQuery.top_k ≥ 1`;
  `RetrievalEvaluationCase.minimum_top_k_hit_count ≥ 1`). No ingestion/chunking/embedding/
  retrieval behavior, no endpoints, no UI, and **no** changes to the review contract — those
  additive review fields are deferred to Phase 1B. `bedrock_optional_future` is a reserved
  enum name only and implies no integration.
- **Phase 1B adds additive review-contract fields only.** `ReviewRequest` gains
  `knowledge_sources: list[str] | None = None` and `retrieval: RetrievalQuery | None =
  None`; `ReviewFinding` gains `citations: list[RetrievedCitation] = []`; `ReviewResponse`
  gains `context_used: list[RetrievalResult] = []`. They are **accepted by the contract but
  ignored by runtime review behavior** — contract placeholders only. No citations are
  generated and `contextUsed` is never populated this phase; risk, findings, severities,
  recommendation, suggested replies, tone, and import behavior are unchanged. The fields
  default to `None`/empty lists (with per-instance list defaults, no shared mutables) so
  existing requests/responses stay backward-compatible; FastAPI already serializes empty
  defaults (e.g. `suggestedReplies: []`), so adding `citations: []`/`contextUsed: []` is
  consistent with current API output. Ingestion/chunking/embedding/retrieval stay deferred
  to Phase 2+.
- **Phase 2 adds local ingestion + deterministic chunking only.**
  `backend/app/services/knowledge/ingestion.py` exposes `ingest_local_file(...)`, which
  reads **allow-listed** local text files (default roots: `README.md`, `docs/`) into
  `KnowledgeDocument`s. It rejects paths outside the allow-list, path traversal (paths are
  resolved before the allow-list check), missing files, directories, and binary/non-text
  files (NUL byte / non-UTF-8). Document ids are deterministic (`doc-<sha1(relative_path)>`),
  titles are inferred from the first Markdown H1 (else the filename), and content is stored
  verbatim. `chunking.py` exposes `chunk_document(...)`, a **pure, idempotent** function that
  splits by headings, paragraphs, and fenced code blocks into stable
  `{document.id}#chunk-{ordinal}` chunks, preserves heading + `startLine`/`endLine` metadata,
  adds an approximate whitespace-based `tokenEstimate`, keeps code fences intact where
  practical, and splits oversized prose deterministically by line/char boundaries. It is
  **offline only**: no network, URL, token/OAuth, embeddings, vector similarity, retrieval,
  endpoints, UI, or new dependencies; review behavior is unchanged and
  `citations`/`contextUsed` stay unpopulated. This is **not** production RAG, semantic
  retrieval, or Bedrock/live-provider integration. Embedding/retrieval stay deferred to
  Phase 3+.
- **Phase 3 adds a deterministic local embedding provider + in-memory index only.**
  `backend/app/services/knowledge/embedding.py` defines an `EmbeddingProvider` protocol and
  `DeterministicLocalEmbeddingProvider` — a **lexical feature-hashing** vectorizer (default
  128 dims, stdlib-only). It normalizes (NFKC + lowercase) and tokenizes text, hashes each
  token into a signed bucket using a **stable SHA-1 digest** (deliberately not Python's
  per-process salted `hash()`, so vectors are reproducible across runs/processes), weights
  by term frequency, and L2-normalizes; empty/whitespace/low-signal text returns a safe
  zero vector (chosen over raising). Vectors carry
  `EmbeddingProviderType.deterministic_local` with `dimensions == len(values)`.
  `index.py` defines `KnowledgeIndex` and `build_index(chunks, provider=None)`: an
  in-memory map of chunks + vectors whose `search(RetrievalQuery) -> list[RetrievalResult]`
  embeds the query with the same provider, ranks by cosine similarity (dot product of
  normalized vectors), applies optional `source_path`/`heading`/metadata `filters`, drops
  non-positive scores, limits to `top_k`, and tie-breaks deterministically (score desc,
  then chunk id asc). Similarity is **lexical, not semantic**; this is **not**
  neural-embedding quality, production RAG, or Bedrock/live/paid integration. It is offline
  and **in-memory only** (no vector DB, disk index, network, URL, or token/OAuth) with
  **no** new dependencies. There is still **no** review integration: the index is not
  called from `review_engine`, and `ReviewFinding.citations`/`ReviewResponse.context_used`
  stay unpopulated. Endpoints/UI/review integration stay deferred to Phase 4+.
- **Phase 4 adds a local-only retrieval service + optional endpoint only.**
  `backend/app/services/knowledge/retrieval.py` exposes `retrieve_context(query, *,
  source_paths, repo_root=None, allowed_roots=None, provider=None, max_chars=1200)`, a thin
  deterministic orchestrator that composes ingest → chunk → `build_index` → `search` on
  each call (**no persistence, no cache, no hidden global state**) and returns
  `list[RetrievalResult]`. It enforces the ingestion allow-list, **rejects URL-like inputs**
  (e.g. `scheme://…`, `git@…`, `ssh://…`) without ever fetching them, and raises a clear
  `RetrievalError` (a `ValueError`) for URL-like/outside-root/missing/non-text sources;
  empty `source_paths` and low-signal queries return `[]` (chosen over raising).
  `backend/app/api/routes/retrieve_context.py` adds `POST /api/retrieve-context` with a
  small route model (`query: RetrievalQuery`, `sourcePaths: list[str]`) returning
  `{ results, warnings }` in camelCase; the **repo root and allow-list are pinned
  server-side** (`README.md` + `docs/`), so callers cannot read arbitrary filesystem paths,
  and `RetrievalError` maps to HTTP 400. Retrieval is offline, deterministic, and
  **lexical** — **not** semantic search, production RAG, or Bedrock/live/paid integration;
  no network/URL/token/OAuth and no new dependencies. There is still **no** review
  integration: `review_engine` does not import or call retrieval, and
  `ReviewFinding.citations`/`ReviewResponse.context_used` stay unpopulated. Review
  integration, citations/contextUsed population, and any UI stay deferred to Phase 5+.
- **Phase 5 wires retrieval into review as opt-in, provenance-only grounding.**
  `backend/app/services/knowledge/review_context.py` adds `should_retrieve`,
  `resolve_retrieval_query`, and `attach_citations`, and `review_engine.run_review` calls
  them **after** computing risk/recommendation/summary/suggested replies. **Opt-in:**
  retrieval runs only when `ReviewRequest.knowledge_sources` is non-empty (a `retrieval`
  query alone has no files to read); when no retrieval query is supplied, one is derived
  deterministically from the MR title + description + changed file paths. Results populate
  `ReviewResponse.context_used`. **Citation mapping rule (documented + tested):** a
  retrieved result is cited by a finding when their *meaningful* tokens (length ≥ 3,
  excluding common stopwords) overlap — taken from the finding's
  title/explanation/recommendation/file path vs. the result's snippet/heading/source path —
  in rank order, capped at 2 per finding. Citations are **provenance only** and attached
  via `model_copy`, so detection, severity, confidence, risk, merge recommendation,
  summary, tone wording, and suggested replies are **invariant** whether or not knowledge
  sources are supplied (proven by invariance tests). The engine pins the repo root +
  ingestion allow-list (`README.md` + `docs/`); unsafe/outside/URL-like sources raise
  `RetrievalError`, which `POST /api/reviews` maps to **400** (consistent with the other
  local routes). When knowledge fields are absent, **no retrieval runs** and
  `contextUsed`/`citations` stay empty; when retrieval returns nothing, the review is
  produced normally with empty context/citations. Still local, offline, deterministic, and
  **lexical** — **not** production RAG, semantic search, Bedrock/live provider, or
  LLM-generated findings. No new dependencies and **no frontend UI** in this phase (the
  contextUsed/citations contract fields already exist from Phase 1B). Frontend surfacing is
  deferred to a later phase.
- **Phase 6 adds offline retrieval evaluation fixtures + regression metrics only.** A fixed
  synthetic corpus (`backend/tests/fixtures/knowledge/docs/`: authentication/OAuth,
  retrieval/chunking/citations, frontend/UI, reliability/retries/observability,
  security/path-rejection) and fixed cases (`retrieval_cases.json`, parsed into the Phase 1A
  `RetrievalEvaluationCase`) feed `backend/app/services/knowledge/evaluation.py`, which adds
  `load_evaluation_cases`, `evaluate_case`, `evaluate_retrieval`, `run_cases_against_index`,
  and `RetrievalEvaluationResult`/`RetrievalEvaluationReport`. Metric definitions: an
  expected item is an `expected_chunk_ids` entry matched by a result `chunk_id` or an
  `expected_source_paths` entry matched by a result `source_path`; **hit_count** =
  distinct expected items in the top-k; **hit@k** = `hit_count ≥ 1`; **recall@k** =
  `hit_count / #expected`; **precision@k** = `relevant_top_k_results / #top_k_results`;
  **passed** = `hit_count ≥ minimum_top_k_hit_count`. Cases use **expected source paths**
  (stable regardless of repo root, unlike `doc-<sha1>` chunk ids) and lexical query terms
  the deterministic hashing vectorizer can match — no semantic-synonym expectations. The
  corpus is synthetic and repo-safe (no credentials, no external URLs, no private content).
  Everything is deterministic and reproducible across runs, offline, and fixture-based; the
  evaluator is **never wired into production routes** and does **not** change the review
  flow. These metrics are **regression checks for the lexical retriever** and explicitly do
  **not** prove semantic quality — this is still **not** production RAG, semantic search,
  Bedrock/live provider, or LLM-generated review output. No new dependencies, endpoints, or
  frontend UI.
- **Phase 7 surfaces opt-in retrieval grounding in the frontend (presentation only).**
  TypeScript review types gained additive fields mirroring the backend contract
  (`frontend/src/types/review.ts`): `RetrievalQuery`, `RetrievedCitation`, `RetrievalResult`,
  plus `ReviewRequest.knowledgeSources`/`retrieval`, `ReviewFinding.citations`, and
  `ReviewResponse.contextUsed`. A collapsible **“Optional local context sources”** input
  (`ContextSourcesInput`) collects one local source path per line plus an optional
  local/lexical **“context query”**; the panel suggests safe local examples (`README.md`,
  `docs/project-case-study.md`, `docs/decisions.md`) and **never** asks for URLs or tokens or
  implies GitHub/GitLab fetching. **Default behavior is invariant:** `DiffInputPanel` attaches
  `knowledgeSources` only when the user enters source paths, and `retrieval` only when a query
  is also typed — an untouched form sends exactly the pre-v0.4 payload. Results render a
  read-only, collapsible **“Retrieved local context”** panel (`ContextUsedPanel`) and a
  secondary, expandable **“Cited context”** detail per finding (`FindingCitations`), each
  showing source path, heading, line range, a score rounded to two decimals, and the snippet —
  and are **hidden entirely** when context/citations are absent or empty. Markdown export adds
  a **“Context used”** section and per-finding citation lines only when present and is
  otherwise byte-for-byte unchanged (verified by a timestamp-stripped equality test). All copy
  is honest — retrieved context is **local, deterministic, lexical, and provenance-only**,
  explicitly *not* semantic search, *not* proof of correctness, and it does **not** change a
  finding's severity or the merge recommendation. Score/line-range formatting is centralized in
  `lib/reviewLabels.ts` (`formatScore`, `formatLineRange`, `RETRIEVAL_PROVENANCE_NOTE`). This
  is a pure presentation/adapter layer: **no backend behavior changed**, no new dependencies,
  no network behavior beyond the existing `/api/reviews` call, and still **not** production
  RAG, semantic search, Bedrock/live provider, or LLM-generated review output.
- **Phase 8 finalizes v0.4 with provider-seam docs + exact-version demo assets (no behavior
  change).** The future embedding-provider seam is documented design-only in
  [`future-embedding-provider-path.md`](future-embedding-provider-path.md): v0.4 ships **only**
  the `deterministic_local` lexical provider (`DeterministicLocalEmbeddingProvider` behind the
  `EmbeddingProvider` protocol, with the `provider=` argument to
  `build_index`/`retrieve_context` being the entire swap point), and
  `EmbeddingProviderType.BEDROCK_OPTIONAL_FUTURE` remains a **reserved name with no
  implementation**. The doc records the hard rules for any future real provider — explicitly
  configured, tested, disabled by default, fails clearly when unconfigured, **never** silently
  falls back to fabricated vectors, keeps vectors provider-tagged, and confines any
  network/credential handling to that opt-in provider. We deliberately **did not** add a
  Bedrock/OpenAI client, credentials, token/OAuth handling, network fetching, or heavy
  dependencies. Exact-version **demo assets** were captured from the current v0.4 app using the
  existing Playwright harness: `frontend/demo/screenshots/v0.4.screenshots.spec.ts` writes
  `docs/assets/screenshots/v0.4/` (`v0.4-context-sources-input`, `v0.4-retrieved-local-context`,
  `v0.4-finding-cited-context`, `v0.4-markdown-context-used`), and
  `frontend/demo/videos/v0.4.video.spec.ts` records
  `docs/assets/videos/mr-review-council-v0.4-retrieval-grounding-demo.webm`. The flow uses only
  built-in sample diffs and **local allow-listed** context sources (`README.md`,
  `docs/project-case-study.md`, `docs/decisions.md`); each spec `test.skip`s if the v0.4 UI is
  absent so it never writes a misleading file. Honest labels throughout (local, deterministic,
  lexical, provenance-only); nothing implies live providers, tokens, OAuth, GitHub/GitLab
  fetching, Bedrock/OpenAI, or semantic search.
