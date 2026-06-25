import { test } from "@playwright/test";

import {
  addManualCommentThreadIfAvailable,
  gotoApp,
  loadCoreReviewSample,
  openReviewerTonePanelIfAvailable,
  runReview,
  waitForSuggestedRepliesIfAvailable,
} from "../helpers/flows";
import { capturePage, captureElement } from "../helpers/screenshot";

/**
 * v0.2 — reviewer tone + local comment threads + suggested replies screenshots.
 *
 * Run from a `v0.2.0` worktree for exact-version assets; from a newer tree these are a
 * truthful **v0.2-style** fallback of the current app. The "suggested replies" shot
 * runs a review, so the backend must be on port 8000.
 *
 * Each test skips gracefully if its v0.2 feature is absent (e.g. when run against a
 * v0.1.0 tree) rather than capturing a misleading screenshot.
 */
const V = "v0.2";

test.describe("v0.2 tone / comments / replies screenshots", () => {
  test("reviewer tone panel", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const opened = await openReviewerTonePanelIfAvailable(page);
    if (!opened) {
      test.skip(true, "Reviewer tone panel not present in this version.");
    }
    await captureElement(
      page,
      page.locator("details.tone-panel"),
      V,
      "v0.2-reviewer-tone-panel.png",
    );
  });

  test("comment threads input", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const added = await addManualCommentThreadIfAvailable(page);
    if (!added) {
      test.skip(true, "Comment threads input not present in this version.");
    }
    // The manual comment-threads panel (not the v0.3 import panel which reuses the class).
    await captureElement(
      page,
      page.locator("details.threads-panel:not(.import-panel)"),
      V,
      "v0.2-comment-threads-input.png",
    );
  });

  test("suggested replies", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const added = await addManualCommentThreadIfAvailable(page);
    if (!added) {
      test.skip(true, "Comment threads input not present in this version.");
    }
    await runReview(page); // needs backend on :8000
    const present = await waitForSuggestedRepliesIfAvailable(page);
    if (!present) {
      test.skip(true, "Suggested replies feature not present in this version.");
    }
    await captureElement(
      page,
      page.getByRole("region", { name: /suggested replies/i }),
      V,
      "v0.2-suggested-replies.png",
    );
  });
});
