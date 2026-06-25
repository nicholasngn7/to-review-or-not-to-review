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

// ---- Reviewer tone profiles (v0.2 contract; presentation only) ----

export type ToneStyle =
  | "direct"
  | "supportive"
  | "educational"
  | "strict"
  | "curious"
  | "executive";

export type ToneStrictness = "low" | "medium" | "high";

export type ToneVerbosity = "brief" | "normal" | "detailed";

export interface ToneProfile {
  style: ToneStyle;
  strictness: ToneStrictness;
  verbosity: ToneVerbosity;
  customInstructions?: string | null;
}

// ---- Existing MR comment threads & suggested replies (v0.2) ----

export type CommentThreadStatus = "open" | "resolved" | "unknown";

export interface ThreadComment {
  id: string;
  author?: string | null;
  body: string;
  createdAt?: string | null;
  isResolved?: boolean | null;
}

export interface CommentThread {
  id: string;
  filePath?: string | null;
  line?: number | null;
  status: CommentThreadStatus;
  comments: ThreadComment[];
  source?: string | null;
}

export interface SuggestedReply {
  id: string;
  threadId: string;
  reviewer: ReviewerPersona;
  suggestedReply: string;
  rationale: string;
  confidence?: number | null;
  needsHumanReview: boolean;
  toneProfile?: ToneProfile | null;
  /** File the source thread is anchored to, copied for context. */
  filePath?: string | null;
  /** Line the source thread is anchored to, copied for context. */
  line?: number | null;
}

// ---- Retrieval / grounding (v0.4; local, lexical, provenance-only) ----

/**
 * Options for opt-in local retrieval grounding. Lexical/deterministic — not a
 * semantic search. Sent only when the user provides local context sources.
 */
export interface RetrievalQuery {
  query: string;
  topK?: number;
  persona?: string | null;
  filePath?: string | null;
  diffSummary?: string | null;
  filters?: Record<string, string>;
}

/** Provenance for a grounded finding: a retrieved local context snippet. */
export interface RetrievedCitation {
  sourcePath?: string | null;
  heading?: string | null;
  snippet: string;
  score: number;
  startLine?: number | null;
  endLine?: number | null;
  chunkId: string;
}

/** A single ranked retrieval result surfaced in "Context used". */
export interface RetrievalResult {
  chunkId: string;
  documentId: string;
  sourcePath?: string | null;
  heading?: string | null;
  snippet: string;
  score: number;
  startLine?: number | null;
  endLine?: number | null;
  metadata?: Record<string, string>;
}

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
  /** Global tone profile for all selected reviewers (presentation only). */
  toneProfile?: ToneProfile | null;
  /** Per-persona tone overrides; these win over toneProfile. */
  personaToneProfiles?: Partial<Record<ReviewerPersona, ToneProfile>> | null;
  /** Existing MR/PR comment threads, captured as structured input. */
  commentThreads?: CommentThread[] | null;
  /**
   * Local doc/source paths to ground the review on (v0.4 opt-in retrieval).
   * Allow-listed, local, lexical — never sent unless the user provides sources.
   */
  knowledgeSources?: string[] | null;
  /** Optional local retrieval query/options; backend derives one if omitted. */
  retrieval?: RetrievalQuery | null;
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
  /** Provenance-only retrieved context (v0.4). Does not affect severity. */
  citations?: RetrievedCitation[] | null;
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
  /** Draft, copy-only replies to comment threads. Empty until Phase 15. */
  suggestedReplies: SuggestedReply[];
  /** Retrieved local context used for grounding (v0.4). Empty when none. */
  contextUsed?: RetrievalResult[] | null;
}
