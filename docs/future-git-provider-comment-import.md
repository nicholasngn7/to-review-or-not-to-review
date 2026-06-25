# Future Design: GitHub / GitLab Comment Import

> **Status: design notes only — not implemented.** MR Review Council has **no**
> GitHub/GitLab API calls, no OAuth, no token input, and no auto-posting. Today,
> existing review comment threads are entered **locally** through the
> `CommentThreads` input and flow into the review as `ReviewRequest.commentThreads`.
> This document sketches how *importing* real PR/MR comment threads would be added
> later, behind the **existing** `CommentThread` contract, so nothing downstream
> (suggested-reply generation, tone, UI, export) has to change.
>
> This is the comment-thread counterpart to
> [`future-git-provider-import.md`](future-git-provider-import.md) (which covers
> importing the **diff**). The two share an adapter pattern but are independent.

> **Implementation status.** The *fixture-based, network-free* foundation for this
> design is being built under [`v0.3-plan-git-comment-import-mappers.md`](v0.3-plan-git-comment-import-mappers.md):
> Phase 1 added the import contracts (`app/models/git_import.py`); Phase 2 added the
> shared mapper helpers and a pure **GitHub PR review-comment** mapper
> (`app/services/git_import/`) with a synthetic fixture; Phase 3 added a pure
> **GitHub PR issue-comment** mapper (`map_github_issue_comments_to_threads`) that
> maps line-less PR conversation comments to single-comment threads; Phase 4 added a
> pure **GitLab MR discussions** mapper (`map_gitlab_discussions_to_threads`) that
> maps one discussion → one thread with ordered notes (system notes filtered,
> positional file/line, resolved/outdated handling). The GitHub/GitLab payload shapes
> below and in the fixtures are **synthetic and tolerant** — they must be verified
> against official GitHub/GitLab API docs before any live integration. No live API
> calls, OAuth, tokens, endpoints, or UI exist yet.

## 1. Product goal

Let a user point at a real GitHub PR or GitLab MR and have its **existing review
comment threads** imported and normalized into the current `commentThreads`
contract, so the deterministic suggested-reply feature can draft replies to *real*
discussions — without any manual copy/paste of each comment.

Concretely: importing should produce a `list[CommentThread]` that is
indistinguishable, to the rest of the system, from threads typed in by hand. Import
is purely an **input adapter** in front of the unchanged pipeline:

```text
provider PR/MR  -->  adapter (normalize)  -->  CommentThread[]  -->  existing review/reply flow
```

## 2. Non-goals

- **No posting / no auto-posting.** Import is read-only. Drafted replies remain
  copy-only and `needsHumanReview: true`. Writing comments back is explicitly out
  of scope (see §13).
- **No OAuth flow, no stored credentials.** No login, no token vault, no refresh
  tokens. (A future, separate auth design would be required first.)
- **No persistence of imported content** by default. Fetch → normalize → review →
  return; nothing is written to disk/DB unless persistence is later designed and
  consented to.
- **No change to detection.** Imported threads never affect diff parsing, findings,
  severity, risk, or merge recommendation — exactly as local threads don't today.
- **No real AI/LLM calls.** Reply generation stays deterministic and local.
- **No new reviewer logic.** Routing, reviewer selection, confidence, and tone are
  unchanged; import only changes where threads *come from*.

## 3. Why this is design-only for now

- **Stabilize the local model first.** The `CommentThread` / `SuggestedReply`
  contract is new (Phases 14–16). Importing real-world data should only happen once
  that shape is proven and stable, so the adapter has a fixed target.
- **Security surface is significant.** Tokens, scopes, SSRF, rate limits, and
  private-repo handling are real work that shouldn't gate the core feature or be
  rushed.
- **Demo value without spend.** The local input already demonstrates the end-to-end
  reply feature; import is an enhancement, not a prerequisite.

## 4. Proposed normalized provider model

These types live in a **new adapter layer** and never leak provider-specific JSON
into the core contract. Backend names use `snake_case`; the API stays `camelCase`
via the existing `CamelModel` convention.

### 4.1 Provider identity

```python
# app/services/git_comment_import/types.py  (illustrative)
from enum import Enum

class GitProviderType(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"

class GitProvider(CamelModel):
    """A configured provider host the importer knows how to talk to."""
    type: GitProviderType
    base_url: str            # e.g. "https://github.com" / "https://gitlab.com" / self-hosted
    api_base_url: str        # e.g. "https://api.github.com" / "https://gitlab.com/api/v4"
    display_name: str
```

### 4.2 External reference (provenance, never lossy)

```python
class ExternalCommentReference(CamelModel):
    """Stable, provider-specific identity preserved for round-tripping / dedupe.

    This is the anchor that a *future, separate* posting design would need. We
    capture it now so imported threads are traceable, even though we never write back.
    """
    provider: GitProviderType
    # Where the thread lives:
    project: str                       # "owner/repo" (GitHub) or project path/id (GitLab)
    merge_request_iid: int | None = None   # GitLab MR iid
    pull_request_number: int | None = None # GitHub PR number
    # Provider-native thread/discussion identity:
    discussion_id: str | None = None   # GitLab discussion id
    review_id: str | None = None       # GitHub review id (if part of a review)
    comment_id: str | None = None      # provider comment/note id (root of the thread)
    web_url: str | None = None         # human-openable link to the comment/thread
    kind: str | None = None            # "review_comment" | "issue_comment" | "discussion_note"
```

### 4.3 Imported thread (superset of the local contract)

```python
class ImportedCommentThread(CamelModel):
    """An imported thread plus provenance. `to_comment_thread()` returns the
    *existing* CommentThread used by the rest of the system."""
    thread: CommentThread                  # the normalized, contract-shaped thread
    external: ExternalCommentReference      # provider-specific identity/links
    imported_at: datetime
```

The importer returns `list[ImportedCommentThread]`; the review pipeline consumes
`[i.thread for i in imported]` as `ReviewRequest.commentThreads`. The `external`
side-car is optional metadata the UI can use for "open on GitHub/GitLab" links and
that a future poster would need — but the **core contract is untouched**.

### 4.4 Request shapes

```python
class ImportDiffRequest(CamelModel):
    """(Cross-references future-git-provider-import.md.) Import just the diff."""
    url: str                       # PR/MR URL
    provider: GitProviderType | None = None   # optional hint; else inferred from URL
    token: str | None = None       # per-request only; never stored (see §9)

class ImportCommentsRequest(CamelModel):
    """Import existing comment threads from a PR/MR."""
    url: str
    provider: GitProviderType | None = None
    token: str | None = None
    include_resolved: bool = True  # whether to import resolved/outdated threads
    include_outdated: bool = False # threads anchored to lines no longer in the diff
    max_threads: int | None = None # safety cap (see §11)
```

A combined convenience (import diff **and** comments in one call) could exist later,
but keeping `ImportDiffRequest` and `ImportCommentsRequest` separate mirrors the
existing clean split between *diff input* and *comment input*.

## 5. GitHub / GitLab adapter boundary

A small interface mirroring the existing `ReviewProvider` pattern (interface +
concrete implementations, chosen by a factory). Adapters are the **only** code that
knows provider JSON; everything above them speaks `CommentThread`.

```python
class GitCommentImporter(ABC):
    provider_type: GitProviderType
    def matches(self, url: str) -> bool: ...
    def import_comments(
        self, req: ImportCommentsRequest
    ) -> list[ImportedCommentThread]: ...
```

- **`GitHubCommentImporter`** — recognizes `github.com/.../pull/<n>`. Reads PR
  **review comments** (line-anchored, grouped into threads via
  `in_reply_to_id` / pull-request review threads) and PR-level **issue comments**.
- **`GitLabCommentImporter`** — recognizes `gitlab.com/.../-/merge_requests/<n>`.
  Reads MR **discussions**, each containing ordered **notes**; positional notes
  carry file/line, non-positional notes are MR-level discussion.
- **Selection:** a factory picks the first importer whose `matches(url)` is true (or
  an explicit `provider` hint), analogous to `create_provider()` for review
  providers. Unknown hosts fail with a clear, typed error.

All network access would use `httpx` with explicit timeouts; adapters translate
provider errors into the typed errors in §10.

## 6. How imported threads map into the existing `CommentThread`

The existing local contract is the target. Mapping rules:

| `CommentThread` field | Source |
| --- | --- |
| `id`              | A stable synthetic id derived from provider identity (e.g. `github:owner/repo#42:disc:<id>`), so re-imports are idempotent. The provider-native id is also kept in `ExternalCommentReference`. |
| `filePath`        | The comment's anchored file path (`path` on GitHub; `position.new_path`/`old_path` on GitLab). `null` for PR/MR-level (non-positional) comments. |
| `line`            | The anchored line (see §7.3). `null` when not line-anchored or outdated. |
| `status`          | Mapped to the existing `CommentThreadStatus` (see §7.4). |
| `comments[]`      | Each provider comment/note → one `ThreadComment` (see below). |

`ThreadComment` mapping:

| `ThreadComment` field | Source |
| --- | --- |
| `id`     | Provider comment/note id (stringified). |
| `author` | Comment author login/username (display only). |
| `body`   | Comment text, trimmed; empty/whitespace-only comments are dropped (the existing validator already forbids empty bodies). |

Threads with **no** non-empty comments after normalization are skipped (the contract
requires ≥1 comment per thread).

## 7. Normalization details

### 7.1 GitHub PR review comments

- Line-anchored comments on the diff. GitHub groups replies via `in_reply_to_id`
  (and, in the GraphQL API, `PullRequestReviewThread`). Reconstruct each thread as
  the root comment + its replies in chronological order.
- One `CommentThread` per review thread; `filePath` = `path`, `line` = resolved line
  (§7.3).

### 7.2 GitHub issue comments on PRs

- PR conversation comments are **issue comments** (no file/line). Map each to a
  single-comment `CommentThread` with `filePath = null`, `line = null`. Because
  there's no native threading, each issue comment is its own thread unless a future
  heuristic groups them.

### 7.3 GitLab MR discussions / notes & file/line mapping

- A GitLab **discussion** → one `CommentThread`; its ordered **notes** →
  `ThreadComment`s. System notes (e.g. "changed the description") are filtered out.
- **File/line mapping is the tricky part.** Providers expose old-side and new-side
  positions:
  - Prefer the **new-side** line (`position.new_line` / GitHub `line`/`original_line`)
    so the anchor matches the current diff the reviewer is looking at.
  - Fall back to the old-side line when only that exists (e.g. comments on removed
    lines); record which side was used in `ExternalCommentReference` if useful.
  - When a comment is **outdated** (anchored to a line no longer present), keep
    `filePath` but set `line = null` and mark the thread accordingly, rather than
    guessing a wrong line.

### 7.4 Resolved / unresolved state

- GitLab discussions expose `resolved` / `resolvable`; GitHub review threads expose
  `isResolved` (GraphQL). Map:
  - resolved → `CommentThreadStatus.RESOLVED`
  - unresolved/open → `CommentThreadStatus.OPEN`
  - outdated-but-unresolved → `OPEN` (with file kept, line nulled per §7.3); if the
    enum later grows an `OUTDATED` value, use it.
- When the provider doesn't expose resolution state, default to `OPEN`.

## 8. Preserving provider-specific thread/discussion IDs

Provider-native identity is **never discarded**. It is preserved in
`ExternalCommentReference` (`discussion_id`, `review_id`, `comment_id`, `web_url`,
`project`, PR/MR number). This enables:

- **Idempotent re-import / dedupe** — the synthetic `CommentThread.id` is derived
  deterministically from this identity, so importing the same PR twice yields the
  same thread ids.
- **"Open in GitHub/GitLab" links** in the UI via `web_url`.
- **A future, separate posting design** — replying to the *correct* discussion/note
  requires exactly these ids. We capture them now even though we never write back.

## 9. Token handling considerations

- **Per-request only.** Tokens (if ever accepted) are passed in the request body for
  a single import and are **never persisted**, logged, cached, or echoed back.
- **Headers, not URLs.** Send via `Authorization: Bearer …` (GitHub) /
  `PRIVATE-TOKEN: …` (GitLab) — never in query strings (avoids referer/proxy/log
  leakage).
- **Least privilege.** Document the minimal scopes (read-only repo/MR read); never
  request write scopes for an import-only feature.
- **Public-first.** Public PR/MR comments should work with no token at all; tokens
  are only for private resources.
- **Not in v0.2.** This phase adds **no** token input; this section is forward-looking.

## 10. Security considerations

- **SSRF guard / host allowlist.** Only fetch known provider hosts (and explicitly
  configured self-hosted instances). Reject internal/loopback/link-local addresses
  and non-`https` URLs.
- **Input validation.** Strictly parse and validate PR/MR URLs before any network
  call; reject ambiguous or non-matching URLs with a typed error.
- **Output sanitization.** Treat imported comment bodies as untrusted text — the
  React UI renders them as text (no HTML injection); Markdown export should not
  introduce injection either.
- **Size & count caps.** Cap thread count (`max_threads`) and per-comment size to
  prevent resource exhaustion from huge PRs.
- **Fail closed.** Any uncertainty (unknown host, unparseable position) results in a
  clear error or a safely-degraded thread, never a guessed write target.

## 11. Rate-limit considerations

- **Respect upstream limits.** Read GitHub `X-RateLimit-Remaining` / `Retry-After`
  and GitLab equivalents; surface a typed `429` with a helpful message rather than
  hammering.
- **Minimize calls.** Prefer batched/paginated endpoints (and GraphQL on GitHub) to
  fetch review threads efficiently; bound pagination with `max_threads`.
- **Backoff.** Use bounded exponential backoff with jitter on `429`/`5xx`, with an
  overall deadline so the import endpoint stays responsive.

## 12. Privacy / logging considerations

- **Never log tokens or full comment bodies.** Redact `Authorization` /
  `PRIVATE-TOKEN`. Log only coarse metadata (provider, project, counts, timing) at
  info level; bodies only at debug behind an explicit, off-by-default flag.
- **No retention by default.** Don't persist imported threads or diffs; they live
  for the duration of the request/review only.
- **Author data minimization.** Store only what the UI needs (a display author);
  avoid collecting emails or other PII from the provider.
- **Add a redaction test** asserting tokens never appear in serialized logs/errors
  (mirrors the diff-import design).

## 13. Error handling

Typed, user-meaningful errors mapped to the existing `{ "detail": "..." }` shape:

| Condition | Suggested status |
| --- | --- |
| Invalid/unsupported URL | `400` |
| Auth required (private resource, no/invalid token) | `401` / `403` |
| PR/MR not found | `404` |
| Too many threads / payload too large | `413` |
| Upstream rate-limited | `429` (pass through `Retry-After`) |
| Upstream/provider error or timeout | `502` |

Partial success is acceptable and explicit: if some threads fail to normalize, the
importer can return the good ones plus a structured warning, rather than failing the
whole import.

## 14. Test strategy

All against **recorded fixtures / stubbed HTTP** — no live network in tests.

- **Adapter unit tests** with captured GitHub/GitLab JSON fixtures:
  - review comments grouped into the right threads (reply chains preserved/ordered),
  - issue comments → single-comment, line-less threads,
  - GitLab discussions/notes → threads with system notes filtered out,
  - file/line mapping (new-side preferred, old-side fallback, outdated → line null),
  - resolved/unresolved/outdated → `CommentThreadStatus`,
  - empty/whitespace bodies dropped; empty threads skipped.
- **Contract conformance:** the output is valid `CommentThread[]` (passes existing
  validators) and feeds `run_review` unchanged.
- **Invariance:** importing threads (vs. typing the same threads locally) yields
  identical suggested replies, routing, confidence, findings, risk, and
  recommendation. Import must be presentation/provenance only.
- **Idempotency:** importing the same PR/MR twice yields identical `CommentThread.id`s.
- **Security/privacy:** SSRF guard rejects internal hosts; tokens never appear in
  logs/errors; size/count caps enforced.
- **Error mapping:** each condition in §13 maps to the right status and `detail`.

## 15. Suggested implementation phases

1. **Contract & adapter interface (no network).** Add the normalized types
   (`GitProviderType`, `GitProvider`, `ExternalCommentReference`,
   `ImportedCommentThread`, `ImportCommentsRequest`) and the `GitCommentImporter`
   interface + factory. Pure mapping functions tested against fixtures.
2. **GitHub adapter (public, no token).** Implement review + issue comment import
   for public PRs against fixtures, then behind a real (rate-limited) call.
3. **GitLab adapter (public, no token).** MR discussions/notes with file/line
   mapping.
4. **Endpoint + UI preview.** `POST /api/import-comments` returning normalized
   threads; UI lets the user paste a PR/MR URL, preview imported threads, then run a
   review (reusing the existing reply flow). Add "open on provider" links.
5. **Private-resource support (token, security).** Per-request token, SSRF guard,
   host allowlist, redaction, rate-limit/backoff, size caps — the full security pass.
6. **(Separate, gated) posting design.** Only after all of the above is stable and
   trusted — see §13/§16.

## 16. Why auto-posting remains deferred

Posting replies back to real PRs/MRs is **high-risk and effectively irreversible**
(a wrong/noisy comment is publicly visible and damages trust). It would require, at
minimum: authentication & permissioning, a human **preview/confirm** step,
**auditability** (who posted what, when), and **duplicate-prevention** (idempotency
keyed on `ExternalCommentReference`). Until those safeguards exist, replies stay
**copy-only** with `needsHumanReview: true`. Auto-posting, if ever built, is a
deliberate, separate, gated phase *after* import — never bundled with it.
