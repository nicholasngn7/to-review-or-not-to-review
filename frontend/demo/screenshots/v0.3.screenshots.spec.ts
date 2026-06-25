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
import { capturePage, captureElement } from "../helpers/screenshot";

/**
 * v0.3 — local fixture-based comment import screenshots.
 *
 * The current tree is v0.3.0, so these are exact-version assets. The import uses
 * **bundled synthetic sample payloads** — nothing is fetched from GitHub/GitLab, no
 * tokens/OAuth, nothing posted. The Normalize / review steps call the local backend,
 * so it must be on port 8000.
 *
 * Each test skips gracefully if the import feature is absent (older trees).
 */
const V = "v0.3";
const IMPORT_PANEL = "details.import-panel";

test.describe("v0.3 local import screenshots", () => {
  test("import sample panel", async ({ page }) => {
    await gotoApp(page);
    const opened = await openImportCommentsPanelIfAvailable(page);
    if (!opened) {
      test.skip(true, "Import comments panel not present in this version.");
    }
    await captureElement(page, page.locator(IMPORT_PANEL), V, "v0.3-import-sample-panel.png");
  });

  test("normalized import preview", async ({ page }) => {
    await gotoApp(page);
    const loaded = await loadSampleImportPayloadIfAvailable(page);
    if (!loaded) {
      test.skip(true, "Import sample payloads not present in this version.");
    }
    const normalized = await normalizeImportedCommentsIfAvailable(page); // needs backend
    if (!normalized) {
      test.skip(true, "Normalize comments action not present in this version.");
    }
    await captureElement(
      page,
      page.locator(IMPORT_PANEL),
      V,
      "v0.3-normalized-import-preview.png",
    );
  });

  test("imported threads review results", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const loaded = await loadSampleImportPayloadIfAvailable(page);
    if (!loaded) {
      test.skip(true, "Import sample payloads not present in this version.");
    }
    await normalizeImportedCommentsIfAvailable(page);
    await loadImportedThreadsIfAvailable(page);
    await runReview(page); // needs backend on :8000
    await capturePage(page, V, "v0.3-imported-threads-review-results.png");
  });

  test("suggested replies from imported comments", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const loaded = await loadSampleImportPayloadIfAvailable(page);
    if (!loaded) {
      test.skip(true, "Import sample payloads not present in this version.");
    }
    await normalizeImportedCommentsIfAvailable(page);
    await loadImportedThreadsIfAvailable(page);
    await runReview(page);
    const present = await waitForSuggestedRepliesIfAvailable(page);
    if (!present) {
      test.skip(true, "Suggested replies not generated in this version/state.");
    }
    await captureElement(
      page,
      page.getByRole("region", { name: /suggested replies/i }),
      V,
      "v0.3-suggested-replies-from-imported-comments.png",
    );
  });
});
