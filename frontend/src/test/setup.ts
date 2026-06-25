// Extends Vitest's `expect` with jest-dom matchers (e.g. toBeInTheDocument)
// and cleans up the DOM between tests.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
