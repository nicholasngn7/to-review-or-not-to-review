import { test } from "@playwright/test";

import {
  gotoApp,
  loadCoreReviewSample,
  loadImportedThreadsIfAvailable,
  loadSampleImportPayloadIfAvailable,
  normalizeImportedCommentsIfAvailable,
  openImportCommentsPanelIfAvailable,
  runReview,
  waitForSuggestedRepliesIfAvailable,
} from "../helpers/flows";
import { beat, recordDemo } from "../helpers/video";

/**
 * v0.3 — local fixture-based comment import demo video.
 *
 * Records: load a sample diff, open "Import comments (local demo)", load a **bundled
 * synthetic** GitHub sample payload, normalize it through the local-only
 * `POST /api/import-comments`, preview the normalized threads, load them, run the
 * review, and show suggested replies generated from the imported comments.
 *
 * This is a LOCAL fixture-based demo — nothing is fetched from GitHub/GitLab, no
 * tokens/OAuth, nothing posted; it is NOT live provider integration. Needs the
 * backend on :8000. The current tree is v0.3.0, so this is an exact-version video.
 */
const FILENAME = "mr-review-council-v0.3-local-import-demo.webm";

test("v0.3 local import demo", async ({ browser, baseURL }) => {
  const produced = await recordDemo(browser, baseURL, FILENAME, async (page) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    await beat(page);

    if (!(await openImportCommentsPanelIfAvailable(page))) {
      return false; // import feature absent in this version
    }
    await beat(page);

    // Load a bundled synthetic payload (defaults to "GitHub review comments").
    await loadSampleImportPayloadIfAvailable(page);
    await beat(page, 900);

    // Normalize through the local endpoint, then preview.
    await normalizeImportedCommentsIfAvailable(page);
    await beat(page, 900);

    // Load the normalized threads into the review input.
    await loadImportedThreadsIfAvailable(page);
    await beat(page);

    await runReview(page);
    await beat(page, 900);

    if (await waitForSuggestedRepliesIfAvailable(page)) {
      await beat(page, 900);
    }
    return true;
  });

  test.skip(!produced, "Local import feature not present in this version.");
});
