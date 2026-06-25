import type {
  RetrievalResult,
  RetrievedCitation,
  ReviewResponse,
} from "../types/review";

/** A small but realistic review result spanning two personas and severities. */
export const mockReviewResult: ReviewResponse = {
  overallRisk: "high",
  mergeRecommendation: "needs_human_review",
  summary: {
    headline: "Needs human review before merge.",
    details: "2 reviewer(s) produced 2 finding(s) (1 high, 1 medium).",
    totalFindings: 2,
    findingsBySeverity: { high: 1, medium: 1 },
  },
  diffStats: {
    filesChanged: 1,
    addedLines: 12,
    removedLines: 2,
    totalHunks: 1,
  },
  personaReviews: [
    {
      persona: "security",
      riskLevel: "high",
      summary: "Security reviewer raised 1 finding(s), 1 high.",
      findings: [
        {
          id: "security-1",
          reviewer: "security",
          severity: "high",
          title: "Possible use of eval()",
          explanation: "An added line appears to use eval().",
          recommendation: "Avoid eval(); parse input safely.",
          filePath: "app/auth.py",
          hunkReference: { hunkIndex: 0, header: "@@ -1,1 +1,4 @@", line: 3 },
          confidence: 0.45,
        },
      ],
    },
    {
      persona: "qa",
      riskLevel: "medium",
      summary: "QA / Test reviewer raised 1 finding(s), 1 medium.",
      findings: [
        {
          id: "qa-1",
          reviewer: "qa",
          severity: "medium",
          title: "Production code changed without test updates",
          explanation: "1 production file changed but no tests were updated.",
          recommendation: "Add or update tests covering the changed logic.",
          filePath: "app/auth.py",
          hunkReference: null,
          confidence: 0.65,
        },
      ],
    },
  ],
  findings: [
    {
      id: "security-1",
      reviewer: "security",
      severity: "high",
      title: "Possible use of eval()",
      explanation: "An added line appears to use eval().",
      recommendation: "Avoid eval(); parse input safely.",
      filePath: "app/auth.py",
      hunkReference: { hunkIndex: 0, header: "@@ -1,1 +1,4 @@", line: 3 },
      confidence: 0.45,
    },
    {
      id: "qa-1",
      reviewer: "qa",
      severity: "medium",
      title: "Production code changed without test updates",
      explanation: "1 production file changed but no tests were updated.",
      recommendation: "Add or update tests covering the changed logic.",
      filePath: "app/auth.py",
      hunkReference: null,
      confidence: 0.65,
    },
  ],
  suggestedReplies: [],
};

/** A sample per-finding citation (local, lexical, provenance-only). */
export const mockCitation: RetrievedCitation = {
  chunkId: "doc-abc#chunk-2",
  sourcePath: "docs/decisions.md",
  heading: "Authentication",
  snippet: "Avoid eval(); parse input with a safe, explicit parser.",
  score: 0.4231,
  startLine: 12,
  endLine: 18,
};

/** A sample retrieved context result for the "Context used" panel. */
export const mockRetrievalResult: RetrievalResult = {
  chunkId: "doc-abc#chunk-2",
  documentId: "doc-abc",
  sourcePath: "docs/decisions.md",
  heading: "Authentication",
  snippet: "Avoid eval(); parse input with a safe, explicit parser.",
  score: 0.4231,
  startLine: 12,
  endLine: 18,
  metadata: { sourceType: "repo_doc" },
};

/** A review result that includes retrieved context and a per-finding citation. */
export const mockReviewResultWithContext: ReviewResponse = {
  ...mockReviewResult,
  contextUsed: [mockRetrievalResult],
  personaReviews: mockReviewResult.personaReviews.map((pr) =>
    pr.persona === "security"
      ? {
          ...pr,
          findings: pr.findings.map((f) => ({
            ...f,
            citations: [mockCitation],
          })),
        }
      : pr,
  ),
  findings: mockReviewResult.findings.map((f) =>
    f.reviewer === "security" ? { ...f, citations: [mockCitation] } : f,
  ),
};
