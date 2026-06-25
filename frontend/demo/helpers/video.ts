/**
 * Video recording helper for the demo specs.
 *
 * Playwright records video **per browser context**, finalizing the file on
 * `context.close()`. We enable `recordVideo` only inside these video specs (never
 * globally), record the real interactions driven by the shared flow helpers, then
 * rename the artifact to the exact target filename under `docs/assets/videos/`.
 *
 * If the run's defining feature is absent (e.g. a v0.3 flow on a v0.1 tree), the
 * callback returns false and we DELETE the throwaway recording instead of writing a
 * misleading file — the spec then skips.
 */

import { promises as fs } from "node:fs";
import path from "node:path";

import type { Browser, Page } from "@playwright/test";

import { DEMO_VIDEO_DIR } from "../../playwright.config";

/** Recording canvas size (CSS px). Matches the screenshot viewport. */
const VIDEO_SIZE = { width: 1440, height: 900 };

/**
 * Short, intentional pause to make the recording watchable (NOT a wait-for-state
 * hack). Keep these small; total runtime should stay well under ~90s.
 */
export async function beat(page: Page, ms = 700): Promise<void> {
  await page.waitForTimeout(ms);
}

/**
 * Record a demo into `docs/assets/videos/<targetName>`.
 *
 * `run` performs the real interactions and returns `true` when its defining feature
 * was present (so the recording is meaningful for this version) or `false` to discard.
 */
export async function recordDemo(
  browser: Browser,
  baseURL: string | undefined,
  targetName: string,
  run: (page: Page) => Promise<boolean>,
): Promise<boolean> {
  const context = await browser.newContext({
    baseURL,
    viewport: VIDEO_SIZE,
    recordVideo: { dir: DEMO_VIDEO_DIR, size: VIDEO_SIZE },
    // Allow the in-app "Copy reply" buttons to work in headless Chromium.
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const page = await context.newPage();

  let produced = false;
  try {
    produced = await run(page);
  } finally {
    // Finalizes the .webm on disk.
    await context.close();
  }

  const video = page.video();
  const tmpPath = video ? await video.path() : null;
  if (!tmpPath) {
    return produced;
  }

  if (produced) {
    const target = path.join(DEMO_VIDEO_DIR, targetName);
    await fs.rm(target, { force: true });
    try {
      await fs.rename(tmpPath, target);
    } catch {
      // Cross-device fallback.
      await fs.copyFile(tmpPath, target);
      await fs.rm(tmpPath, { force: true });
    }
  } else {
    await fs.rm(tmpPath, { force: true });
  }
  return produced;
}
