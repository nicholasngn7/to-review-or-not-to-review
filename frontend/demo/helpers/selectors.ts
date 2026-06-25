/**
 * Centralized, human-readable selectors for the demo automation flows.
 *
 * These mirror the accessible names / visible text used by the app's components and
 * the Vitest suite, so the demo specs stay resilient to markup changes. Some features
 * only exist in later versions (tone/comments in v0.2+, import in v0.3+); helpers that
 * use those selectors are written to no-op when the elements are absent.
 */

export const TEXT = {
  /** App shell (all versions). */
  appTitle: /MR Review Council/i,

  /** Core review flow (v0.1+). */
  sampleRiskyDiff: /risky backend auth change/i,
  sampleLowRiskDiff: /low-risk frontend change/i,
  runReview: /run review/i,
  /** RiskBadge renders "Risk: Low|Medium|High" once results are present. */
  riskBadge: /Risk:\s*(Low|Medium|High)/i,
  exportMarkdown: /export markdown/i,

  /** Reviewer tone (v0.2+). */
  tonePanelTitle: /reviewer voice/i,

  /** Local comment threads (v0.2+). */
  commentThreadsTitle: /existing comment threads/i,
  addCommentThread: /add comment thread/i,

  /** Local fixture-based import (v0.3+). */
  importPanelTitle: /import comments/i,
  normalizeComments: /normalize comments/i,
  loadImportedThreads: /load imported threads/i,
  importedCommentsGroup: /imported comments/i,

  /** Suggested replies (v0.2+, populated when threads are submitted). */
  suggestedReplies: /suggested replies/i,
} as const;

/** Default bundled import sample label used by demo flows (v0.3+). */
export const DEFAULT_IMPORT_SAMPLE_LABEL = "GitHub review comments";

/** How long an "...IfAvailable" probe waits before deciding a feature is absent. */
export const FEATURE_PROBE_TIMEOUT_MS = 2_000;
