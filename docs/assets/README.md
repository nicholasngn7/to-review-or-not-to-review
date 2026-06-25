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

## Conventions

- **Format:** PNG.
- **Naming:** lowercase, hyphen-separated, descriptive (matching the table above).
- **Location:** this folder (`docs/assets/`); the README uses relative paths like
  `docs/assets/main-review-input.png`.
- **Content:** use only the built-in demo diffs — no real/proprietary code.
- Keep file sizes reasonable (resize/compress very large captures).
