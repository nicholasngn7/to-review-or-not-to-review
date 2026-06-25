/**
 * Shared display metadata for the review contract enums.
 *
 * Single source of truth for human-readable labels and canonical ordering so
 * presentational components stay consistent and DRY.
 */

import type {
  FindingSeverity,
  MergeRecommendation,
  ReviewerPersona,
  RiskLevel,
  ToneProfile,
  ToneStrictness,
  ToneStyle,
  ToneVerbosity,
} from "../types/review";

export const PERSONA_ORDER: ReviewerPersona[] = [
  "architect",
  "qa",
  "security",
  "frontend",
  "backend",
  "sre",
  "product",
];

export const PERSONA_LABELS: Record<ReviewerPersona, string> = {
  architect: "Architect",
  qa: "QA / Test",
  security: "Security",
  frontend: "Frontend",
  backend: "Backend",
  sre: "SRE / On-call",
  product: "Product",
};

export const PERSONA_BLURBS: Record<ReviewerPersona, string> = {
  architect: "Structure & boundaries",
  qa: "Coverage & regressions",
  security: "Secrets & unsafe patterns",
  frontend: "UI, state & a11y",
  backend: "APIs & validation",
  sre: "Observability & reliability",
  product: "Clarity & maintainability",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const RECOMMENDATION_LABELS: Record<MergeRecommendation, string> = {
  ready: "Ready",
  ready_with_followups: "Ready with follow-ups",
  needs_changes: "Needs changes",
  needs_human_review: "Needs human review",
};

export const SEVERITY_ORDER: FindingSeverity[] = [
  "high",
  "medium",
  "low",
  "info",
];

export const SEVERITY_LABELS: Record<FindingSeverity, string> = {
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
};

export function personaLabel(persona: ReviewerPersona): string {
  return PERSONA_LABELS[persona] ?? persona;
}

// ---- Retrieval / grounding (presentation only) ----

/** Honest, reusable caption for retrieved local context. */
export const RETRIEVAL_PROVENANCE_NOTE =
  "Retrieved local context (lexical, provenance-only) — not semantic search and " +
  "not proof of correctness.";

/** Format a retrieval score for display (e.g. 0.4045 -> "0.40"). */
export function formatScore(score: number): string {
  return score.toFixed(2);
}

/** "lines 3–8", "line 3", or null when no range is known. */
export function formatLineRange(
  startLine?: number | null,
  endLine?: number | null,
): string | null {
  if (startLine == null && endLine == null) {
    return null;
  }
  if (startLine != null && endLine != null && startLine !== endLine) {
    return `lines ${startLine}–${endLine}`;
  }
  const single = startLine ?? endLine;
  return single != null ? `line ${single}` : null;
}

// ---- Reviewer tone (presentation only) ----

/**
 * The default reviewer voice. Sending this is equivalent to sending no tone at
 * all — the backend treats it as a no-op (see `isDefaultTone`).
 */
export const DEFAULT_TONE_PROFILE: ToneProfile = {
  style: "direct",
  strictness: "medium",
  verbosity: "normal",
  customInstructions: "",
};

export const TONE_STYLE_ORDER: ToneStyle[] = [
  "direct",
  "supportive",
  "educational",
  "strict",
  "curious",
  "executive",
];

export const TONE_STYLE_LABELS: Record<ToneStyle, string> = {
  direct: "Direct",
  supportive: "Supportive",
  educational: "Educational",
  strict: "Strict",
  curious: "Curious",
  executive: "Executive",
};

export const TONE_STYLE_BLURBS: Record<ToneStyle, string> = {
  direct: "Concise and action-oriented",
  supportive: "Collaborative, lower-friction",
  educational: "Explains why it matters",
  strict: "Firm, merge-safety framing",
  curious: "Asks clarifying questions",
  executive: "Risk / business impact",
};

export const TONE_STRICTNESS_ORDER: ToneStrictness[] = ["low", "medium", "high"];

export const TONE_STRICTNESS_LABELS: Record<ToneStrictness, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const TONE_VERBOSITY_ORDER: ToneVerbosity[] = [
  "brief",
  "normal",
  "detailed",
];

export const TONE_VERBOSITY_LABELS: Record<ToneVerbosity, string> = {
  brief: "Brief",
  normal: "Normal",
  detailed: "Detailed",
};

/** True when a profile matches the default voice (no custom instructions). */
export function isDefaultTone(tone: ToneProfile): boolean {
  return (
    tone.style === "direct" &&
    tone.strictness === "medium" &&
    tone.verbosity === "normal" &&
    !tone.customInstructions?.trim()
  );
}

/**
 * Normalize a tone profile for the wire: drops empty/whitespace-only custom
 * instructions so we never send blank text.
 */
export function toRequestTone(tone: ToneProfile): ToneProfile {
  const custom = tone.customInstructions?.trim();
  const normalized: ToneProfile = {
    style: tone.style,
    strictness: tone.strictness,
    verbosity: tone.verbosity,
  };
  if (custom) {
    normalized.customInstructions = custom;
  }
  return normalized;
}
