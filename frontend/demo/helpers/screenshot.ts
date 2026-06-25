/**
 * Screenshot path + capture helpers for the demo automation specs.
 *
 * Images are written to `docs/assets/screenshots/<version>/<name>` relative to the
 * frontend working directory (npm scripts run Playwright from `frontend/`). Playwright
 * creates missing parent directories automatically.
 *
 * Captures use only the real running app driven by the shared flow helpers — no
 * fabricated/placeholder PNGs. Full-page captures are used for whole-screen states;
 * element captures are used for focused panels.
 */

import type { Locator, Page } from "@playwright/test";

export type DemoVersion = "v0.1" | "v0.2" | "v0.3";

const BASE = "../docs/assets/screenshots";

export function screenshotPath(version: DemoVersion, name: string): string {
  return `${BASE}/${version}/${name}`;
}

/** Full-page screenshot of the current app state. */
export async function capturePage(
  page: Page,
  version: DemoVersion,
  name: string,
): Promise<void> {
  await page.screenshot({ path: screenshotPath(version, name), fullPage: true });
}

/**
 * Stable-viewport screenshot (the 1440×900 frame, not the full scroll height). Used
 * for tall states (e.g. a long results dashboard) to keep asset size reasonable.
 */
export async function captureViewport(
  page: Page,
  version: DemoVersion,
  name: string,
): Promise<void> {
  await page.screenshot({ path: screenshotPath(version, name), fullPage: false });
}

/**
 * Focused screenshot of a single element (e.g. a panel). Scrolls it into view first.
 * Falls back to a full-page capture if the element is not present.
 */
export async function captureElement(
  page: Page,
  locator: Locator,
  version: DemoVersion,
  name: string,
): Promise<void> {
  if ((await locator.count()) > 0) {
    await locator.first().scrollIntoViewIfNeeded();
    await locator.first().screenshot({ path: screenshotPath(version, name) });
    return;
  }
  await capturePage(page, version, name);
}
