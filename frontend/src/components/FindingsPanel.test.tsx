import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FindingsPanel } from "./FindingsPanel";
import { mockReviewResult } from "../test/fixtures";

function renderPanel() {
  return render(
    <FindingsPanel
      personaReviews={mockReviewResult.personaReviews}
      findings={mockReviewResult.findings}
    />,
  );
}

describe("FindingsPanel filtering", () => {
  it("shows all findings by default", () => {
    renderPanel();
    expect(screen.getByText("Possible use of eval()")).toBeInTheDocument();
    expect(
      screen.getByText("Production code changed without test updates"),
    ).toBeInTheDocument();
  });

  it("filters by severity", async () => {
    const user = userEvent.setup();
    renderPanel();

    const severityGroup = screen.getByRole("group", {
      name: /filter by severity/i,
    });
    await user.click(within(severityGroup).getByRole("button", { name: "Medium" }));

    // Only the medium (QA) finding remains; the high (security) one is hidden.
    expect(
      screen.getByText("Production code changed without test updates"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Possible use of eval()")).not.toBeInTheDocument();
  });

  it("filters by reviewer tab", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole("tab", { name: /security/i }));

    expect(screen.getByText("Possible use of eval()")).toBeInTheDocument();
    expect(
      screen.queryByText("Production code changed without test updates"),
    ).not.toBeInTheDocument();
  });

  it("renders the positive empty state when there are no findings", () => {
    render(<FindingsPanel personaReviews={[]} findings={[]} />);
    expect(screen.getByText(/no findings found/i)).toBeInTheDocument();
  });
});
