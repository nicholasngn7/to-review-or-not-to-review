import type { Page } from "@playwright/test";

import { TEXT } from "./selectors";

/**
 * Wait for review results to be visible. The RiskBadge ("Risk: Low|Medium|High")
 * only renders after a successful review, so it is a reliable readiness signal.
 *
 * NOTE: running a review requires the backend on port 8000 (the Vite dev server
 * proxies `/api` to it). The smoke test does not call this.
 */
export async function waitForReviewResults(
  page: Page,
  timeout = 20_000,
): Promise<void> {
  await page.getByText(TEXT.riskBadge).first().waitFor({
    state: "visible",
    timeout,
  });
}
