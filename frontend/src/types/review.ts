/**
 * Shared review-contract types for MR Review Council.
 *
 * These mirror the backend Pydantic models in `backend/app/models/`. Field
 * names match the camelCase JSON the API emits. Keep this file in sync with the
 * backend contract.
 */

// ---- Enums (string unions) ----

export type ReviewerPersona =
  | "architect"
  | "qa"
  | "security"
  | "frontend"
  | "backend"
  | "sre"
  | "product";

export type RiskLevel = "low" | "medium" | "high";

export type MergeRecommendation =
  | "ready"
  | "ready_with_followups"
  | "needs_changes"
  | "needs_human_review";

export type FindingSeverity = "info" | "low" | "medium" | "high";

// ---- Diff models ----

export type LineKind = "added" | "removed" | "context";

export type FileChangeType =
  | "added"
  | "modified"
  | "deleted"
  | "renamed"
  | "unknown";

export interface DiffLine {
  kind: LineKind;
  content: string;
  oldLineNo: number | null;
  newLineNo: number | null;
}

export interface DiffHunk {
  header: string;
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: DiffLine[];
}

export interface DiffFile {
  oldPath: string | null;
  newPath: string | null;
  changeType: FileChangeType;
  hunks: DiffHunk[];
}

export interface DiffStats {
  filesChanged: number;
  addedLines: number;
  removedLines: number;
  totalHunks: number;
}

export interface ParsedDiff {
  files: DiffFile[];
  stats: DiffStats;
}

// ---- Review models ----

export interface ReviewRequest {
  diffText: string;
  selectedPersonas: ReviewerPersona[];
  title?: string | null;
  description?: string | null;
  source?: string | null;
}

export interface HunkReference {
  hunkIndex: number;
  header?: string | null;
  line?: number | null;
}

export interface ReviewFinding {
  id: string;
  reviewer: ReviewerPersona;
  severity: FindingSeverity;
  title: string;
  explanation: string;
  recommendation: string;
  filePath?: string | null;
  hunkReference?: HunkReference | null;
  confidence?: number | null;
}

export interface PersonaReview {
  persona: ReviewerPersona;
  riskLevel: RiskLevel;
  summary: string;
  findings: ReviewFinding[];
}

export interface ReviewSummary {
  headline: string;
  details: string;
  totalFindings: number;
  findingsBySeverity: Partial<Record<FindingSeverity, number>>;
}

export interface ReviewResponse {
  overallRisk: RiskLevel;
  mergeRecommendation: MergeRecommendation;
  summary: ReviewSummary;
  diffStats: DiffStats;
  personaReviews: PersonaReview[];
  findings: ReviewFinding[];
}
