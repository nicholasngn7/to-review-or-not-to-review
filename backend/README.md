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

| Method | Path              | Description                                   |
| ------ | ----------------- | --------------------------------------------- |
| GET    | `/health`         | Liveness probe, returns `{"status":"ok"}`     |
| POST   | `/api/parse-diff` | Parse unified diff text into a `ParsedDiff`    |

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

## Tests

```bash
source .venv/bin/activate
python -m pytest          # or: python -m pytest -q
```

Parser tests live in `tests/test_diff_parser.py`.

## Layout

```text
app/
  main.py                  # FastAPI app + /health, includes routers
  models/                  # Pydantic contract (enums, diff, review)
  services/
    diff_parser.py         # unified-diff -> ParsedDiff
  api/routes/
    diff.py                # POST /api/parse-diff
tests/
  test_diff_parser.py
```

Future phases add the mock review engine and the `/api/review` endpoint.
