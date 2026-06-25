import { expect, test } from "@playwright/test";

import { gotoApp, loadCoreReviewSample, runReview } from "../helpers/flows";
import { capturePage, captureElement } from "../helpers/screenshot";
import { TEXT } from "../helpers/selectors";

/**
 * v0.1 — core review MVP screenshots.
 *
 * Run from a `v0.1.0` worktree for exact-version assets (see
 * docs/demo-automation-plan.md). Run from a newer tree, the images are a truthful
 * **v0.1-style** fallback of the current app, not an exact v0.1.0 build.
 *
 * "review results" and "markdown export" run a review, so the backend must be on
 * port 8000 (the Vite dev server proxies `/api`).
 */
const V = "v0.1";

test.describe("v0.1 core review screenshots", () => {
  test("core review input", async ({ page }) => {
    await gotoApp(page);
    const loaded = await loadCoreReviewSample(page);
    expect(loaded, "a built-in demo diff should be loadable").toBeTruthy();
    // Deterministic wait: the diff textarea is populated from the sample.
    await expect(
      page.getByLabel("Diff", { exact: true }),
    ).toHaveValue(/diff --git/);
    await capturePage(page, V, "v0.1-core-review-input.png");
  });

  test("review results", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    await runReview(page); // waits for the risk badge; needs backend on :8000
    await capturePage(page, V, "v0.1-review-results.png");
  });

  test("markdown export UI", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    await runReview(page);

    const exportButton = page.getByRole("button", { name: TEXT.exportMarkdown });
    if ((await exportButton.count()) === 0) {
      test.skip(
        true,
        "Export Markdown UI is not available in this version — skipping rather than capturing a misleading screenshot.",
      );
    }
    // Capture the results toolbar (verdict + Export Markdown control). We do NOT click
    // it: that triggers a file download, and rendering the .md is a manual step.
    await exportButton.first().scrollIntoViewIfNeeded();
    await captureElement(
      page,
      page.locator(".results__toolbar"),
      V,
      "v0.1-markdown-export.png",
    );
  });
});
