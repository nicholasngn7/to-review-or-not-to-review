import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for **demo automation** (screenshots/videos), kept separate
 * from the Vitest unit suite. Phase A scaffolds the harness only — no screenshots
 * or videos are generated here (screenshots are captured only on failure; video is
 * off). Later phases will add exact-version screenshot/video specs.
 *
 * Capture conventions (match docs/assets/README.md): 1440×900 @ 2x, Chromium.
 *
 * Dev servers: the frontend Vite server (port 5173) proxies `/api` to the backend
 * (port 8000). This config can reuse already-running dev servers; if none is up it
 * starts `npm run dev` for the frontend only. It does NOT start the backend — that
 * matches the repo (there is no combined start command), and the smoke test does not
 * require the backend. Specs that run a review must ensure the backend is running.
 *
 * Exact-version capture: point the harness at a *historical* app (started from a tag
 * worktree) by setting `DEMO_BASE_URL`, e.g.
 *   DEMO_BASE_URL=http://localhost:5173 npm run demo:screenshots:v0.1
 * When `DEMO_BASE_URL` is set the bundled `webServer` is disabled (we attach to the
 * already-running historical server instead of starting this checkout's dev server).
 */

/** Base URL under test; override with DEMO_BASE_URL for exact-version capture. */
export const DEMO_BASE_URL = process.env.DEMO_BASE_URL ?? "http://localhost:5173";

/** True when capturing against an externally-started (e.g. historical) app. */
const USE_EXTERNAL_SERVER = Boolean(process.env.DEMO_BASE_URL);

/** Where Phase C writes demo videos. Kept here so it is easy to find/share. */
export const DEMO_VIDEO_DIR = "../docs/assets/videos";

export default defineConfig({
  testDir: "./demo",
  testMatch: /.*\.spec\.ts$/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  // Test artifacts (failure screenshots/traces) land here, away from committed assets.
  outputDir: "./demo/.artifacts",
  use: {
    baseURL: DEMO_BASE_URL,
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    // Phase A: do not generate assets. Capture a screenshot only if a test fails.
    screenshot: "only-on-failure",
    video: "off",
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
      },
    },
  ],
  // When DEMO_BASE_URL is set we attach to an externally-started app (e.g. a tag
  // worktree's dev server) and must NOT start this checkout's dev server.
  webServer: USE_EXTERNAL_SERVER
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5173",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
