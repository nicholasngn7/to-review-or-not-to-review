import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
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

  // ---- Reviewer voice (tone) ----

  const loadDemo = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(
      screen.getByRole("button", { name: /risky backend auth change/i }),
    );
  };

  it("renders the Reviewer voice controls", () => {
    render(<DiffInputPanel isLoading={false} onRun={vi.fn()} />);
    expect(screen.getByText(/reviewer voice/i)).toBeInTheDocument();
    expect(
      screen.getByText(/wording and framing/i),
    ).toBeInTheDocument();
    // The global voice selects are present.
    expect(screen.getByLabelText("Tone")).toBeInTheDocument();
    expect(screen.getByLabelText("Strictness")).toBeInTheDocument();
    expect(screen.getByLabelText("Verbosity")).toBeInTheDocument();
  });

  it("omits tone fields when the voice is left at default", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await user.click(screen.getByRole("button", { name: /run review/i }));

    const request = onRun.mock.calls[0][0];
    expect(request.toneProfile).toBeUndefined();
    expect(request.personaToneProfiles).toBeUndefined();
  });

  it("sends toneProfile when the global voice changes", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await user.selectOptions(screen.getByLabelText("Tone"), "supportive");
    await user.selectOptions(screen.getByLabelText("Verbosity"), "detailed");
    await user.click(screen.getByRole("button", { name: /run review/i }));

    const request = onRun.mock.calls[0][0];
    expect(request.toneProfile).toEqual({
      style: "supportive",
      strictness: "medium",
      verbosity: "detailed",
    });
    // No custom instructions were typed, so the field is omitted.
    expect(request.toneProfile.customInstructions).toBeUndefined();
  });

  it("sends custom instructions only when non-empty", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    const custom = screen.getByLabelText(/custom reviewer instructions/i);
    await user.type(custom, "   ");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    // Whitespace-only is treated as default -> nothing sent.
    expect(onRun.mock.calls[0][0].toneProfile).toBeUndefined();

    await user.clear(custom);
    await user.type(custom, "Reference the style guide.");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    const request = onRun.mock.calls[1][0];
    expect(request.toneProfile.customInstructions).toBe(
      "Reference the style guide.",
    );
  });

  it("sends personaToneProfiles when a per-persona override is enabled", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    // Enable the Security override (Security is in the risky demo's personas).
    const overrides = screen.getByRole("group", {
      name: /per-reviewer overrides/i,
    });
    await user.click(
      within(overrides).getByRole("checkbox", { name: /security/i }),
    );
    // Adjust the Security override style (the override editor's "Tone" select).
    const toneSelects = screen.getAllByLabelText("Tone");
    await user.selectOptions(toneSelects[toneSelects.length - 1], "strict");
    await user.click(screen.getByRole("button", { name: /run review/i }));

    const request = onRun.mock.calls[0][0];
    expect(request.personaToneProfiles).toBeDefined();
    expect(request.personaToneProfiles.security.style).toBe("strict");
  });

  it("only offers overrides for selected personas", async () => {
    const user = userEvent.setup();
    render(<DiffInputPanel isLoading={false} onRun={vi.fn()} />);

    await loadDemo(user);
    // Scope to the overrides group; the persona *selector* always lists all 7.
    const overrides = screen.getByRole("group", {
      name: /per-reviewer overrides/i,
    });
    // The risky demo selects security/qa/backend/sre but not "Product".
    expect(
      within(overrides).getByRole("checkbox", { name: /security/i }),
    ).toBeInTheDocument();
    expect(
      within(overrides).queryByRole("checkbox", { name: /product/i }),
    ).not.toBeInTheDocument();
  });

  it("ignores an override for a persona that is later deselected", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    const overrides = screen.getByRole("group", {
      name: /per-reviewer overrides/i,
    });
    await user.click(
      within(overrides).getByRole("checkbox", { name: /security/i }),
    );

    // Deselect the Security persona via the persona selector card (first match
    // in DOM order; the override toggle lives further down).
    const personaCheckboxes = screen.getAllByRole("checkbox", {
      name: /security/i,
    });
    await user.click(personaCheckboxes[0]);

    await user.click(screen.getByRole("button", { name: /run review/i }));
    const request = onRun.mock.calls[0][0];
    expect(request.selectedPersonas).not.toContain("security");
    expect(request.personaToneProfiles).toBeUndefined();
  });
});
