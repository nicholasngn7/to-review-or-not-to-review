# Future Design: GitHub / GitLab Diff Import

> **Status: design notes only — not implemented.** The current MVP has no
> GitHub/GitLab integration and no OAuth. Diffs are pasted, uploaded, or loaded
> from built-in samples. This document sketches how MR/PR import *would* be added
> later behind the existing contracts.

## 1. Goal

Let a user paste a merge-request / pull-request **URL** and have the app fetch the
diff and run a review — removing the manual copy/paste step while reusing the
entire existing pipeline (parser → review engine → providers → UI).

## 2. MVP approach (smallest useful version)

1. **Paste MR/PR URL** in the UI (a new optional input next to the diff textarea).
2. **Fetch the diff:**
   - Prefer the provider's diff/patch endpoint for public resources (e.g. GitHub's
     `.diff`/`.patch` view, or the GitLab MR changes API).
   - For private resources, accept an optional **personal access token** supplied
     per request (never stored).
3. **Normalize into existing `diffText`.** The fetched unified diff is fed into the
   *same* `ReviewRequest.diffText`, so the diff parser, review engine, and UI need
   **no changes**. Import is purely an input adapter in front of the current flow.

This keeps the blast radius tiny: one new endpoint + adapters, zero changes to the
review contract.

## 3. Backend adapter design

A small adapter layer that turns a URL (+ optional token) into raw unified-diff
text. It mirrors the existing `ReviewProvider` pattern (an interface + concrete
implementations selected at runtime).

```python
# app/services/git_providers/base.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ImportedDiff:
    diff_text: str
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None   # "github" | "gitlab"

class GitProvider(ABC):
    name: str
    def matches(self, url: str) -> bool: ...
    def fetch_diff(self, url: str, token: Optional[str] = None) -> ImportedDiff: ...
```

- **`GitHubProvider`** — recognizes `github.com/.../pull/<n>` URLs; fetches the PR
  diff (public `.diff` endpoint, or the REST API with `Accept:
  application/vnd.github.v3.diff` when a token is supplied). Maps PR title/body into
  `title`/`description`.
- **`GitLabProvider`** — recognizes `gitlab.com/.../-/merge_requests/<n>` URLs;
  fetches MR changes via the MR API (token via `PRIVATE-TOKEN` header when needed)
  and reconstructs unified diff text. Maps MR title/description.
- **Selection:** a small factory picks the first provider whose `matches(url)` is
  true (or an explicit `source` hint), analogous to `create_provider()` for review
  providers. Unknown hosts fail with a clear error.

Both implementations would use `httpx` with explicit timeouts and surface clear,
typed errors (invalid URL, not found, auth required, rate-limited).

## 4. Security considerations

- **Token handling.** Accept tokens **per request only**; do not persist them and
  do not put them in query strings. Pass them in headers to the upstream API.
- **Never log tokens.** Redact `Authorization` / `PRIVATE-TOKEN` headers and any
  token-bearing values in logs and error messages. Add a test asserting tokens
  never appear in serialized logs.
- **Avoid storing diffs by default.** Fetch, review, return — don't write the diff
  to disk/DB unless persistence is explicitly added and consented to.
- **Private repo considerations.** Require an explicit token for private resources;
  fail clearly (e.g. 401/403 mapped to a helpful message) rather than guessing.
  Consider an allowlist of hosts and an SSRF guard (only fetch known
  GitHub/GitLab hosts; reject internal/loopback addresses).
- **Rate limits & size caps.** Enforce a max diff size and handle upstream
  rate-limit responses gracefully.

## 5. Future API shape

A new endpoint that returns a normalized diff (which the client then submits to the
existing `POST /api/reviews`), keeping import and review cleanly separated:

```text
POST /api/import-diff
```

**Request**
```json
{
  "url": "https://github.com/acme/widgets/pull/42",
  "token": "optional-personal-access-token",
  "source": "github"
}
```

**Response (200)**
```json
{
  "diffText": "diff --git a/...\n@@ ...",
  "title": "Add rate limiting to the login endpoint",
  "description": "Fixes #41 ...",
  "source": "github",
  "stats": { "filesChanged": 3, "addedLines": 88, "removedLines": 12, "totalHunks": 5 }
}
```

**Error (clear and typed)** — e.g. `400` invalid/unsupported URL, `401/403` auth
required for a private resource, `404` not found, `413` diff too large, `429`
rate-limited, `502` upstream error. Bodies use `{ "detail": "..." }` like the rest
of the API.

Optionally, a future convenience could let `POST /api/reviews` accept a `url`
instead of `diffText` and import internally — but a separate `/api/import-diff`
keeps responsibilities clear and lets the UI preview the fetched diff before
running a review.

## 6. Sequencing: before or after real Bedrock integration?

**Recommendation: do Git provider import _before_ real Bedrock integration.**

Reasons:
- **Reuses everything, costs nothing.** Import feeds the *existing* mock pipeline,
  so it's demoable and valuable without any LLM spend.
- **Bigger demo payoff per unit of work.** "Paste a real PR URL and get a review"
  is a compelling story that's mostly an input adapter + one endpoint.
- **De-risks the AI work.** Real-world diffs (large, renames, binary, edge cases)
  will stress the parser; hardening it on real PRs first means the eventual
  Bedrock provider runs against battle-tested input.

**Tradeoffs / when to flip the order:**
- If the portfolio goal is specifically to show **LLM/Bedrock** skills, do Bedrock
  first — it's the headline capability, and import can follow.
- Import adds **security surface** (tokens, SSRF, rate limits) that must be done
  carefully; if you can't invest in that rigor yet, defer it.
- The two are independent (one is input, the other is the provider), so either
  order works — but import-first generally maximizes demo value at minimal cost.
