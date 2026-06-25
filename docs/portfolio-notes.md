# Portfolio & Resume Notes — MR Review Council

Positioning material for *MR Review Council* (repo: `to-review-or-not-to-review`).
Use these blurbs and talking points for a portfolio site, resume, LinkedIn, or
interviews. Keep claims accurate — see the "Do not overclaim" section.

## 1. Project summary (portfolio)

**MR Review Council** is a multi-persona merge-request review assistant. It parses
a unified diff and reviews it through seven specialized engineering perspectives —
Architect, QA, Security, Frontend, Backend, SRE, and Product — then aggregates a
single verdict: an overall risk level, a merge recommendation, and per-persona
findings you can filter, read, and export to Markdown. The MVP is **local-first**:
reviews are produced by a deterministic mock provider behind a clean
`ReviewProvider` interface, so a real AI provider (Amazon Bedrock / OpenAI /
Anthropic) can be added later without changing the API or UI. Built with a React +
TypeScript frontend and a Python + FastAPI + Pydantic backend.

## 2. Resume bullet variants

**Concise**
- Built *MR Review Council*, a full-stack (React/TypeScript + Python/FastAPI)
  multi-persona code-review tool that turns a diff into a risk verdict, persona
  findings, and an exportable Markdown report.

**Technical**
- Designed and built a full-stack review assistant: a FastAPI/Pydantic backend
  with a custom unified-diff parser, a multi-persona review engine, and a
  pluggable `ReviewProvider` abstraction (deterministic mock today, Bedrock-ready
  seam), paired with a typed React/TypeScript dashboard (reviewer tabs, severity
  filtering, client-side Markdown export). Backed by a pytest suite and a
  type-checked frontend build.

**Leadership / architecture-focused**
- Led the architecture of an AI-assisted code-review system, deliberately shipping
  a local-first MVP behind a provider interface to validate the end-to-end product
  flow and contracts before incurring cloud/LLM cost — establishing a clean seam
  for future Amazon Bedrock integration, plus documented decisions, demo assets,
  and a contract-first frontend/backend boundary.

## 3. LinkedIn / GitHub project description

> **MR Review Council** — a multi-persona merge-request reviewer. It reviews a Git
> diff through Architect, QA, Security, Frontend, Backend, SRE, and Product lenses,
> returning an overall risk level, a merge recommendation, and per-persona findings
> with file/line context — exportable as Markdown for an MR/PR comment.
>
> Full-stack: React + TypeScript (Vite) frontend, Python + FastAPI + Pydantic
> backend, with a custom unified-diff parser and a pluggable review-provider
> interface. The MVP runs entirely locally using a deterministic mock provider; a
> real AI provider (Bedrock/OpenAI/Anthropic) plugs into the same seam without API
> or UI changes. Contract-first, tested, and documented.

## 4. Interview talking points

**Why I built it**
- Code review is where a lot of engineering judgment lives, but one reviewer rarely
  holds every lens at once. I wanted to explore an automated "council" of
  specialized reviewers over a single diff — and use it as a vehicle to design a
  realistic AI-assisted system end to end.

**Architecture choices**
- Contract-first: Pydantic models are the source of truth and serialize to
  camelCase JSON mirrored by TypeScript types, so the frontend/backend boundary is
  explicit and type-safe.
- Separation of concerns: a pure diff parser → a review engine that only
  aggregates → providers that only produce per-persona reviews. The engine and API
  contract are provider-independent.
- Persona knowledge centralized in a registry (focus, output expectations,
  severity guidance) so the mock provider and any future LLM provider share one
  source of truth.

**Local-first MVP tradeoff**
- I shipped a deterministic mock provider first. Upside: free to run, no
  credentials, fast/deterministic tests, easy for anyone to clone and demo, and the
  architecture is proven before spending on tokens. Downside: findings are
  heuristic, not "intelligent" — an explicit, documented tradeoff, not an
  oversight.

**How the provider abstraction supports future AI**
- All review generation is behind a single `ReviewProvider.review(...)` method,
  selected by a `REVIEW_PROVIDER` env var via a validating factory. A
  `BedrockReviewProvider` placeholder marks the exact seam; implementing it means
  building a prompt per persona from the registry, calling the model, and parsing
  results into the existing finding/persona models — no changes to the engine,
  routes, or UI.

**How this reflects real code-review / production-readiness experience**
- The personas mirror what real review and on-call actually check: test coverage
  gaps, secret/unsafe-pattern handling, broad exception handling, removed logging,
  missing timeouts, oversized/multi-concern MRs, and user-facing copy. The verdict
  + recommendation model reflects how teams gate merges ("ready" vs "needs human
  review"), and Markdown export fits the real workflow of dropping review notes
  into an MR/PR.

## 5. Do not overclaim

Always state these honestly:

- **Deterministic mock, not AI.** The current version produces findings from
  deterministic heuristics. It is not an LLM and does not "understand" code.
- **Real AI is intentionally deferred.** `REVIEW_PROVIDER=bedrock` is a placeholder
  that returns a clear 501; there are no real Bedrock/OpenAI/Anthropic calls and no
  paid-API dependencies.
- **No GitHub/GitLab integration yet.** Diffs are pasted, uploaded, or loaded from
  built-in samples — there is no OAuth and no MR/PR fetching (see
  [`future-git-provider-import.md`](future-git-provider-import.md)).
- **No persistence.** Reviews aren't stored; there is no database. Export to
  Markdown is the way to keep a result.
- Describe it as an **MVP / architecture demonstration**, not a finished product.
