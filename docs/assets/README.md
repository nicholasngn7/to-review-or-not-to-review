# Screenshots & demo assets

This folder holds the screenshots and (later) demo videos referenced by the root
[`README.md`](../../README.md).

## Canonical layout (v0.1+ structured)

Screenshots are now organized by milestone and generated from the **real running app**
by the Playwright demo specs (`frontend/demo/screenshots/`):

```
docs/assets/screenshots/v0.1/   v0.1-core-review-input.png, v0.1-review-results.png, v0.1-markdown-export.png
docs/assets/screenshots/v0.2/   v0.2-reviewer-tone-panel.png, v0.2-comment-threads-input.png, v0.2-suggested-replies.png
docs/assets/screenshots/v0.3/   v0.3-import-sample-panel.png, v0.3-normalized-import-preview.png,
                                v0.3-imported-threads-review-results.png, v0.3-suggested-replies-from-imported-comments.png
docs/assets/videos/             mr-review-council-v0.{1,2,3}-*.webm (recorded from real app interactions)
```

**Generation status:** **all three sets are generated from their exact release tags.**
The **v0.3** set is from the `v0.3.0` tree (current checkout). The **v0.1** and **v0.2**
sets were captured by running the **current** harness against the **historical** app
started from a `v0.1.0` / `v0.2.0` worktree, using `DEMO_BASE_URL` (the old tags do
**not** contain the `demo:*` scripts). See
[`../demo-automation-plan.md`](../demo-automation-plan.md) §1 and
[`../../frontend/demo/README.md`](../../frontend/demo/README.md) for the exact workflow.

```bash
# From the frontend dir, with the backend running on :8000.
# A bare run targets the CURRENT app (exact for the latest version = v0.3 today;
# a milestone-style fallback if used for an older version's folder):
npm run demo:screenshots          # all specs (current app)
npm run demo:screenshots:v0.3     # v0.3 specs only

# Exact v0.1/v0.2 (how the committed v0.1/v0.2 assets were produced): start the
# historical app from a worktree, then point the current harness at it (this does
# NOT auto-start this checkout's dev server):
DEMO_BASE_URL=http://localhost:5173 npm run demo:screenshots:v0.1
DEMO_BASE_URL=http://localhost:5173 npm run demo:video:v0.1
```

> The legacy flat filenames in the table below (`main-review-input.png`,
> `risky-review-dashboard.png`, `markdown-export.png`) are **superseded** by the
> structured `screenshots/v0.1/` names above and are kept only as historical
> capture notes.

## Images to capture

| Filename                       | What it shows                | App state to set up                                                                 |
| ------------------------------ | ---------------------------- | ----------------------------------------------------------------------------------- |
| `main-review-input.png`        | Main review input screen     | Fresh load, **Low-risk frontend change** demo loaded (title/description/diff filled, personas pre-selected), *before* clicking Run Review. |
| `risky-review-dashboard.png`   | Risky backend review dashboard | **Risky backend auth change** demo loaded and **Run Review** clicked. Show the verdict badges (Risk: High / Needs human review), stats, reviewer tabs, and finding cards. |
| `markdown-export.png`          | Markdown export output       | The exported `.md` report (from the risky review) opened in a Markdown previewer or editor, showing the overview, summary, and findings grouped by reviewer. |

### v0.3 — Local comment import demo

> All four use **bundled synthetic sample payloads** only — no real repos/people,
> no provider fetch, no tokens. (See [`frontend/src/fixtures/importSamples.ts`](../../frontend/src/fixtures/importSamples.ts).)

| Filename                                          | What it shows                          | App state to set up                                                                                                                              |
| ------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `v0.3-import-sample-panel.png`                    | Import panel + sample buttons          | Risky backend demo loaded. Expand **Import comments (local demo)**. Show the **Load sample payload** buttons, provider/source selectors, and the (empty or sample-filled) JSON textarea — **before** clicking Normalize. Make clear there is no URL/token field. |
| `v0.3-normalized-import-preview.png`              | Normalized import preview              | Click a sample (e.g. **GitHub review comments**), then **Normalize comments**. Show the thread count, any warnings, and the read-only thread preview. |
| `v0.3-imported-threads-review-results.png`        | Review results from imported threads   | After **Load imported threads** and **Run Review**. Show the verdict badges/stats with the imported threads having driven the run.                |
| `v0.3-suggested-replies-from-imported-comments.png`| Suggested replies from imported comments | Same review, scrolled to the **Suggested replies** section, showing deterministic copy-only replies with file/line context for the imported threads. |

## How to capture

1. Start the backend on port 8000 and the frontend dev server (see the root
   README's [Local setup](../../README.md#local-setup)).
2. Open the app in your browser.
3. **Recommended browser size:** ~**1440 × 900** (a standard laptop viewport).
   Use a clean window with no dev tools open. A device-pixel-ratio of 2 (retina)
   produces crisp images.
4. Capture each state from the table above. Prefer a full-window or
   panel-focused capture rather than the whole desktop.
5. For `markdown-export.png`, click **Export Markdown**, then open the downloaded
   file (e.g. in VS Code's Markdown preview or any Markdown viewer) and screenshot
   the rendered report.
6. For the **v0.3 import** shots, follow the
   [v0.3 demo flow](../../README.md#v03-demo-flow): load the risky diff, open
   **Import comments (local demo)**, click a **Load sample payload** button,
   **Normalize comments**, **Load imported threads**, then **Run Review**. Capture
   each of the four states from the v0.3 table above in order.

## Automation

A Playwright **demo harness** exists (`frontend/playwright.config.ts`,
`frontend/demo/`) — see [`demo-automation-plan.md`](../demo-automation-plan.md).
**Phase B added screenshot capture specs** (`frontend/demo/screenshots/`) and
**Phase C added video specs** (`frontend/demo/videos/`), with the
`demo:screenshots[:vX]` and `demo:video[:vX]` scripts (and `demo:all`). Videos are
**recorded from real app interactions** and written to [`videos/`](videos/) as `.webm`:

```bash
cd frontend && npm run demo:video           # all video specs (current tree)
cd frontend && npm run demo:video:v0.3      # one milestone
```

Video files:

- `videos/mr-review-council-v0.1-core-review-demo.webm` — **recorded from the `v0.1.0` tag** (~0.5 MB)
- `videos/mr-review-council-v0.2-suggested-replies-demo.webm` — **recorded from the `v0.2.0` tag** (~0.7 MB)
- `videos/mr-review-council-v0.3-local-import-demo.webm` — **recorded from the `v0.3.0` tag** (~0.8 MB)

`ffmpeg` conversion to `.mp4`/`.gif` is **optional**, e.g.:

```bash
ffmpeg -i videos/mr-review-council-v0.3-local-import-demo.webm videos/mr-review-council-v0.3-local-import-demo.mp4
```

The harness uses the conventions below (1440×900 @ 2x, Chromium) and drives only
built-in sample diffs and bundled synthetic import samples — no provider fetch,
tokens, OAuth, or posting. The v0.3 import video is a **local fixture-based demo**, not
live GitHub/GitLab integration.

## Conventions

- **Format:** PNG.
- **Naming:** lowercase, hyphen-separated, descriptive (matching the table above).
- **Location:** this folder (`docs/assets/`); the README uses relative paths like
  `docs/assets/main-review-input.png`.
- **Content:** use only the built-in demo diffs — no real/proprietary code.
- Keep file sizes reasonable (resize/compress very large captures).
