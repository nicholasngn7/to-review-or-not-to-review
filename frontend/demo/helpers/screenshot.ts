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

import type { Browser, Locator, Page } from "@playwright/test";

export type DemoVersion = "v0.1" | "v0.2" | "v0.3" | "v0.4";

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
 * Render the **verbatim** exported Markdown text into a simple monospace page and
 * screenshot it. The content is the real export output read from the in-app download
 * (see `readMarkdownExportIfAvailable`) — it is displayed as-is, never edited.
 *
 * Uses a dedicated 1x context: a full-page capture of a long report at retina 2x is
 * needlessly heavy, and crisp text does not require 2x. This keeps the asset light.
 */
export async function captureMarkdownDocument(
  browser: Browser,
  version: DemoVersion,
  name: string,
  markdown: string,
): Promise<void> {
  const context = await browser.newContext({
    viewport: { width: 1100, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  try {
    await page.setContent(
      `<!doctype html><html><head><meta charset="utf-8"><style>
        body { margin: 0; background: #0d1117; }
        pre {
          margin: 0; padding: 24px 32px;
          font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          color: #e6edf3; white-space: pre-wrap; word-break: break-word;
        }
      </style></head><body><pre id="md"></pre></body></html>`,
    );
    // Set as textContent (not innerHTML) so the Markdown is shown literally, unparsed.
    await page.locator("#md").evaluate((el, text) => {
      el.textContent = text;
    }, markdown);
    await page.screenshot({
      path: screenshotPath(version, name),
      fullPage: true,
    });
  } finally {
    await context.close();
  }
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
