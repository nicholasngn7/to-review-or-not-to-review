import { describe, expect, it } from "vitest";

import { buildReportFilename, exportReviewMarkdown } from "./exportMarkdown";
import { mockReviewResult } from "../test/fixtures";

describe("buildReportFilename", () => {
  it("returns the base name when there is no title", () => {
    expect(buildReportFilename()).toBe("mr-review-council-report.md");
    expect(buildReportFilename(null)).toBe("mr-review-council-report.md");
    expect(buildReportFilename("   ")).toBe("mr-review-council-report.md");
  });

  it("appends a sanitized slug from the title", () => {
    expect(buildReportFilename("Add login handler!")).toBe(
      "mr-review-council-report-add-login-handler.md",
    );
  });
});

describe("exportReviewMarkdown", () => {
  const md = exportReviewMarkdown(mockReviewResult, "Add login handler");

  it("includes the report header and the MR title", () => {
    expect(md).toContain("# MR Review Council Report");
    expect(md).toContain("Add login handler");
  });

  it("includes the overall risk, recommendation, and summary", () => {
    expect(md).toContain("**Overall risk:** High");
    expect(md).toContain("**Merge recommendation:** Needs human review");
    expect(md).toContain("Needs human review before merge.");
  });

  it("includes findings grouped by every reviewer (full result, not filtered)", () => {
    expect(md).toContain("### Security");
    expect(md).toContain("### QA / Test");
    expect(md).toContain("Possible use of eval()");
    expect(md).toContain("Production code changed without test updates");
  });

  it("falls back to a placeholder title when none is given", () => {
    const out = exportReviewMarkdown(mockReviewResult);
    expect(out).toContain("Untitled merge request");
  });

  it("renders a clean-state report when there are no findings", () => {
    const clean = {
      ...mockReviewResult,
      findings: [],
      personaReviews: [],
      summary: { ...mockReviewResult.summary, totalFindings: 0 },
    };
    const out = exportReviewMarkdown(clean, "Clean change");
    expect(out).toContain("No findings found.");
  });

  it("omits the suggested replies section when there are none", () => {
    expect(md).not.toContain("## Suggested replies");
  });

  it("includes suggested replies grouped by thread when present", () => {
    const withReplies = {
      ...mockReviewResult,
      suggestedReplies: [
        {
          id: "reply-t1-security",
          threadId: "t1",
          reviewer: "security" as const,
          suggestedReply: "Can we confirm the token is handled safely?",
          rationale: 'The comment mentions "token", which maps to Security.',
          confidence: 0.6,
          needsHumanReview: true,
          filePath: "app/auth.py",
          line: 5,
        },
      ],
    };
    const out = exportReviewMarkdown(withReplies, "Add login handler");
    expect(out).toContain("## Suggested replies");
    expect(out).toContain("### Thread `t1`");
    expect(out).toContain("#### Security");
    expect(out).toContain("**Location:** `app/auth.py` · line 5");
    expect(out).toContain("Can we confirm the token is handled safely?");
    expect(out).toContain("**Rationale:**");
    expect(out).toContain("**Confidence:** 60%");
    expect(out).toContain("**Needs human review before sending.**");
  });
});
