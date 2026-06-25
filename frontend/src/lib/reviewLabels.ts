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
