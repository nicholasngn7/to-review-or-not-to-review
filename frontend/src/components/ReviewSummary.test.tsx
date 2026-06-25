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
});
