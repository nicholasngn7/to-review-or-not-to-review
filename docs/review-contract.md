# Review Contract

The shared contract between the frontend and the `POST /api/reviews` endpoint
(served by the deterministic mock review engine). The backend defines this with
Pydantic models in [`backend/app/models/`](../backend/app/models); the frontend
mirrors it in [`frontend/src/types/review.ts`](../frontend/src/types/review.ts).

All JSON keys are **camelCase**. Python uses snake_case field names that are
aliased to camelCase via a shared `CamelModel` base, so requests accept camelCase
and responses emit camelCase.

## Request shape

`ReviewRequest`:

```json
{
  "diffText": "diff --git a/app.py b/app.py\n@@ ...",
  "selectedPersonas": ["architect", "security"],
  "title": "Add rate limiting",
  "description": "Optional MR/PR description",
  "source": "github",
  "toneProfile": {
    "style": "supportive",
    "strictness": "medium",
    "verbosity": "normal",
    "customInstructions": null
  },
  "personaToneProfiles": {
    "security": { "style": "strict", "strictness": "high", "verbosity": "brief" }
  }
}
```

| Field                 | Type                                  | Required | Notes                                  |
| --------------------- | ------------------------------------- | -------- | -------------------------------------- |
| `diffText`            | string                                | yes      | Raw unified diff / patch text.         |
| `selectedPersonas`    | `ReviewerPersona[]`                   | yes\*    | Personas to run (may be empty).        |
| `title`               | string \| null                        | no       | MR/PR title for context.               |
| `description`         | string \| null                        | no       | MR/PR description for context.         |
| `source`              | string \| null                        | no       | Origin hint, e.g. `gitlab`/`github`.   |
| `toneProfile`         | `ToneProfile` \| null                 | no       | Global tone for all reviewers.         |
| `personaToneProfiles` | `{ [persona]: ToneProfile }` \| null  | no       | Per-persona tone overrides.            |
| `commentThreads`      | `CommentThread[]` \| null             | no       | Existing MR/PR comment threads.        |

\* The field is always present; an empty array is allowed.

### Existing comment threads (v0.2 contract)

`commentThreads` captures existing MR/PR discussion as **structured input** so a
future feature can draft **suggested replies**. This is framed as *copy-only draft
replies* — nothing is posted back to GitHub/GitLab, and there is no Git provider
import. In Phase 14 the endpoint validates `commentThreads` but does not act on
them; reply generation lands in Phase 15.

```json
{
  "commentThreads": [
    {
      "id": "t1",
      "filePath": "app/auth.py",
      "line": 5,
      "status": "open",
      "source": "github",
      "comments": [
        {
          "id": "c1",
          "author": "Reviewer",
          "body": "Can we avoid swallowing this exception?",
          "createdAt": null,
          "isResolved": null
        }
      ]
    }
  ]
}
```

`CommentThread`:

| Field      | Type                  | Required | Notes                                   |
| ---------- | --------------------- | -------- | --------------------------------------- |
| `id`       | string                | yes      | Stable thread identifier.               |
| `filePath` | string \| null        | no       | File the thread is anchored to.         |
| `line`     | number \| null        | no       | Line the thread is anchored to.         |
| `status`   | `CommentThreadStatus` | no       | `open` / `resolved` / `unknown`.        |
| `comments` | `ThreadComment[]`     | yes      | At least one comment required.          |
| `source`   | string \| null        | no       | Origin hint, e.g. `gitlab`/`github`.    |

`ThreadComment`:

| Field       | Type            | Required | Notes                                  |
| ----------- | --------------- | -------- | -------------------------------------- |
| `id`        | string          | yes      | Stable comment identifier.             |
| `author`    | string \| null  | no       | Comment author.                        |
| `body`      | string          | yes      | Comment text; must be non-empty (trimmed). |
| `createdAt` | string \| null  | no       | Timestamp string.                      |
| `isResolved`| boolean \| null | no       | Whether this comment is resolved.      |

The frontend only sends `commentThreads` when at least one thread has a non-empty
comment body; empty rows are dropped and bodies are trimmed.

### Reviewer tone profiles (v0.2 contract)

Tone profiles configure **how** a reviewer communicates — wording, explanation
style, and recommendation framing. **Tone is presentation only**: it must never
change which findings are detected, their severity, the overall risk, the merge
recommendation, diff parsing, or provider selection.

`ToneProfile`:

| Field                | Type             | Default    | Notes                                     |
| -------------------- | ---------------- | ---------- | ----------------------------------------- |
| `style`              | `ToneStyle`      | `direct`   | Communication style.                      |
| `strictness`         | `ToneStrictness` | `medium`   | Framing forcefulness (not severity).      |
| `verbosity`          | `ToneVerbosity`  | `normal`   | Amount of explanatory detail.             |
| `customInstructions` | string \| null   | `null`     | Free-form wording guidance (phrasing only). |

**Resolution order** for a given persona: per-persona entry in
`personaToneProfiles` → global `toneProfile` → the built-in default
(`direct` / `medium` / `normal`). If both fields are omitted, behavior is
identical to before tone existed (fully backward-compatible).

**Status (Phase 13A):** tone is now **rendered by the deterministic mock
provider**. When a profile resolves to something other than the default, the
provider rewords three text fields only — a finding's `explanation`, a finding's
`recommendation`, and the persona `summary`. Everything else is invariant:
finding ids, `reviewer`, `severity`, `filePath`, `hunkReference`, `confidence`,
`title`, `overallRisk`, `mergeRecommendation`, and `diffStats`.

How each axis renders (deterministic, table-driven — no AI):

- **style** sets a leading framing on `recommendation`/`summary`
  (`direct` = no prefix/baseline; `supportive`, `educational`, `strict`,
  `curious`, `executive` each add a distinct prefix).
- **strictness** adjusts emphasis on `recommendation` only (`medium` = baseline;
  `low` softens, `high` adds a merge-safety nudge). It never changes severity.
- **verbosity** adjusts `explanation` detail (`normal` = baseline; `brief`
  trims to the first sentence; `detailed` appends a clarifying note). It never
  changes the number of findings.
- **customInstructions**, when present, is appended to the persona `summary` as a
  short reviewer note.

The default profile (`direct` / `medium` / `normal`, no custom instructions) is an
exact no-op, so omitting tone is byte-identical to the pre-tone output. Tone enum
values are listed under [Enum values](#enum-values).

**Status (Phase 13B):** a **"Reviewer voice" UI** in the diff input panel now lets
users configure the global tone and optional per-persona overrides. The frontend
builds the request conservatively:

- `toneProfile` is sent only when the global voice differs from the default
  (an untouched form sends no tone fields, reproducing the original payload).
- `personaToneProfiles` is sent only for personas that are *both* selected and
  have an override enabled; overrides for deselected personas are dropped.
- empty/whitespace-only `customInstructions` are never sent.

Real AI-driven tone rendering remains future work.

## Response shape

`ReviewResponse`:

```json
{
  "overallRisk": "medium",
  "mergeRecommendation": "ready_with_followups",
  "summary": {
    "headline": "Looks mergeable with a few follow-ups",
    "details": "Longer narrative...",
    "totalFindings": 3,
    "findingsBySeverity": { "info": 1, "low": 1, "medium": 1 }
  },
  "diffStats": {
    "filesChanged": 2,
    "addedLines": 40,
    "removedLines": 5,
    "totalHunks": 3
  },
  "personaReviews": [
    {
      "persona": "security",
      "riskLevel": "medium",
      "summary": "One potential secret exposure.",
      "findings": [
        {
          "id": "sec-1",
          "reviewer": "security",
          "severity": "medium",
          "title": "Possible hardcoded secret",
          "explanation": "An API key appears to be committed.",
          "recommendation": "Move it to an environment variable.",
          "filePath": "app/config.py",
          "hunkReference": { "hunkIndex": 0, "header": "@@ -1,3 +1,5 @@", "line": 4 },
          "confidence": 0.7
        }
      ]
    }
  ],
  "findings": [
    {
      "id": "sec-1",
      "reviewer": "security",
      "severity": "medium",
      "title": "Possible hardcoded secret",
      "explanation": "An API key appears to be committed.",
      "recommendation": "Move it to an environment variable.",
      "filePath": "app/config.py",
      "hunkReference": { "hunkIndex": 0, "header": "@@ -1,3 +1,5 @@", "line": 4 },
      "confidence": 0.7
    }
  ]
}
```

Notes:

- `personaReviews[].findings` are grouped by persona.
- Top-level `findings` is the flattened list of the same finding cards, convenient
  for rendering a single feed.
- `suggestedReplies` is **always present**. It is empty unless the request
  included `commentThreads`, in which case it holds deterministic, **copy-only**
  draft replies (Phase 15). Nothing is ever posted anywhere.

### `SuggestedReply` (generated as of Phase 15)

| Field             | Type                  | Notes                                       |
| ----------------- | --------------------- | ------------------------------------------- |
| `id`              | string                | Stable identifier.                          |
| `threadId`        | string                | The `CommentThread.id` being replied to.    |
| `reviewer`        | `ReviewerPersona`     | Persona voice the reply uses.               |
| `suggestedReply`  | string                | The drafted reply text.                     |
| `rationale`       | string                | Why this reply was suggested.               |
| `confidence`      | number \| null        | 0.0–1.0 confidence.                         |
| `needsHumanReview`| boolean               | Always `true`: replies are human-sent drafts. |
| `toneProfile`     | `ToneProfile` \| null | Tone used to frame the reply, if any.       |
| `filePath`        | string \| null        | File copied from the source thread, for context. |
| `line`            | number \| null        | Line copied from the source thread, for context. |

Each `SuggestedReply` is **self-contained**: `filePath`/`line` are copied from the
source `CommentThread` (Phase 16), so consumers don't need to re-join against the
request to show where a reply belongs.

**Generation (deterministic, local, no AI):** for each `commentThread`, the
combined comment text is keyword-routed to relevant **selected** personas
(tests/coverage → QA; auth/token/secret → Security; exception/validation/API →
Backend; logging/timeout/retry → SRE; component/UI/a11y → Frontend;
scope/boundary/coupling → Architect; wording/UX/acceptance criteria → Product).
Each matched-and-selected persona produces one reply (`confidence` 0.6). If no
keyword matches, a single fallback reply is produced for Product or Architect (if
selected), else the first selected persona (`confidence` 0.3). Tone is applied to
the reply **wording only** via the resolved `ToneProfile` (per-persona → global →
default); it never changes reviewer selection, count, or confidence. Replies never
affect findings, risk, severity, merge recommendation, or diff stats.

### Future: Git provider comment-import contracts (v0.3, Phase 1 — contracts only)

These models exist as **contracts only**. They describe the shape a future
fixture-based mapping layer would produce when normalizing recorded GitHub/GitLab
comment JSON into the existing `CommentThread` contract above. As of this phase there
are **no mappers, no fixtures, no live API calls, no OAuth, no token input, and no
endpoints** — and no behavior change to reviews or replies. Defined in
[`backend/app/models/git_import.py`](../backend/app/models/git_import.py); design in
[`v0.3-plan-git-comment-import-mappers.md`](v0.3-plan-git-comment-import-mappers.md).

`ExternalCommentReference` (provider-native identity; provenance only, never affects
review behavior):

| Field                | Type                | Notes                                       |
| -------------------- | ------------------- | ------------------------------------------- |
| `provider`           | `GitProviderType`   | `github` / `gitlab` (required).             |
| `repository`         | string \| null      | GitHub `owner/repo`.                        |
| `projectId`          | string \| null      | GitLab project path or numeric id.          |
| `pullRequestNumber`  | number \| null      | GitHub PR number.                           |
| `mergeRequestIid`    | number \| null      | GitLab MR iid.                              |
| `discussionId`       | string \| null      | GitLab discussion id (thread root).         |
| `reviewId`           | string \| null      | GitHub review id, if part of a review.      |
| `commentId`          | string \| null      | Provider comment id (thread root).          |
| `noteId`             | string \| null      | GitLab note id.                             |
| `webUrl`             | string \| null      | Human-openable link.                        |
| `isOutdated`         | boolean \| null     | Source anchored to an outdated line, if known. |

`ImportedCommentThread`: `{ thread: CommentThread, externalReference: ExternalCommentReference, warnings: string[] }`
— wraps the existing `CommentThread` (consumed unchanged by the pipeline) plus
provenance and non-fatal normalization notes.

`ImportCommentsRequest` (carries **no token**, triggers **no** network):
`{ provider: GitProviderType, source?: string | null, rawPayload?: object | array | null }`.
A future phase supplies already-fetched provider JSON via `rawPayload`.

`ImportCommentsResponse`:
`{ provider: GitProviderType, threads: ImportedCommentThread[], warnings: string[] }`.

**`POST /api/import-comments` (local-only, v0.3 Phase 6).** A thin endpoint that runs
the pure `import_comments(...)` orchestrator over a **caller-supplied** `rawPayload`
and returns the camelCase `ImportCommentsResponse`. It is purely a normalization
boundary for demos/tests — it **does not** call GitHub/GitLab, accepts **no** tokens
or OAuth, fetches no URLs, and posts nothing. `source` selects the mapper
(`github_review_comments` / `github_issue_comments` / `gitlab_discussions`) and must
match `provider`; an unsupported or ambiguous request returns `400` with
`{ "detail": "..." }`, while an empty payload returns `200` with `threads: []` and a
warning.

The frontend mirrors these import types in
[`frontend/src/types/gitImport.ts`](../frontend/src/types/gitImport.ts) and calls the
endpoint from [`frontend/src/api/importComments.ts`](../frontend/src/api/importComments.ts).
The **"Import comments (local demo)"** panel pastes provider-shaped JSON, normalizes
it through this endpoint, previews the result, and loads the normalized
`CommentThread`s into the existing `commentThreads` flow. It is a **local
fixture-based demo** — it does not fetch from GitHub/GitLab, require tokens, or post
comments, and is **not** live provider integration.

### `ReviewFinding` (finding card)

| Field            | Type                    | Required | Notes                                  |
| ---------------- | ----------------------- | -------- | -------------------------------------- |
| `id`             | string                  | yes      | Stable identifier.                     |
| `reviewer`       | `ReviewerPersona`       | yes      | Which persona raised it.               |
| `severity`       | `FindingSeverity`       | yes      |                                        |
| `title`          | string                  | yes      | Short heading.                         |
| `explanation`    | string                  | yes      | What the issue is and why it matters.  |
| `recommendation` | string                  | yes      | Suggested action.                      |
| `filePath`       | string \| null          | no       | Related file, if any.                  |
| `hunkReference`  | `HunkReference` \| null | no       | Hunk/line the finding ties to.         |
| `confidence`     | number \| null          | no       | 0.0–1.0 model confidence.              |

### `HunkReference`

| Field       | Type           | Required | Notes                                |
| ----------- | -------------- | -------- | ------------------------------------ |
| `hunkIndex` | number         | yes      | Index into `DiffFile.hunks`.         |
| `header`    | string \| null | no       | The `@@` header, for display.        |
| `line`      | number \| null | no       | New-file line number, when known.    |

## Parsed diff stats

`DiffStats` (also nested in `ParsedDiff`):

| Field          | Type   | Notes                          |
| -------------- | ------ | ------------------------------ |
| `filesChanged` | number | Number of files in the diff.   |
| `addedLines`   | number | Total added lines.             |
| `removedLines` | number | Total removed lines.           |
| `totalHunks`   | number | Total hunks across all files.  |

Full parsed-diff models (`DiffLine`, `DiffHunk`, `DiffFile`, `ParsedDiff`) are
defined for the parser phase; only `DiffStats` is surfaced in the review response.

## Enum values

| Enum                  | Values                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| `ReviewerPersona`     | `architect`, `qa`, `security`, `frontend`, `backend`, `sre`, `product` |
| `RiskLevel`           | `low`, `medium`, `high`                                                |
| `MergeRecommendation` | `ready`, `ready_with_followups`, `needs_changes`, `needs_human_review` |
| `FindingSeverity`     | `info`, `low`, `medium`, `high`                                        |
| `LineKind`            | `added`, `removed`, `context`                                          |
| `FileChangeType`      | `added`, `modified`, `deleted`, `renamed`, `unknown`                   |
| `ToneStyle`           | `direct`, `supportive`, `educational`, `strict`, `curious`, `executive` |
| `ToneStrictness`      | `low`, `medium`, `high`                                                |
| `ToneVerbosity`       | `brief`, `normal`, `detailed`                                          |
| `CommentThreadStatus` | `open`, `resolved`, `unknown`                                          |
| `GitProviderType`     | `github`, `gitlab` (future import contracts; not yet wired to anything) |

## Reviewer personas and responsibilities

| Persona     | Value       | Focus                                                                                  |
| ----------- | ----------- | -------------------------------------------------------------------------------------- |
| Architect   | `architect` | System design, boundaries, coupling, abstractions, long-term maintainability of structure. |
| QA / Test   | `qa`        | Test coverage, edge cases, regressions, missing or weak assertions.                    |
| Security    | `security`  | Vulnerabilities, secrets, injection, authz/authn, unsafe dependencies and patterns.    |
| Frontend    | `frontend`  | UI/UX correctness, accessibility, state handling, component and styling concerns.      |
| Backend     | `backend`   | API design, data handling, error handling, performance of server-side logic.          |
| SRE / On-call | `sre`     | Observability, logging, metrics, reliability, deployment and operational risk.         |
| Product / Maintainability | `product` | Scope clarity, readability, documentation, and alignment with intended behavior. |
