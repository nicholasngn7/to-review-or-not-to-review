import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DiffInputPanel } from "./DiffInputPanel";

describe("DiffInputPanel", () => {
  it("disables Run Review while the diff is empty", () => {
    render(<DiffInputPanel isLoading={false} onRun={vi.fn()} />);
    const runButton = screen.getByRole("button", { name: /run review/i });
    expect(runButton).toBeDisabled();
    expect(screen.getByText(/paste or upload a diff to begin/i)).toBeInTheDocument();
  });

  it("loads a demo diff into the form and enables Run Review", async () => {
    const user = userEvent.setup();
    render(<DiffInputPanel isLoading={false} onRun={vi.fn()} />);

    await user.click(
      screen.getByRole("button", { name: /low-risk frontend change/i }),
    );

    // Title + diff get populated from the sample.
    expect(screen.getByLabelText(/title/i)).toHaveValue(
      "Add reset button to Counter",
    );
    const diff = screen.getByLabelText("Diff", {
      exact: true,
    }) as HTMLTextAreaElement;
    expect(diff.value).toContain("diff --git");

    // With a diff present and personas selected, Run Review is enabled.
    expect(screen.getByRole("button", { name: /run review/i })).toBeEnabled();
  });

  it("submits a built request when Run Review is clicked", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await user.click(
      screen.getByRole("button", { name: /risky backend auth change/i }),
    );
    await user.click(screen.getByRole("button", { name: /run review/i }));

    expect(onRun).toHaveBeenCalledTimes(1);
    const request = onRun.mock.calls[0][0];
    expect(request.diffText).toContain("diff --git");
    expect(request.selectedPersonas.length).toBeGreaterThan(0);
    expect(request.title).toBe("Add login handler to auth service");
  });
});
