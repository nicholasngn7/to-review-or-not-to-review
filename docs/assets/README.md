# Screenshots & demo assets

This folder holds the screenshots referenced by the root [`README.md`](../../README.md).
Images are intentionally **not committed yet** — capture them locally and drop
them in here with the exact filenames below.

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

## Conventions

- **Format:** PNG.
- **Naming:** lowercase, hyphen-separated, descriptive (matching the table above).
- **Location:** this folder (`docs/assets/`); the README uses relative paths like
  `docs/assets/main-review-input.png`.
- **Content:** use only the built-in demo diffs — no real/proprietary code.
- Keep file sizes reasonable (resize/compress very large captures).
