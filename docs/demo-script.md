# MR Review Council — Demo Script & Recording Checklist

A script for a tight **60–90 second** screen recording that shows the full
review flow end to end. Everything uses the built-in demo diffs, so no real
merge request is needed.

> **Automated alternative:** short `.webm` demos are also recorded directly from real
> app interactions by the Playwright video specs (`frontend/demo/videos/`) — run
> `npm run demo:video:v0.1|v0.2|v0.3` (backend on :8000) to regenerate them into
> `docs/assets/videos/`. Record exact-version videos from `v0.1.0`/`v0.2.0`/`v0.3.0`
> worktrees; the v0.3 import video is a **local fixture-based demo**, not live
> GitHub/GitLab integration. `ffmpeg` conversion to `.mp4`/`.gif` is optional. This
> hand script remains useful for a narrated screen recording.

## 1. Goal of the demo

Show that MR Review Council takes a merge-request diff, reviews it through
multiple specialized personas, and produces a structured, actionable verdict —
clean for a low-risk change, and high-risk with detailed findings for a risky
one — plus a Markdown report you can paste into an MR/PR. Make clear it runs
**locally** behind a provider seam that a real AI model can plug into later.

## 2. Pre-recording setup

1. **Start the backend** (port 8000, default mock provider):
   ```bash
   cd backend && source .venv/bin/activate
   uvicorn app.main:app --port 8000
   ```
2. **Start the frontend:**
   ```bash
   cd frontend && npm run dev
   ```
3. **Load the app** in a clean browser window at the dev URL (e.g.
   `http://localhost:5173`).
4. **Recommended browser size:** ~**1440 × 900** (standard laptop viewport),
   retina/2x for crisp video. Close dev tools and unrelated tabs. Pre-scroll so
   the input panel is fully visible.
5. Have a Markdown previewer ready (e.g. VS Code Markdown preview) for the final
   step, and know your browser's download location.

> Tip: do a dry run once before recording so the steps feel smooth and you land
> inside the time budget.

## 3. Suggested narration

Keep it conversational; ~120 words total fits 60–90s comfortably.

- **Intro:** "This is MR Review Council — a multi-persona merge-request reviewer.
  It reviews a diff through several engineering perspectives and gives you a risk
  verdict and a merge recommendation."
- **Low-risk:** "I'll load a small frontend change with a matching test and run a
  review. The council runs the selected personas and comes back clean — low risk,
  ready to merge."
- **Risky:** "Now a risky backend auth change — secret handling, eval, a
  swallowed exception, no tests. This time it flags high risk and needs human
  review."
- **Explore:** "Each persona reports separately — I can switch reviewer tabs,
  filter by severity, and open detailed finding cards with file and line context."
- **Export:** "And I can export the full review as Markdown to drop into an MR or
  PR comment."
- **Close:** "It all runs locally behind a clean provider interface — today a
  deterministic mock, with an obvious seam to plug in Amazon Bedrock later."

## 4. Step-by-step demo flow

1. **Landing / review input** — Show the app: the Merge request panel (title,
   description, diff, persona selector) and the empty Review panel.
2. **Load low-risk demo** — Click **Load a demo diff → Low-risk frontend change**.
   Point out the fields auto-fill and personas pre-select (nothing runs yet).
3. **Run review** — Click **Run Review**.
4. **Clean result** — Show **Risk: Low**, **Ready** recommendation, the stats row,
   and the "No findings" clean state.
5. **Load risky demo** — Click **Load a demo diff → Risky backend auth change**
   (note the previous result stays until you re-run).
6. **Run review** — Click **Run Review**.
7. **Risky result** — Show **Risk: High** / **Needs human review** badges and the
   stats (note the High count). Then:
   - **Reviewer tabs** — click between Security / Backend / SRE / QA.
   - **Severity filter** — filter to **High** to isolate the most serious findings.
   - **Finding cards** — open/scroll a couple, highlighting file path, hunk/line
     reference, explanation, and recommendation.
8. **Export Markdown** — Click **Export Markdown** to download the `.md`.
9. **Show the report** — Open the downloaded file in a Markdown previewer and
   scroll briefly through the overview, summary, and findings grouped by reviewer.

## 4a. Optional segment — Import comments (local demo)

A short add-on showing the normalization boundary. Skip it for the 60s cut.

1. With the risky backend demo loaded, expand **Import comments (local demo)**.
2. Under **Load sample payload**, click **GitHub review comments** — it fills the
   provider, source, and JSON textarea with bundled synthetic data (no pasting
   needed). Then click **Normalize comments**.
3. Point out the **thread count**, any **warning**, and the **read-only preview**
   with file/line. (You can also click **GitHub issue comments** or **GitLab
   discussions** to show the other shapes.)
4. Click **Load imported threads** — they appear in the **Imported comments** group.
5. Click **Run Review** and show suggested replies generated for the imported
   thread, referencing its file/line.

> Say it plainly on-screen and in narration: *"This is a local, fixture-based demo —
> I'm pasting provider-shaped JSON. Nothing is fetched from GitHub or GitLab, no
> tokens are used, and no comments are posted anywhere."*

## 5. Timing guide (target ~75s)

| Section                         | Target time |
| ------------------------------- | ----------- |
| Intro + review input            | 0:00–0:10   |
| Low-risk demo: load + run + result | 0:10–0:25 |
| Risky demo: load + run          | 0:25–0:35   |
| Risky result: badges + stats    | 0:35–0:45   |
| Reviewer tabs + severity filter + finding cards | 0:45–1:00 |
| Export Markdown + show report   | 1:00–1:15   |
| Close / wrap                    | 1:15–1:25   |

If you need the short cut (60s), trim the finding-card exploration and the
closing line.

## 6. What to emphasize technically

Work these in naturally (narration or on-screen callouts) — they're the
portfolio signal:

- **React + TypeScript frontend** — component-driven UI, typed end to end.
- **Python + FastAPI backend** — `POST /api/reviews` drives the flow.
- **Pydantic contracts** — one source of truth, serialized to camelCase JSON and
  mirrored in TypeScript types.
- **Unified diff parser** — raw diff → structured files / hunks / lines / stats.
- **Multi-persona reviewer model** — 7 personas, each with its own focus and
  severity guidance, aggregated into one verdict.
- **Provider abstraction** — reviews sit behind a `ReviewProvider` interface;
  `REVIEW_PROVIDER` selects it, with a Bedrock placeholder showing the seam.
- **Local-first mock provider** — deterministic, offline, no credentials or cost.

## 7. What NOT to overclaim

Be explicit that this is an architecture/MVP demo, not a finished AI product:

- **No real AI calls yet** — findings come from a deterministic mock provider;
  `REVIEW_PROVIDER=bedrock` is a placeholder that returns a clear 501.
- **No GitLab/GitHub OAuth or API integration yet** — diffs are pasted, uploaded,
  or loaded from samples, not fetched from a real MR/PR.
- **The comment import panel is a local fixture-based demo** — it normalizes pasted
  (or bundled-sample) provider-shaped JSON; it does not fetch from GitHub/GitLab,
  require tokens, or post comments, and is **not** live provider integration. The
  "Load sample payload" buttons use **bundled synthetic data**, not real payloads.
- **No persistence yet** — reviews aren't stored; Markdown export is the way to
  keep a result.

## 8. v0.3 demo script — local comment import (60–90s)

A focused, standalone walkthrough of the **local, fixture-based** comment-import
path. It can follow the main demo or stand alone. Everything runs locally — there is
no GitHub/GitLab fetch, no tokens, and nothing is posted.

### Narration (~110 words)

- **Intro:** "MR Review Council can also work from *existing* review comments. To
  show the shape of that, v0.3 adds a local import demo."
- **Honesty line (say this clearly):** "This is a **local fixture-based import demo,
  not live GitHub/GitLab integration** — I'm loading bundled synthetic JSON. Nothing
  is fetched from a provider, no tokens or OAuth are involved, and nothing is posted."
- **Normalize:** "I pick a bundled sample — GitHub review comments — and normalize it.
  The backend maps that provider-shaped JSON into our comment-thread contract; I can
  see the thread count, any warnings, and a preview."
- **Run:** "I load those threads, run the review, and the council generates
  deterministic, copy-only suggested replies for each imported thread — with file and
  line context — which I can copy or export to Markdown."

### What to click, in order

1. **Load a demo diff → Risky backend auth change.**
2. Expand **Import comments (local demo)**. Point out: no URL field, no token field.
3. Under **Load sample payload**, click **GitHub review comments** (mention the
   **GitHub issue comments** / **GitLab discussions** buttons exist too). Note the
   provider, source, and JSON textarea auto-fill.
4. Click **Normalize comments** → show thread count, warnings, and the read-only
   preview.
5. Click **Load imported threads** → the **Imported comments** group appears.
6. Click **Run Review.**
7. Scroll to **Suggested replies** → show replies tied to the imported threads
   (file/line), use a **Copy** button, and/or **Export Markdown.**

### Timing guide (target ~75s)

| Section                                   | Target time |
| ----------------------------------------- | ----------- |
| Intro + honesty line                      | 0:00–0:12   |
| Load risky diff + open import panel       | 0:12–0:25   |
| Load sample + Normalize + preview         | 0:25–0:45   |
| Load imported threads + Run Review        | 0:45–0:58   |
| Suggested replies + copy/export + wrap    | 0:58–1:15   |

> Do not say "connected to GitHub/GitLab", "fetched the PR", or "posted a reply."
> The truthful framing is: *normalizes supplied provider-shaped JSON, locally.*

## 9. README blurb (for reference)

A short blurb linking here lives in the root README's **Demo video** section; the
recorded video can be added later (e.g. linked from the README or embedded as a
GIF in `docs/assets/`).
