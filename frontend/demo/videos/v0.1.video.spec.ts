import { test } from "@playwright/test";

import {
  exportMarkdownIfAvailable,
  gotoApp,
  loadCoreReviewSample,
  runReview,
} from "../helpers/flows";
import { TEXT } from "../helpers/selectors";
import { beat, recordDemo } from "../helpers/video";

/**
 * v0.1 — core review demo video.
 *
 * Records real interactions: load a built-in sample diff, run the review, show the
 * results, and reveal the Markdown export control. Needs the backend on :8000 (the
 * dev server proxies `/api`). Run from a `v0.1.0` worktree for an exact-version video;
 * from a newer tree it is a truthful v0.1-style fallback of the current app.
 */
const FILENAME = "mr-review-council-v0.1-core-review-demo.webm";

test("v0.1 core review demo", async ({ browser, baseURL }) => {
  const produced = await recordDemo(browser, baseURL, FILENAME, async (page) => {
    await gotoApp(page);
    await beat(page);

    const loaded = await loadCoreReviewSample(page);
    if (!loaded) {
      return false; // no demo diff available in this version
    }
    await beat(page);

    await runReview(page);
    await beat(page, 900);

    // Reveal the export control (we do not click it: that triggers a download).
    const exportButton = page.getByRole("button", { name: TEXT.exportMarkdown });
    if (await exportButton.count()) {
      await exportButton.first().scrollIntoViewIfNeeded();
      await beat(page, 900);
    } else {
      await exportMarkdownIfAvailable(page); // no-op if absent
    }
    return true;
  });

  test.skip(!produced, "Core review flow not available in this version.");
});
