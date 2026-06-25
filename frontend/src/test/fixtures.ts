import type { ReviewResponse } from "../types/review";

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
};
