import { test } from "@playwright/test";

import {
  addManualCommentThreadIfAvailable,
  gotoApp,
  loadCoreReviewSample,
  openReviewerTonePanelIfAvailable,
  runReview,
  waitForSuggestedRepliesIfAvailable,
} from "../helpers/flows";
import { beat, recordDemo } from "../helpers/video";

/**
 * v0.2 — reviewer tone + local comment threads + suggested replies demo video.
 *
 * Records: load a sample diff, open the reviewer tone panel (and tweak the voice),
 * add a *synthetic local* comment thread, run the review, show the suggested replies,
 * and copy one. Nothing is fetched or posted. Needs the backend on :8000.
 *
 * Run from a `v0.2.0` worktree for exact-version video; otherwise it is a v0.2-style
 * fallback. Skips if the comment-thread feature is absent (e.g. a v0.1.0 tree).
 */
const FILENAME = "mr-review-council-v0.2-suggested-replies-demo.webm";

test("v0.2 suggested replies demo", async ({ browser, baseURL }) => {
  const produced = await recordDemo(browser, baseURL, FILENAME, async (page) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    await beat(page);

    // Open the reviewer voice panel and (best-effort) change the global tone.
    if (await openReviewerTonePanelIfAvailable(page)) {
      await beat(page);
      const toneSelect = page.getByLabel("Tone", { exact: true }).first();
      if (await toneSelect.count()) {
        await toneSelect.selectOption("supportive").catch(() => {});
        await beat(page);
      }
    }

    // Add a synthetic local MR comment thread (defining v0.2 feature).
    const added = await addManualCommentThreadIfAvailable(page);
    if (!added) {
      return false;
    }
    await beat(page);

    await runReview(page);
    await beat(page, 900);

    // Show suggested replies and copy one if present.
    if (await waitForSuggestedRepliesIfAvailable(page)) {
      const copy = page.getByRole("button", { name: /^copy reply$/i });
      if (await copy.count()) {
        await copy.first().scrollIntoViewIfNeeded();
        await copy.first().click().catch(() => {});
        await beat(page, 900);
      }
    }
    return true;
  });

  test.skip(!produced, "Comment threads / suggested replies not present in this version.");
});
