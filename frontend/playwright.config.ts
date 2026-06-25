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
 */

/** Where Phase C will write demo videos. Kept here so it is easy to find/share. */
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
    baseURL: "http://localhost:5173",
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
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
