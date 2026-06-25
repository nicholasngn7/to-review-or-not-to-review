import { expect, test } from "@playwright/test";

import { gotoApp } from "./helpers/flows";
import { TEXT } from "./helpers/selectors";

/**
 * Minimal harness smoke test (Phase A).
 *
 * Purpose: confirm the Playwright harness launches and the app loads at `/`.
 * It intentionally:
 *  - does NOT capture screenshots or videos,
 *  - does NOT run a review (so the backend is not required),
 *  - does NOT depend on any v0.2/v0.3-only features,
 * so it works against v0.1.0, v0.2.0, and v0.3.0 alike.
 */
test.describe("demo harness smoke", () => {
  test("loads the app shell at /", async ({ page }) => {
    await gotoApp(page);

    // The product title is present in every version.
    await expect(
      page.getByRole("heading", { name: TEXT.appTitle }).first(),
    ).toBeVisible();

    // The core review action exists (still disabled until a diff is entered).
    await expect(
      page.getByRole("button", { name: TEXT.runReview }).first(),
    ).toBeVisible();
  });
});
