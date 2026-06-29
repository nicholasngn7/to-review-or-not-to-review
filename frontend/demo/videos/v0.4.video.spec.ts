import { test } from "@playwright/test";

import {
  enterLocalContextSourcesIfAvailable,
  expandFirstCitedContextIfAvailable,
  gotoApp,
  loadCoreReviewSample,
  openContextSourcesPanelIfAvailable,
  openRetrievedContextPanelIfAvailable,
  runReview,
} from "../helpers/flows";
import { beat, recordDemo } from "../helpers/video";

/**
 * v0.4 — opt-in local retrieval-grounding demo video.
 *
 * Records: load a sample diff, open "Optional local context sources", enter local
 * allow-listed repo docs (README.md, docs/*) plus an optional lexical context query, run
 * the review, open the "Retrieved local context" panel, and expand a finding's "Cited
 * context".
 *
 * This is a LOCAL, deterministic, **lexical, provenance-only** retrieval demo — nothing is
 * fetched from any provider, no tokens/OAuth, no semantic search, no Bedrock/OpenAI, and
 * the retrieved context does not change findings/severity/recommendation. Needs the backend
 * on :8000. The current tree is v0.4, so this is an exact-version video.
 */
const FILENAME = "mr-review-council-v0.4-retrieval-grounding-demo.webm";

test("v0.4 retrieval grounding demo", async ({ browser, baseURL }) => {
  const produced = await recordDemo(browser, baseURL, FILENAME, async (page) => {
    await gotoApp(page);
    await loadCoreReviewSample(page);
    await beat(page);

    const entered = await enterLocalContextSourcesIfAvailable(
      page,
      undefined,
      "authentication and security review",
    );
    if (!entered) {
      return false; // retrieval-grounding UI absent in this version
    }
    await beat(page, 900);

    // Collapse the input panel so the results are the focus, then run.
    await openContextSourcesPanelIfAvailable(page);
    await runReview(page);
    await beat(page, 900);

    if (await openRetrievedContextPanelIfAvailable(page)) {
      await beat(page, 1000);
    }

    const card = await expandFirstCitedContextIfAvailable(page);
    if (card) {
      await card.scrollIntoViewIfNeeded();
      await beat(page, 1000);
    }
    return true;
  });

  test.skip(!produced, "Retrieval-grounding feature not present in this version.");
});
