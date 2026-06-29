import { test } from "@playwright/test";

import {
  enterLocalContextSourcesIfAvailable,
  expandFirstCitedContextIfAvailable,
  gotoApp,
  loadCoreReviewSample,
  openContextSourcesPanelIfAvailable,
  openRetrievedContextPanelIfAvailable,
  readMarkdownExportIfAvailable,
  runReview,
} from "../helpers/flows";
import {
  captureElement,
  captureMarkdownDocument,
} from "../helpers/screenshot";

/**
 * v0.4 — opt-in local retrieval-grounding screenshots.
 *
 * The current tree is v0.4, so these are exact-version assets. The flow grounds a review
 * on **local, allow-listed** repo docs (README.md, docs/*) using a **deterministic,
 * lexical, provenance-only** retriever — nothing is fetched from any provider, no tokens
 * or OAuth, no semantic search, no Bedrock/OpenAI. Steps that run a review call the local
 * backend, so it must be on port 8000.
 *
 * Each test skips gracefully if the v0.4 retrieval UI / context is absent, so it never
 * writes a misleading file.
 */
const V = "v0.4";

test.describe("v0.4 retrieval grounding screenshots", () => {
  test("optional local context sources input", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const entered = await enterLocalContextSourcesIfAvailable(
      page,
      undefined,
      "authentication and security review",
    );
    if (!entered) {
      test.skip(true, "Optional local context sources input not present.");
    }
    await captureElement(
      page,
      page.locator("details.context-input"),
      V,
      "v0.4-context-sources-input.png",
    );
  });

  test("review results with Retrieved local context panel", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const entered = await enterLocalContextSourcesIfAvailable(
      page,
      undefined,
      "authentication and security review",
    );
    if (!entered) {
      test.skip(true, "Optional local context sources input not present.");
    }
    // Collapse the input panel again so the results panel is the focus.
    await openContextSourcesPanelIfAvailable(page);
    await runReview(page); // needs backend on :8000
    const present = await openRetrievedContextPanelIfAvailable(page);
    if (!present) {
      test.skip(true, "No retrieved local context returned for this state.");
    }
    await captureElement(
      page,
      page.locator("details.context-used"),
      V,
      "v0.4-retrieved-local-context.png",
    );
  });

  test("finding card with Cited context", async ({ page }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const entered = await enterLocalContextSourcesIfAvailable(
      page,
      undefined,
      "authentication and security review",
    );
    if (!entered) {
      test.skip(true, "Optional local context sources input not present.");
    }
    await runReview(page);
    const card = await expandFirstCitedContextIfAvailable(page);
    if (!card) {
      test.skip(true, "No finding carried citations in this state.");
    }
    await captureElement(page, card!, V, "v0.4-finding-cited-context.png");
  });

  test("markdown export with Context used and Cited context", async ({
    page,
    browser,
  }) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    const entered = await enterLocalContextSourcesIfAvailable(
      page,
      undefined,
      "authentication and security review",
    );
    if (!entered) {
      test.skip(true, "Optional local context sources input not present.");
    }
    await runReview(page);
    const markdown = await readMarkdownExportIfAvailable(page);
    if (!markdown || !markdown.includes("## Context used")) {
      test.skip(
        true,
        "Exported Markdown has no Context used section in this state.",
      );
    }
    await captureMarkdownDocument(
      browser,
      V,
      "v0.4-markdown-context-used.png",
      markdown!,
    );
  });
});
