/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Vitest-only config (kept separate from vite.config.ts so the production
// `tsc -b` build is not type-checked against Vitest's bundled Vite types).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
    // Scope Vitest to the app source so the Playwright demo specs under `demo/`
    // (which import @playwright/test) are never collected by the unit runner.
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
