# Portfolio package — MR Review Council

Ready-to-use positioning copy for *MR Review Council* (repo:
`to-review-or-not-to-review`). Everything here is written to be **truthful**: it is a
local-first portfolio/architecture demonstration with a deterministic mock review
provider, a provider abstraction, a fixture-based comment-import demo, and copy-only
suggested replies. It is **not** a live GitHub/GitLab integration, **not** a real
AI/LLM product, and **not** a production deployment. See
[Do not overclaim](#do-not-overclaim) and the [Final accuracy checklist](#final-accuracy-checklist).

**Fast facts (for metrics-aware copy):**

- Full-stack: **React + TypeScript (Vite)** frontend, **Python + FastAPI + Pydantic v2**
  backend.
- **7** reviewer personas (Architect, QA, Security, Frontend, Backend, SRE, Product).
- **3** tagged milestones: `v0.1.0`, `v0.2.0`, `v0.3.0`.
- **~217 automated tests** (161 backend / 56 frontend) plus Playwright demo automation.
- **10** exact-version screenshots and **3** demo videos captured from the tagged builds.

---

## Blurbs

### Short (1–2 sentences)

> **MR Review Council** is a local-first, full-stack merge-request review assistant
> (React/TypeScript + FastAPI/Pydantic) that reviews a diff through seven engineering
> personas and returns a risk verdict, per-persona findings, and an exportable Markdown
> report — with review generation behind a pluggable provider seam (deterministic mock
> today, real AI ready to drop in).

### Medium (paragraph)

> **MR Review Council** turns a unified diff into a structured, multi-perspective code
> review. Seven specialized personas — Architect, QA, Security, Frontend, Backend, SRE,
> and Product — each produce findings that roll up into one overall risk level and merge
> recommendation, all exportable as Markdown for an MR/PR comment. It is built as a
> contract-first full stack: a typed React/TypeScript frontend and a FastAPI/Pydantic
> backend sharing one JSON boundary. Review generation lives behind a `ReviewProvider`
> abstraction selected by an environment variable, so a deterministic, offline mock runs
> today and a real AI provider (Bedrock/OpenAI/Anthropic) can be added later without
> changing the API or UI. Later milestones add reviewer tone profiles, deterministic
> copy-only suggested replies for existing comment threads, and a local fixture-based
> path that normalizes GitHub/GitLab-shaped comment JSON into the same review pipeline.

### Long (portfolio detail)

> **MR Review Council** is a portfolio/architecture demonstration of an AI-assisted code
> reviewer, deliberately shipped local-first so the entire product flow is proven before
> spending on tokens or cloud infrastructure.
>
> The backend (Python, FastAPI, Pydantic v2) parses raw unified-diff text into structured
> files/hunks/lines/stats, then asks a configured `ReviewProvider` for one review per
> selected persona and aggregates a single response: overall risk, a merge recommendation
> (`ready` → `needs human review`), a council summary, diff stats, and per-persona plus
> flattened findings. Persona knowledge (focus, output expectations, severity guidance)
> lives once in a registry so every provider shares one source of truth. The provider is
> chosen by `REVIEW_PROVIDER` through a validating factory; the default mock is fully
> deterministic and offline, and a `bedrock` placeholder returns an explicit `501` instead
> of faking a review.
>
> The frontend (React, TypeScript, Vite) is a typed dashboard: diff input by paste, file
> upload, or built-in sample; reviewer tabs; severity filters; detailed finding cards; and
> a fully client-side Markdown export of the complete review.
>
> Across three tagged milestones it adds: reviewer **tone profiles** that change wording
> and framing only (never risk, severity, or the recommendation); deterministic,
> **copy-only suggested replies** for existing MR/PR comment threads (routed to relevant
> personas, each marked "needs human review", never posted anywhere); and a **local,
> fixture-based comment-import demo** that normalizes provider-shaped GitHub/GitLab JSON
> into the existing comment-thread contract via pure, fixture-tested mappers — with
> invariance tests proving imported threads drive the pipeline identically to
> locally-entered ones. Quality is backed by ~217 automated tests and Playwright demo
> automation that captures real screenshots/videos from each exact Git tag.
>
> Live GitHub/GitLab API calls, OAuth/tokens, comment posting, real AI/LLM generation, and
> hosted deployment are intentionally out of scope and documented as future work behind the
> existing seams.

---

## Resume bullets

Pick 3–5. All are truthful; numbers reflect the current repo.

- Built **MR Review Council**, a full-stack merge-request review assistant
  (React/TypeScript + FastAPI/Pydantic) that turns a unified diff into a risk verdict,
  per-persona findings, and an exportable Markdown report.
- Designed a **pluggable `ReviewProvider` abstraction** (env-selected via a validating
  factory) so a deterministic, offline mock runs today and a real AI provider can be added
  later **without changing the API or UI**.
- Delivered the project in **three tagged milestones** (`v0.1`–`v0.3`), each adding a
  coherent capability — core review, reviewer tone + suggested replies, and a local
  comment-import demo.
- Implemented **deterministic multi-persona review logic** over a custom unified-diff
  parser, aggregating seven engineering perspectives into one risk level and merge
  recommendation.
- Added **reviewer tone profiles** (presentation-only) and deterministic, **copy-only
  suggested replies** for existing comment threads, with per-reviewer overrides and
  Markdown export.
- Normalized **GitHub/GitLab-shaped comment payloads** into a shared comment-thread
  contract through **pure, fixture-tested mappers**, with **invariance tests** proving
  import behaves as a pure input adapter.
- Established **~217 automated tests** (161 backend / 56 frontend) and **Playwright demo
  automation** that captures real screenshots and videos.
- Captured **exact-version screenshots and videos from tagged builds** by running the
  current Playwright harness against historical apps via a configurable base URL.

> Do **not** add: live GitHub/GitLab API integration, real AI/LLM review generation,
> production users, or automated posting to PRs/MRs.

---

## LinkedIn

### Project entry (concise)

> **MR Review Council** — local-first multi-persona merge-request reviewer.
> React/TypeScript + FastAPI/Pydantic. Parses a diff and reviews it through seven
> engineering personas (Architect, QA, Security, Frontend, Backend, SRE, Product) into one
> risk verdict, per-persona findings, and a Markdown export. Review generation sits behind
> a pluggable provider seam — a deterministic mock runs today; a real AI provider drops in
> later with no API/UI changes. Adds reviewer tone profiles, copy-only suggested replies,
> and a local fixture-based GitHub/GitLab comment-import demo. Contract-first, tested
> (~217 tests), and demoed with Playwright-captured assets.

### Post draft (slightly longer)

> I built **MR Review Council**, a small full-stack project exploring what an automated
> "review council" could look like: review one merge-request diff through seven
> engineering lenses — Architect, QA, Security, Frontend, Backend, SRE, Product — and roll
> them into a single risk verdict, per-persona findings, and a Markdown report.
>
> The deliberate part is the architecture. I shipped it **local-first**: review generation
> sits behind a pluggable `ReviewProvider` interface, with a deterministic, offline mock as
> the default. That kept the whole flow free, fast, and reproducible — and proved the
> end-to-end product before spending a cent on tokens. A real AI provider can be added
> later as an isolated change, with no impact on the API or UI.
>
> Three tagged milestones layer on reviewer tone profiles (wording only — never risk or
> severity), deterministic **copy-only** suggested replies for existing comment threads,
> and a **local, fixture-based** demo that normalizes GitHub/GitLab-shaped comment JSON into
> the same review pipeline — with invariance tests proving the import is just an input
> adapter.
>
> Honest scope: no live GitHub/GitLab calls, no OAuth/tokens, no auto-posting, no real LLM
> calls yet — all designed for behind the existing seams. Stack: React + TypeScript + Vite,
> Python + FastAPI + Pydantic, ~217 automated tests, and Playwright demo automation.
>
> #SoftwareEngineering #FullStack #React #TypeScript #Python #FastAPI #CodeReview

### GitHub pinned-repo summary (< 350 chars)

> Local-first multi-persona merge-request reviewer. React/TypeScript + FastAPI/Pydantic.
> Parses a diff and reviews it through 7 personas into a risk verdict, findings, and
> Markdown export — behind a pluggable provider seam (deterministic mock now, real AI
> later). Adds tone profiles, copy-only suggested replies, and a local comment-import demo.

*(343 characters, under the 350 limit.)*

---

## Interview talking points

1. **Why local-first / deterministic first.** A deterministic mock provider made the whole
   diff → review → verdict flow free to run, reproducible, and trivially testable. It let me
   validate product flow and contracts before incurring any LLM/cloud cost — an explicit,
   documented tradeoff (heuristic findings) rather than an accidental limitation.
2. **Why the provider abstraction matters.** All review generation is behind one
   `ReviewProvider.review(...)` method, env-selected via a validating factory. The mock and
   any future model build from the same persona registry, so swapping in real AI is an
   isolated change with no impact on the engine, routes, or UI — and a `bedrock` placeholder
   marks exactly where it plugs in (returning a clear `501`, never a fake review).
3. **How normalized comment threads decouple provider data from review behavior.** Existing
   discussions are represented by one comment-thread contract. Whether a thread is typed in
   locally or imported from provider-shaped JSON, it enters the *same* review/reply path —
   the review engine never knows or cares where the data came from.
4. **How invariance tests prove import is a pure input adapter.** Tests feed identical logical
   threads through both the local and imported paths and assert the review/reply outputs
   match. That pins down "import only adapts input; it must not change review behavior" as an
   enforced property, not just a comment.
5. **Why copy-only replies are safer than auto-posting.** Suggested replies are deterministic,
   framed in the resolved tone, marked "needs human review", and only ever copied by the user.
   Keeping a human in the loop avoids posting low-confidence or wrong content to real
   discussions — and sidesteps the auth, permissions, and trust problems of write access.
6. **Why tone is presentation-only.** Tone profiles reword explanations/recommendations but
   never touch findings, severities, overall risk, or the merge recommendation; the default
   voice is an exact no-op. This keeps the "verdict" trustworthy and independent of styling.
7. **Why demo automation uses exact Git tags.** Each milestone is a runnable tag. To show a
   version honestly, I run the historical app from its tag worktree and point the *current*
   Playwright harness at it via a configurable base URL — so screenshots/videos reflect the
   real build at that version, never the latest code mislabeled.
8. **Contract-first frontend/backend boundary.** Pydantic models are the source of truth and
   serialize to camelCase JSON mirrored by TypeScript types, keeping the boundary explicit and
   type-safe and making breaking changes obvious.
9. **Separation of concerns.** A pure diff parser → an engine that only aggregates → providers
   that only produce per-persona reviews → pure mappers for import. Each piece is small,
   testable, and replaceable.
10. **What comes next for live provider integration.** Implement `BedrockReviewProvider`
    (prompt-per-persona from the registry, parse output into the existing finding models);
    add live GitHub/GitLab diff/comment fetch by URL behind an adapter (tokens, rate limits,
    privacy); then persistence and deployment — all behind seams that already exist.

---

## Do not overclaim

State these plainly anywhere the project is described:

- **Deterministic mock, not AI.** Findings come from deterministic heuristics; the app does
  not call an LLM and does not "understand" code. `REVIEW_PROVIDER=bedrock` is a placeholder
  that returns a `501`.
- **No live GitHub/GitLab integration.** Diffs and comments are pasted, uploaded, or loaded
  from bundled **synthetic** samples. There is no API fetch, no OAuth, and no token input.
- **No comment posting.** Suggested replies are copy-only; nothing is ever posted back to a
  PR/MR.
- **No production deployment / users.** It runs locally; there is no hosting, no database, and
  no real users. Call it an **MVP / architecture demonstration**.
- **Future AI must be clearly labeled.** Only describe real AI/provider integration as
  *planned/designed* until the provider is actually implemented.

## Final accuracy checklist

Before publishing any portfolio/resume/LinkedIn copy or tagging a release, confirm:

- [ ] No claim of **live GitHub/GitLab** API integration.
- [ ] No claim of **OAuth or token** input/handling.
- [ ] No claim of **production users** or a hosted deployment.
- [ ] No claim of **real AI/LLM** review generation (future provider is clearly labeled as
      planned, not shipped).
- [ ] No claim of **auto-posting** replies/comments to PRs/MRs.
- [ ] Screenshots and videos are described as **real captures from the tagged builds**
      (`v0.1.0`, `v0.2.0`, `v0.3.0`).
- [ ] Metrics (test counts, persona count, milestone count) match the repo.
- [ ] All README and doc links resolve.
