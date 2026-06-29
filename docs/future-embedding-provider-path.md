# Future embedding-provider path (design only — not implemented in v0.4)

> **Status: design/seam documentation only.** v0.4 ships **one** embedding provider: a
> **deterministic local lexical provider**. This document describes how a *future* real
> provider (for example, an Amazon Bedrock embeddings model) **could** be added behind the
> existing seam. **No live provider, no network calls, no credentials, and no token/OAuth
> handling exist or are added here.** Nothing in this document is implemented in v0.4.

## 1. What exists today (v0.4)

The retrieval pipeline embeds text behind a small, explicit interface so the embedding
step is swappable. As shipped, only the local provider exists.

- **Interface:** `EmbeddingProvider` (a `Protocol` in
  `backend/app/services/knowledge/embedding.py`) with `provider_type`, `dimensions`,
  `embed_text`, `embed_chunk`, and `embed_chunks`.
- **Implemented provider:** `DeterministicLocalEmbeddingProvider` — a stdlib-only lexical
  **feature-hashing** vectorizer (default 128 dims): normalize → tokenize → hash tokens
  into signed buckets via SHA-1 → weight by term frequency → L2-normalize. It is
  deterministic across processes and runs, offline, and tagged
  `EmbeddingProviderType.DETERMINISTIC_LOCAL` (`"deterministic_local"`).
- **Where it plugs in:** `build_index(chunks, provider=None)` and
  `retrieve_context(..., provider=None)` both default to the deterministic local provider.
  Passing a different `EmbeddingProvider` instance is the entire extension point.
- **Reserved enum name (no implementation):** `EmbeddingProviderType` also defines
  `BEDROCK_OPTIONAL_FUTURE = "bedrock_optional_future"`. This is a **reserved name only** —
  there is no Bedrock client, no SDK dependency, no configuration, and no code path that
  uses it. It exists so the contract can name the future seam honestly.

This is **lexical, not semantic**. Similarity reflects shared tokens, not meaning. It is a
local **RAG architecture demo**, not production RAG and not semantic search.

## 2. The seam (how a future provider would attach)

A future provider would implement the **same** `EmbeddingProvider` interface and be
selected explicitly, mirroring how the review side already gates a non-default provider
(`REVIEW_PROVIDER=bedrock` returns a clear `501` until implemented — see
`docs/decisions.md`).

```text
RetrievalQuery / KnowledgeChunk
        │
        ▼
EmbeddingProvider.embed_text(...) / embed_chunk(...)        ← single swappable seam
        │
        ├── DeterministicLocalEmbeddingProvider   (implemented, default)
        └── <FutureProvider>                       (NOT implemented; design only)
        ▼
KnowledgeIndex (cosine top-k) → RetrievalResult[]
```

Proposed (not built) factory shape, analogous to the review-provider factory:

```text
create_embedding_provider(EMBEDDING_PROVIDER) -> EmbeddingProvider
  • unset / "deterministic_local"  -> DeterministicLocalEmbeddingProvider  (default)
  • "<future>"                     -> a provider that FAILS CLEARLY unless fully configured
  • unknown value                  -> raises a clear ValueError
```

## 3. Requirements for any future real provider

If and when a real embedding provider (e.g. Bedrock) is implemented, it **must**:

1. **Be explicitly configured.** Selected only via an explicit setting (e.g. an
   `EMBEDDING_PROVIDER` env var) **and** with all required configuration present.
2. **Be tested.** Shipped with its own tests before any documentation describes it as
   working or names the vendor.
3. **Be disabled by default.** The default remains the deterministic local provider; no
   real/paid/network provider is ever the default.
4. **Fail clearly when not configured.** If selected without valid configuration, it must
   raise an explicit, explanatory error (mirroring the review `bedrock` placeholder's
   `501`) — surfaced to the caller, never swallowed.
5. **Never silently fall back to fabricated vectors.** It must not return zeros, random,
   or local-provider vectors while *claiming* to be the real provider. No silent fallback,
   no fabricated embeddings.
6. **Keep vectors provider-tagged.** `EmbeddingVector.provider` must reflect the real
   provider so an index built with one provider is never mixed with another.
7. **Add no hidden network/credential behavior elsewhere.** Any network, credential, or
   token handling must live entirely inside that opt-in provider and be off by default.

## 4. Explicitly out of scope for v0.4

- No live Bedrock calls, no OpenAI or other paid provider calls.
- No network fetching, no URL fetching, no token/OAuth handling.
- No credentials, secrets, or cloud setup that claims to be implemented.
- No heavy dependencies (no vector DB, no ML/embedding SDKs).
- No semantic/neural embeddings, no production RAG, no LLM-generated findings, no
  autonomous/agentic behavior.

## 5. Honest wording to use

- ✅ “future provider seam”, “deterministic local lexical provider”,
  “disabled-by-default future provider path”, “not implemented in v0.4”.
- ❌ “Bedrock-powered”, “semantic embeddings”, “production RAG”, “LLM-generated findings”,
  “agentic reviewer”.

See also: [`v0.4-plan-rag-grounded-review.md`](v0.4-plan-rag-grounded-review.md) (§7, §14),
[`decisions.md`](decisions.md), and the embedding code in
`backend/app/services/knowledge/embedding.py`.
