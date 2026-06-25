# Demo Automation Plan — MR Review Council (v0.1 / v0.2 / v0.3)

> **Status: Phase A implemented (harness only).** The Playwright scaffold and reusable
> demo flow helpers now exist; **no screenshots or videos are generated yet**. The
> remaining phases (screenshot specs, video specs, docs wiring) are still planning.
> This document describes *how* we will generate screenshots and short demo videos for
> each milestone.
>
> **Phase A — added (frontend):**
> - `@playwright/test` as a **dev dependency** (Chromium installed via
>   `npm run demo:install-browsers`).
> - `frontend/playwright.config.ts` — `testDir: ./demo`, baseURL `:5173`, viewport
>   1440×900 @ 2x, Chromium, `screenshot: "only-on-failure"`, `video: "off"`,
>   `webServer` that reuses or starts `npm run dev` (frontend only; it does **not**
>   start the backend). Exports `DEMO_VIDEO_DIR = "../docs/assets/videos"` for Phase C.
> - `frontend/demo/helpers/selectors.ts`, `waitForReview.ts`, `flows.ts` — the ten
>   reusable, version-tolerant flows (each post-v0.1 feature has an `...IfAvailable`
>   no-op variant).
> - `frontend/demo/demo-harness.smoke.spec.ts` — loads `/`, asserts the shell renders;
>   no captures, no backend needed, no v0.2/v0.3-only dependencies.
> - `package.json` scripts: `demo:smoke`, `demo:install-browsers`.
> - Vitest scoped to `src/**` so it never collects the Playwright `demo/` specs;
>   `demo/.artifacts/` and Playwright report dirs are gitignored.
>
> **Honesty guardrails (must hold in any future implementation):** demos use only the
> built-in sample diffs and **bundled synthetic import samples**. No real
> GitHub/GitLab data, no live provider calls, no OAuth, no token input, no URL
> fetching, no posting, and no real AI/LLM. Captions/voiceover must never claim live
> GitHub/GitLab integration — the v0.3 import is a **local fixture-based demo**.

## 0. Repo findings (inspected)

| Fact | Value |
| ---- | ----- |
| Tags present | `v0.1.0`, `v0.2.0`, `v0.3.0` all exist |
| `v0.1.0` commit | `b0f2991` |
| `v0.2.0` commit | `fcd871f` |
| `v0.3.0` commit | `481a1dc` (current HEAD content) |
| Frontend dev server | Vite on **`http://localhost:5173`** |
| API proxy | Vite proxies `/api` → `http://localhost:8000` |
| Backend run | `uvicorn app.main:app --reload --port 8000` (default `REVIEW_PROVIDER=mock`) |
| Playwright | **Not present** (frontend `package.json` scripts: `dev`, `build`, `preview`, `test`, `test:watch`) |
| Combined dev helper | **None** (no root `package.json`, Makefile, or shell scripts) |

**Feature availability per tag** (verified via `git cat-file`):

| Capability | `v0.1.0` | `v0.2.0` | `v0.3.0` |
| ---------- | :------: | :------: | :------: |
| Sample diffs (`samples/sampleDiffs.ts`) | ✓ | ✓ | ✓ |
| Reviewer tone panel | — | ✓ | ✓ |
| Comment threads input | — | ✓ | ✓ |
| Suggested replies panel | — | ✓ | ✓ |
| Import panel + bundled samples (`fixtures/importSamples.ts`) | — | — | ✓ |

**Conclusion:** each tag is a self-contained, runnable monorepo snapshot whose feature
set matches its milestone exactly. **Exact-version demos are feasible and recommended.**

## 1. Recommended approach: exact-version via git worktrees

Because all three tags exist and run independently, capture each milestone from its own
**git worktree** so versions never interfere with the working tree:

```bash
# From the repo root (one-time):
git worktree add ../mrrc-v0.1 v0.1.0
git worktree add ../mrrc-v0.2 v0.2.0
git worktree add ../mrrc-v0.3 v0.3.0
```

Each worktree gets its own backend `.venv` and `npm install` (dependencies may differ
per tag). Run that worktree's backend + frontend, capture, then tear down. Full
per-version capture (repeat for v0.2 / v0.3, swapping the version):

```bash
# 1) Backend deps + server on :8000 (in the worktree)
cd ../mrrc-v0.1/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 &        # leave running

# 2) Frontend deps + capture (new terminal, in the worktree)
cd ../mrrc-v0.1/frontend
npm install
npm run demo:install-browsers             # first time only
npm run demo:screenshots:v0.1             # writes docs/assets/screenshots/v0.1/*.png

# 3) Tear down when done
git worktree remove ../mrrc-v0.1
```

> The screenshot scripts write to `docs/assets/screenshots/vX/` **relative to that
> worktree**. Copy the PNGs back to the primary checkout (or capture from a worktree
> created inside the primary repo) so the committed assets land in the main tree.
> **No cross-worktree automation loop is provided** — these documented commands are
> the supported path.

> **Milestone-style fallback (only if a tag fails to run):** capture all three flows
> from the current `v0.3.0` app, since it is a superset, and label them truthfully as
> **"v0.1-style core review flow"**, **"v0.2 reviewer tone / comment reply flow"**,
> and **"v0.3 local import flow"** — *not* as exact historical builds. Prefer exact
> tags; use this only as documented degradation.

## 2. Demo inventory

| Milestone | Screenshots | Video |
| --------- | ----------- | ----- |
| **v0.1** — core review MVP | core review input, review results, Markdown export | core review walkthrough |
| **v0.2** — tone + comments + replies | reviewer tone panel, comment-threads input, suggested replies | suggested-replies walkthrough |
| **v0.3** — local fixture-based import | import sample panel, normalized import preview, imported-threads results, suggested replies from imported comments | local import walkthrough |

## 3. Proposed output paths

```
docs/assets/screenshots/v0.1/
docs/assets/screenshots/v0.2/
docs/assets/screenshots/v0.3/
docs/assets/videos/
```

> **Reconciliation note:** today the v0.3 placeholders referenced by `README.md` and
> `docs/assets/README.md` live at `docs/assets/<name>.png` (flat), e.g.
> `docs/assets/v0.3-import-sample-panel.png`. The implementation phase must pick one
> convention and update all links. **Recommended:** adopt the new
> `docs/assets/screenshots/v0.X/` structure and update README + `docs/assets/README.md`
> (and move the existing flat v0.1 placeholders `main-review-input.png`,
> `risky-review-dashboard.png`, `markdown-export.png` into `screenshots/v0.1/` with
> the new names below, leaving redirect notes).

## 4. Proposed screenshot filenames

**v0.1** → `docs/assets/screenshots/v0.1/`
- `v0.1-core-review-input.png`
- `v0.1-review-results.png`
- `v0.1-markdown-export.png`

**v0.2** → `docs/assets/screenshots/v0.2/`
- `v0.2-reviewer-tone-panel.png`
- `v0.2-comment-threads-input.png`
- `v0.2-suggested-replies.png`

**v0.3** → `docs/assets/screenshots/v0.3/`
- `v0.3-import-sample-panel.png`
- `v0.3-normalized-import-preview.png`
- `v0.3-imported-threads-review-results.png`
- `v0.3-suggested-replies-from-imported-comments.png`

## 5. Proposed video filenames

→ `docs/assets/videos/`
- `mr-review-council-v0.1-core-review-demo.webm`
- `mr-review-council-v0.2-suggested-replies-demo.webm`
- `mr-review-council-v0.3-local-import-demo.webm`

> `.webm` is Playwright's native recording format (VP8/VP9), so no conversion is
> required for web embedding. An optional `.gif`/`.mp4` derivative is covered in §6.

## 6. Automation approach

- **Screenshots — Playwright (preferred).** A small Playwright script per milestone
  drives the running dev server (`baseURL: http://localhost:5173`), performs the
  scripted clicks, waits on stable selectors, and calls `page.screenshot(...)` into
  the milestone's `screenshots/` folder. Use full-page or panel-scoped clips for
  consistency; pin `viewport: { width: 1440, height: 900 }` and
  `deviceScaleFactor: 2` to match the existing `docs/assets/README.md` guidance.
- **Video — Playwright recording (preferred).** Use a context with
  `recordVideo: { dir, size }`. Playwright writes one `.webm` per context on close;
  the script renames it to the milestone filename. No external capture tool needed.
- **ffmpeg — optional, not required.** Only if we later want trimming, `.webm`→`.mp4`,
  or `.gif` derivatives. Document it as optional; the pipeline must work without it.
- **No external services.** Everything runs against the local dev servers; no SaaS,
  no network beyond `localhost`. CI execution is out of scope for this plan.
- **No real provider data.** Selectors interact only with built-in sample diffs and
  bundled synthetic import samples.
- **Determinism:** mock provider is deterministic, so results are stable. Drive the UI
  by role/label selectors (matching the existing test suite), not timeouts, and assert
  a known result element (e.g. risk badge, suggested-reply card) before capturing.

## 7. Scripts to add in a future implementation phase

> Add Playwright **only** in that phase (it is not a dependency today). Keep demo
> tooling isolated from the app/test build.

Proposed layout (illustrative, not yet created):

```
frontend/
  playwright.config.ts          # baseURL 5173, viewport 1440x900, DPR 2, recordVideo dir
  demo/
    screenshots.spec.ts         # or per-version: screenshots.v0_1.ts ...
    video.v0_1.spec.ts
    video.v0_2.spec.ts
    video.v0_3.spec.ts
    helpers/flows.ts            # shared scripted flows (load demo, run review, etc.)
```

Proposed `frontend/package.json` scripts:

| Script | Purpose |
| ------ | ------- |
| `npm run demo:screenshots` | Capture all screenshots for the currently-running version into the matching `screenshots/vX` folder. |
| `npm run demo:video:v0.1` | Record the v0.1 core-review walkthrough `.webm`. |
| `npm run demo:video:v0.2` | Record the v0.2 suggested-replies walkthrough `.webm`. |
| `npm run demo:video:v0.3` | Record the v0.3 local-import walkthrough `.webm`. |
| `npm run demo:all` | Run screenshots + all three videos (assumes the right version is running, or orchestrates per-worktree). |

> Because exact-version capture means *different code per tag*, `demo:all` either (a)
> runs against whichever version's servers are up, or (b) is wrapped by a thin shell
> helper that loops the worktrees. Decide in the implementation phase; default to (a)
> for simplicity and document the worktree loop for full regeneration.

## 8. Manual prerequisites

Per version (or per worktree):

1. **Backend on port 8000:**
   ```bash
   cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000
   ```
2. **Frontend on Vite port 5173:**
   ```bash
   cd frontend && npm run dev
   ```
   (Vite proxies `/api` → `:8000`, so both must be up.)
3. **Browser deps for Playwright** (implementation phase only):
   ```bash
   cd frontend && npx playwright install --with-deps chromium
   ```
4. There is **no** combined "start both" command today. The implementation phase may
   optionally add one (e.g. a `concurrently` dev script or a small shell helper), but
   it is not required — two terminals work.

## 9. Documentation updates needed later

When assets are generated, update:

- **`README.md`** — point the Screenshots section at the new
  `docs/assets/screenshots/vX/...` paths; optionally embed/link the `.webm` videos in
  the **Demo video** section. Keep the implemented-vs-deferred and "not live
  integration" wording intact.
- **`docs/demo-script.md`** — cross-reference the automated capture scripts and the
  exact selector-driven click order so script and automation stay in sync.
- **`docs/assets/README.md`** — replace/extend the manual capture tables with the new
  folder structure and note which shots are now automated.
- **`docs/release-checklist-v0.3.md`** — add a "regenerate demo assets" step
  (`npm run demo:screenshots` / `demo:video:v0.3`) and an asset-freshness check.

## 10. Risks and mitigations

| Risk | Mitigation |
| ---- | ---------- |
| **Flaky timing** | Drive by role/label selectors (mirroring the Vitest suite); `await` a known result element (risk badge, reply card) before capturing; avoid fixed sleeps. |
| **Dev server not running** | Playwright `webServer` config can auto-start `npm run dev`; for exact tags, document the two-terminal startup and a readiness check on `:5173`/`:8000`. |
| **Historical tags not runnable** | All three currently run; if a tag breaks later (dependency drift), fall back to the labeled milestone-style capture from `v0.3.0` (§1) and note it in captions. |
| **Browser video support** | Use Playwright's built-in `.webm` recording (Chromium) — no OS screen recorder. ffmpeg only if a derivative format is needed. |
| **Screenshots becoming stale** | Store the capture scripts in-repo; add a release-checklist step to regenerate; keep filenames stable so links don't break. |
| **Overclaiming live integration** | Hard rule: captions/voiceover say "local fixture-based import demo, not live GitHub/GitLab integration"; only synthetic samples appear on screen; no token/URL fields exist to capture. |
| **Per-version dependency drift** | Use isolated worktrees, each with its own `.venv` + `npm install`; never share `node_modules` across tags. |
| **Asset bloat in git** | Keep videos short (≤90s), `.webm`-compressed; consider downscaling screenshots; revisit Git LFS only if total size becomes a problem. |

## 11. Proposed implementation phases

1. **Phase A — Playwright scaffold (frontend). ✅ Done.** Added Playwright as a dev
   dependency, `playwright.config.ts` (baseURL, viewport, DPR, `webServer`,
   `DEMO_VIDEO_DIR` for later video output), `demo/helpers/{selectors,waitForReview,flows}.ts`
   with the shared scripted flows, and a smoke spec verifying the harness launches.
   No captures generated.
2. **Phase B — Screenshot scripts + `demo:screenshots`. ✅ Done.** Added
   `frontend/demo/screenshots/v0.{1,2,3}.screenshots.spec.ts` (built on the Phase A
   flows + a `helpers/screenshot.ts`), `demo:screenshots[:v0.1|v0.2|v0.3]` scripts, and
   the `docs/assets/screenshots/vX/` folders. **v0.3 assets were captured from the
   `v0.3.0` tree**; v0.1/v0.2 remain capture targets via worktrees. Specs `test.skip`
   gracefully when a feature is absent (so a wrong-version run never writes a
   misleading image). Reconciled README/`docs/assets` links to the structured paths.
3. **Phase C — Video scripts + `demo:video:*` / `demo:all`.** Add the three recording
   specs and scripts; produce the `.webm` files into `docs/assets/videos/`.
4. **Phase D — Docs wiring.** Update README, `demo-script.md`, `docs/assets/README.md`,
   and `release-checklist-v0.3.md` to reference the generated assets and scripts.

## 12. Recommended next implementation prompt

Phases A and B are complete. The next step is **Phase C — video specs**:

> "Implement Phase C of demo automation for MR Review Council: short demo **video**
> specs and `demo:video:v0.1|v0.2|v0.3` + `demo:all` scripts, using the existing
> Playwright harness and `frontend/demo/helpers/flows.ts`. Record one `.webm` per
> milestone into `docs/assets/videos/` (use a context with `recordVideo` pointed at
> `DEMO_VIDEO_DIR` from `playwright.config.ts`, and rename the output to the plan's
> filenames). Drive only built-in sample diffs and bundled synthetic import samples;
> keep each video ≤90s. Document ffmpeg as an optional (not required) post-step for
> `.mp4`/`.gif` derivatives. Generate v0.3 from the current tree and v0.1/v0.2 from
> worktrees. The review/import steps need the backend on port 8000. Do not add live
> provider calls, OAuth, tokens, URL input, posting, or real AI. Update README
> (Demo video section), `docs/assets/README.md`, and `docs/release-checklist-v0.3.md`,
> keeping wording truthful (do not claim assets exist until generated). Verify a v0.3
> recording and stop."
