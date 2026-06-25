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

| Method | Path      | Description                          |
| ------ | --------- | ------------------------------------ |
| GET    | `/health` | Liveness probe, returns `{"status":"ok"}` |

Interactive API docs are available at `http://localhost:8000/docs` while the
server is running.

## Layout

```text
app/
  main.py     # FastAPI app + /health
```

Future phases add `models/` (Pydantic schemas), `services/` (diff parser, review
engine, providers), and `api/routes/` (the `/api/review` endpoint).
