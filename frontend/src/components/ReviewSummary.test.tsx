import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReviewSummary } from "./ReviewSummary";
import { mockReviewResult } from "../test/fixtures";

describe("ReviewSummary", () => {
  it("shows the idle empty state before a review runs", () => {
    render(<ReviewSummary status="idle" result={null} error={null} />);
    expect(screen.getByText(/no review yet/i)).toBeInTheDocument();
  });

  it("shows an error state with the message", () => {
    render(
      <ReviewSummary status="error" result={null} error="Something broke" />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders the verdict, summary, stats, and findings on success", () => {
    render(
      <ReviewSummary
        status="success"
        result={mockReviewResult}
        error={null}
        title="Add login handler"
      />,
    );

    expect(
      screen.getByText("Needs human review before merge."),
    ).toBeInTheDocument();
    // Both findings render.
    expect(screen.getByText("Possible use of eval()")).toBeInTheDocument();
    expect(
      screen.getByText("Production code changed without test updates"),
    ).toBeInTheDocument();
    // Export action is available.
    expect(
      screen.getByRole("button", { name: /export markdown/i }),
    ).toBeInTheDocument();
  });

  it("does not render a suggested replies section when there are none", () => {
    render(
      <ReviewSummary status="success" result={mockReviewResult} error={null} />,
    );
    expect(screen.queryByText("Suggested replies")).not.toBeInTheDocument();
  });

  it("renders suggested replies when present", () => {
    const result = {
      ...mockReviewResult,
      suggestedReplies: [
        {
          id: "reply-t1-security",
          threadId: "t1",
          reviewer: "security" as const,
          suggestedReply: "Can we confirm the token is handled safely?",
          rationale: 'The comment mentions "token".',
          confidence: 0.6,
          needsHumanReview: true,
          filePath: "app/auth.py",
          line: 5,
        },
      ],
    };
    render(
      <ReviewSummary status="success" result={result} error={null} />,
    );

    expect(screen.getByText("Suggested replies")).toBeInTheDocument();
    expect(
      screen.getByText(/Can we confirm the token is handled safely\?/),
    ).toBeInTheDocument();
    // File/line render directly from the reply, no commentThreads prop needed.
    expect(screen.getByText(/app\/auth\.py · line 5/)).toBeInTheDocument();
  });
});
