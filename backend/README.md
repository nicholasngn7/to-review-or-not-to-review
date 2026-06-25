# MR Review Council — Backend

FastAPI service for MR Review Council.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Path              | Description                                    |
| ------ | ----------------- | ---------------------------------------------- |
| GET    | `/health`         | Liveness probe, returns `{"status":"ok"}`      |
| POST   | `/api/parse-diff` | Parse unified diff text into a `ParsedDiff`     |
| POST   | `/api/reviews`    | Run selected personas, return a `ReviewResponse` |

Interactive API docs are available at `http://localhost:8000/docs` while the
server is running.

### `POST /api/parse-diff`

Request body:

```json
{ "diffText": "diff --git a/app.py b/app.py\n@@ -1,2 +1,3 @@\n ..." }
```

Sample curl (run with the server up on port 8000):

```bash
curl -s -X POST http://localhost:8000/api/parse-diff \
  -H 'Content-Type: application/json' \
  -d '{"diffText":"diff --git a/app/calc.py b/app/calc.py\n--- a/app/calc.py\n+++ b/app/calc.py\n@@ -1,2 +1,3 @@\n def add(a, b):\n-    return a + b\n+    # sum\n+    return a + b\n"}'
```

The response is the structured `ParsedDiff` (files, hunks, lines, and stats) in
camelCase JSON. See [`../docs/review-contract.md`](../docs/review-contract.md).

### `POST /api/reviews`

Runs the selected reviewer personas over a diff with the deterministic mock
engine (no AI) and returns a `ReviewResponse`.

Request body (`ReviewRequest`):

```json
{
  "diffText": "diff --git a/app.py b/app.py\n@@ ...",
  "selectedPersonas": ["security", "qa"],
  "title": "optional",
  "description": "optional",
  "source": "optional"
}
```

Sample curl:

```bash
curl -s -X POST http://localhost:8000/api/reviews \
  -H 'Content-Type: application/json' \
  -d '{"diffText":"diff --git a/app/config.py b/app/config.py\n--- a/app/config.py\n+++ b/app/config.py\n@@ -1,1 +1,3 @@\n import os\n+API_TOKEN = \"abc123\"\n+result = eval(data)\n","selectedPersonas":["security","qa"]}'
```

The response includes `overallRisk`, `mergeRecommendation`, `summary`,
`diffStats`, `personaReviews`, and a flattened `findings` list.

## Review providers

Review generation sits behind a `ReviewProvider` interface
(`app/services/providers/base.py`). The engine parses the diff, asks the
configured provider for one `PersonaReview` per selected persona, and aggregates
the result — the API response contract is identical regardless of provider.

Provider selection is controlled by the `REVIEW_PROVIDER` environment variable:

| Value     | Behavior                                                              |
| --------- | -------------------------------------------------------------------- |
| `mock`    | **Default.** Deterministic, offline heuristics. No AI, no creds.     |
| `bedrock` | Placeholder seam. Fails with a clear `501` — not implemented yet.    |

```bash
# Default (mock) — fully local:
uvicorn app.main:app --reload --port 8000

# Explicitly select a provider:
REVIEW_PROVIDER=mock uvicorn app.main:app --reload --port 8000

# Bedrock placeholder: /api/reviews returns 501 with an explanatory message.
REVIEW_PROVIDER=bedrock uvicorn app.main:app --reload --port 8000
```

An unknown value (e.g. `REVIEW_PROVIDER=foo`) fails fast with a `ValueError`
listing the valid options. Persona definitions (focus, output expectations,
severity guidance) live in `app/personas/registry.py` and are shared by the mock
provider and any future LLM provider. Real AI calls are intentionally deferred
(no paid API usage, no AWS credentials required to run locally).

## Tests

```bash
source .venv/bin/activate
python -m pytest          # or: python -m pytest -q
```

Parser tests live in `tests/test_diff_parser.py`; provider/config tests live in
`tests/test_providers.py`.

## Layout

```text
app/
  main.py                  # FastAPI app + /health, routers, 501 handler
  core/
    config.py              # Settings + REVIEW_PROVIDER selection
  personas/
    registry.py            # PersonaSpec registry (focus / output / severity)
  models/                  # Pydantic contract (enums, diff, review)
  services/
    diff_parser.py         # unified-diff -> ParsedDiff
    review_engine.py       # select provider + aggregate ReviewResponse
    providers/
      base.py              # ReviewProvider interface
      mock_provider.py     # deterministic per-persona heuristics (default)
      bedrock_provider.py  # placeholder seam (raises NotImplementedError)
      __init__.py          # create_provider() factory + validation
  api/routes/
    diff.py                # POST /api/parse-diff
    reviews.py             # POST /api/reviews
tests/
  test_diff_parser.py
  test_review_engine.py
  test_reviews_route.py
  test_providers.py
```

A real AI provider (Bedrock/OpenAI/Anthropic) implements `ReviewProvider` and
slots in behind `REVIEW_PROVIDER`; the rest of the engine is unchanged.
