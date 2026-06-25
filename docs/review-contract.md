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

\* The field is always present; an empty array is allowed.

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
values are listed under [Enum values](#enum-values). Real AI-driven tone rendering
and a tone-selection UI are still future work.

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
