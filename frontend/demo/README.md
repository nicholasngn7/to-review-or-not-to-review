# Demo automation (Playwright)

Selector-driven Playwright specs that capture **real** screenshots and short `.webm`
videos of MR Review Council. Nothing here fetches from GitHub/GitLab, uses tokens or
OAuth, or posts anything — flows use only built-in sample diffs and **bundled
synthetic** import samples. The v0.3 import demo is a **local fixture-based demo, not
live GitHub/GitLab integration**.

## Layout

```
demo/
  helpers/      flows.ts, selectors.ts, waitForReview.ts, screenshot.ts, video.ts
  screenshots/  v0.1|v0.2|v0.3|v0.4.screenshots.spec.ts  -> docs/assets/screenshots/vX/*.png
  videos/       v0.1|v0.2|v0.3|v0.4.video.spec.ts          -> docs/assets/videos/*.webm
  demo-harness.smoke.spec.ts
```

> **v0.4 (retrieval grounding).** `v0.4.*.spec.ts` ground a review on **local, allow-listed**
> repo docs (`README.md`, `docs/*`) via the **deterministic, lexical, provenance-only**
> retriever and capture the context-sources input, the "Retrieved local context" panel, a
> finding's "Cited context", and the Markdown export's "Context used" section. Nothing is
> fetched from any provider, no tokens/OAuth, no semantic search, no Bedrock/OpenAI. Specs
> `test.skip` if the v0.4 UI / context is absent.

## Backend requirement

The Vite dev server (`:5173`) proxies `/api` to the backend (`:8000`). Any capture
that **runs a review or normalizes imported comments needs the backend running** on
`:8000`. The smoke test does not.

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000
```

## Scripts (run from `frontend/`)

```bash
npm run demo:install-browsers   # one-time: install Chromium
npm run demo:smoke              # harness sanity check (no backend, no assets)

npm run demo:screenshots        # all screenshot specs (current checkout)
npm run demo:screenshots:v0.1   # one milestone
npm run demo:screenshots:v0.4   # v0.4 retrieval-grounding screenshots (needs backend)
npm run demo:video              # all video specs (current checkout)
npm run demo:video:v0.3         # one milestone
npm run demo:video:v0.4         # v0.4 retrieval-grounding video (needs backend)
npm run demo:all                # smoke + screenshots + videos (current checkout)
```

## Current-harness capture (simplest)

The current checkout is the latest version, so running a spec here captures the
**current app**. For the matching latest milestone (today: v0.4) this is exact; for
older milestone names it is a truthful **milestone-style fallback**, not an exact
historical build. The specs `test.skip` (and discard any throwaway recording) when a
version's defining feature is absent, so they never write a misleading file.

## Exact-version capture (recommended for v0.1 / v0.2)

Older tags (`v0.1.0`, `v0.2.0`) **do not contain these `demo:*` scripts**. So run the
**historical app** from a tag worktree, but run the **current** Playwright harness from
this checkout against it via `DEMO_BASE_URL`. When `DEMO_BASE_URL` is set, the bundled
`webServer` is disabled and Playwright attaches to the already-running historical app.

```bash
# 1) Create a worktree for the tag
git worktree add ../mrrc-v0.1 v0.1.0

# 2) Start the v0.1 backend (:8000)
cd ../mrrc-v0.1/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# 3) Start the v0.1 frontend (:5173) — in another terminal
cd ../mrrc-v0.1/frontend
npm install
npm run dev -- --port 5173

# 4) Capture with the CURRENT harness against the historical app — another terminal
cd frontend   # the PRIMARY checkout (this repo)
DEMO_BASE_URL=http://localhost:5173 npm run demo:screenshots:v0.1
DEMO_BASE_URL=http://localhost:5173 npm run demo:video:v0.1

# 5) Tear down
git worktree remove ../mrrc-v0.1
```

Assets are written into **this checkout's** `docs/assets/screenshots/vX/` and
`docs/assets/videos/` (the screenshot/video paths are relative to the primary
`frontend/`), so no copying between trees is needed. Repeat with `v0.2.0` →
`demo:*:v0.2`, and `v0.3.0` → `demo:*:v0.3`.

## DEMO_BASE_URL

- Unset (default): targets `http://localhost:5173` and auto-starts this checkout's
  `npm run dev`.
- Set: targets that URL and does **not** start a dev server (you start the historical
  app yourself).

## Asset size

Videos are small WebM (the v0.3 demo is well under 1 MB), so regular Git is fine. If
videos grow large later, Git LFS is an **optional** choice — not configured here.
