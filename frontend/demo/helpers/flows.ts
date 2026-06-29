/**
 * Reusable, selector-driven demo flows for MR Review Council.
 *
 * Design goals:
 *  - **Resilient:** drive by accessible name / visible text, not brittle CSS.
 *  - **Version-tolerant:** every feature that postdates v0.1 has an `...IfAvailable`
 *    helper that NO-OPS when the element is absent, so a single flow can run against
 *    v0.1.0 / v0.2.0 / v0.3.0 worktrees. Specs that need version-specific behavior can
 *    still branch on the boolean each helper returns.
 *  - **Honest:** flows only ever touch built-in sample diffs and bundled *synthetic*
 *    import samples. Nothing here fetches from GitHub/GitLab, uses tokens/OAuth, or
 *    posts anything.
 *
 * Phase A note: these helpers are scaffolding for the later screenshot/video specs;
 * they do not capture assets themselves.
 */

import type { Locator, Page } from "@playwright/test";

import {
  DEFAULT_CONTEXT_SOURCES,
  DEFAULT_IMPORT_SAMPLE_LABEL,
  FEATURE_PROBE_TIMEOUT_MS,
  TEXT,
} from "./selectors";
import { waitForReviewResults } from "./waitForReview";

/** Return true if at least one matching element is attached within `timeout`. */
async function isPresent(
  locator: Locator,
  timeout = FEATURE_PROBE_TIMEOUT_MS,
): Promise<boolean> {
  try {
    await locator.first().waitFor({ state: "attached", timeout });
    return true;
  } catch {
    return false;
  }
}

/**
 * Open a `<details>` panel identified by text it contains (e.g. its summary title).
 * Returns false (no-op) when no such panel exists in this version.
 */
async function openDetailsByText(
  page: Page,
  text: RegExp,
): Promise<boolean> {
  const details = page.locator("details").filter({ hasText: text }).first();
  if (!(await isPresent(details))) {
    return false;
  }
  const alreadyOpen = await details.evaluate(
    (el) => (el as HTMLDetailsElement).open,
  );
  if (!alreadyOpen) {
    await details.locator("summary").first().click();
    // Belt-and-suspenders: ensure it is open even if the click was intercepted.
    await details.evaluate((el) => {
      (el as HTMLDetailsElement).open = true;
    });
  }
  return true;
}

/** Navigate to the app root and wait for the shell to render. */
export async function gotoApp(page: Page): Promise<void> {
  await page.goto("/");
  await page
    .getByRole("heading", { name: TEXT.appTitle })
    .first()
    .waitFor({ state: "visible" });
}

/**
 * (1) Load the core risky-diff sample available in the app (v0.1+). Falls back to the
 * first demo-diff chip if labels differ in a given version. No-ops if no chips exist.
 */
export async function loadCoreReviewSample(page: Page): Promise<boolean> {
  const risky = page.getByRole("button", { name: TEXT.sampleRiskyDiff });
  if (await isPresent(risky)) {
    await risky.first().click();
    return true;
  }
  const anyChip = page.locator(".demo-bar__buttons button").first();
  if (await isPresent(anyChip)) {
    await anyChip.click();
    return true;
  }
  return false;
}

/**
 * (2) Click Run Review and wait for results to appear.
 * Requires the backend on port 8000 (the dev server proxies `/api`).
 */
export async function runReview(page: Page): Promise<void> {
  await page.getByRole("button", { name: TEXT.runReview }).first().click();
  await waitForReviewResults(page);
}

/** (3) Click Export Markdown if present; no-op otherwise. */
export async function exportMarkdownIfAvailable(page: Page): Promise<boolean> {
  const button = page.getByRole("button", { name: TEXT.exportMarkdown });
  if (!(await isPresent(button))) {
    return false;
  }
  await button.first().click();
  return true;
}

/** (4) Open the reviewer tone controls if present (v0.2+); no-op for v0.1. */
export async function openReviewerTonePanelIfAvailable(
  page: Page,
): Promise<boolean> {
  return openDetailsByText(page, TEXT.tonePanelTitle);
}

/**
 * (5) Add a small synthetic local MR comment thread if the UI exists (v0.2+).
 * No-ops for v0.1. The body is fabricated demo text — nothing is posted anywhere.
 */
export async function addManualCommentThreadIfAvailable(
  page: Page,
): Promise<boolean> {
  if (!(await openDetailsByText(page, TEXT.commentThreadsTitle))) {
    return false;
  }
  const addButton = page.getByRole("button", { name: TEXT.addCommentThread });
  if (!(await isPresent(addButton))) {
    return false;
  }
  await addButton.first().click();
  const comment = page.getByLabel("Comment", { exact: true }).last();
  if (await isPresent(comment)) {
    await comment.fill("Can we add a regression test for this path?");
  }
  return true;
}

/** (6) Open the local import-comments panel if present (v0.3+); no-op otherwise. */
export async function openImportCommentsPanelIfAvailable(
  page: Page,
): Promise<boolean> {
  return openDetailsByText(page, TEXT.importPanelTitle);
}

/**
 * (7) Click a bundled sample-import payload button if present (v0.3+).
 * `sampleLabel` matches one of: "GitHub review comments", "GitHub issue comments",
 * "GitLab discussions". No-ops if the panel/button is absent.
 */
export async function loadSampleImportPayloadIfAvailable(
  page: Page,
  sampleLabel: string = DEFAULT_IMPORT_SAMPLE_LABEL,
): Promise<boolean> {
  await openImportCommentsPanelIfAvailable(page);
  const button = page.getByRole("button", {
    name: new RegExp(sampleLabel, "i"),
  });
  if (!(await isPresent(button))) {
    return false;
  }
  await button.first().click();
  return true;
}

/**
 * (8) Click Normalize comments if present (v0.3+) and wait for the normalized preview
 * (the "Load imported threads" button appears once normalization succeeds). No-op if
 * absent. Requires the backend on port 8000.
 */
export async function normalizeImportedCommentsIfAvailable(
  page: Page,
): Promise<boolean> {
  const button = page.getByRole("button", { name: TEXT.normalizeComments });
  if (!(await isPresent(button))) {
    return false;
  }
  await button.first().click();
  await page
    .getByRole("button", { name: TEXT.loadImportedThreads })
    .first()
    .waitFor({ state: "visible", timeout: 15_000 });
  return true;
}

/**
 * (9) Click Load imported threads if present (v0.3+) and wait for the
 * "Imported comments" group to render. No-op if absent.
 */
export async function loadImportedThreadsIfAvailable(
  page: Page,
): Promise<boolean> {
  const button = page.getByRole("button", { name: TEXT.loadImportedThreads });
  if (!(await isPresent(button))) {
    return false;
  }
  await button.first().click();
  await page
    .getByRole("group", { name: TEXT.importedCommentsGroup })
    .first()
    .waitFor({ state: "visible", timeout: 10_000 });
  return true;
}

/**
 * (10) Wait for the Suggested replies section if the feature exists (v0.2+).
 * No-ops (returns false) if the section never appears in this version/state.
 */
export async function waitForSuggestedRepliesIfAvailable(
  page: Page,
): Promise<boolean> {
  const section = page.getByRole("region", { name: TEXT.suggestedReplies });
  // The panel uses <section aria-label="Suggested replies">; fall back to heading.
  const heading = page.getByRole("heading", { name: TEXT.suggestedReplies });
  const target = (await isPresent(section, 1_000)) ? section : heading;
  if (!(await isPresent(target, 8_000))) {
    return false;
  }
  await target.first().waitFor({ state: "visible", timeout: 8_000 });
  return true;
}

/**
 * (11) Open the optional local context sources panel if present (v0.4+); no-op otherwise.
 */
export async function openContextSourcesPanelIfAvailable(
  page: Page,
): Promise<boolean> {
  return openDetailsByText(page, TEXT.contextSourcesTitle);
}

/**
 * (12) Enter local, allow-listed context source paths (one per line) and an optional
 * local/lexical context query, opting into retrieval grounding (v0.4+). No-op if the
 * input is absent. Sources are local repo docs only — no URLs, tokens, or fetching.
 */
export async function enterLocalContextSourcesIfAvailable(
  page: Page,
  sources: string[] = DEFAULT_CONTEXT_SOURCES,
  query?: string,
): Promise<boolean> {
  if (!(await openContextSourcesPanelIfAvailable(page))) {
    return false;
  }
  const sourcesField = page.getByLabel(TEXT.sourcePathsLabel);
  if (!(await isPresent(sourcesField))) {
    return false;
  }
  await sourcesField.first().fill(sources.join("\n"));
  if (query) {
    const queryField = page.getByLabel(TEXT.contextQueryLabel);
    if (await isPresent(queryField)) {
      await queryField.first().fill(query);
    }
  }
  return true;
}

/**
 * (13) Open and wait for the "Retrieved local context" results panel if it appears
 * (v0.4+). Returns false when the panel is absent (no context retrieved / older tree).
 */
export async function openRetrievedContextPanelIfAvailable(
  page: Page,
): Promise<boolean> {
  const details = page
    .locator("details.context-used")
    .filter({ hasText: TEXT.retrievedContextTitle })
    .first();
  if (!(await isPresent(details, 8_000))) {
    return false;
  }
  await details.evaluate((el) => {
    (el as HTMLDetailsElement).open = true;
  });
  return true;
}

/**
 * (14) Expand the first finding card's "Cited context" detail if any finding carries
 * citations (v0.4+). Returns false when no finding has citations in this state.
 */
export async function expandFirstCitedContextIfAvailable(
  page: Page,
): Promise<Locator | null> {
  const details = page.locator("details.finding-citations").first();
  if (!(await isPresent(details, 8_000))) {
    return null;
  }
  await details.scrollIntoViewIfNeeded();
  await details.evaluate((el) => {
    (el as HTMLDetailsElement).open = true;
  });
  // Return the enclosing finding card for a focused screenshot.
  return details.locator("xpath=ancestor::li[contains(@class,'finding')][1]");
}

/**
 * (15) Export the review as Markdown and return the file's text content (v0.4+/v0.1+).
 * Intercepts the real in-app download (a Blob anchor click) — nothing is fetched or
 * posted. Returns null if the export control is absent.
 */
export async function readMarkdownExportIfAvailable(
  page: Page,
): Promise<string | null> {
  const button = page.getByRole("button", { name: TEXT.exportMarkdown });
  if (!(await isPresent(button))) {
    return null;
  }
  const downloadPromise = page.waitForEvent("download");
  await button.first().click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf-8");
}
