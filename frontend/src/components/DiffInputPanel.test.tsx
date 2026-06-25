import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DiffInputPanel } from "./DiffInputPanel";
import { importComments } from "../api/importComments";
import type { ImportCommentsResponse } from "../types/gitImport";

vi.mock("../api/importComments", async (orig) => {
  const actual = await orig<typeof import("../api/importComments")>();
  return { ...actual, importComments: vi.fn() };
});

const mockImport = vi.mocked(importComments);

function importResponse(
  threads: ImportCommentsResponse["threads"],
): ImportCommentsResponse {
  return { provider: "github", threads, warnings: [] };
}

function importedThread(id: string, body: string) {
  return {
    thread: {
      id,
      status: "unknown" as const,
      comments: [{ id: `${id}-c1`, body }],
    },
    externalReference: { provider: "github" as const, commentId: id },
    warnings: [] as string[],
  };
}

describe("DiffInputPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

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

  // ---- Existing comment threads ----

  it("renders the comment threads input", () => {
    render(<DiffInputPanel isLoading={false} onRun={vi.fn()} />);
    expect(
      screen.getByText(/existing comment threads/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /add comment thread/i }),
    ).toBeInTheDocument();
  });

  it("does not send commentThreads when none are added", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(onRun.mock.calls[0][0].commentThreads).toBeUndefined();
  });

  it("does not send a comment thread row left empty", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    // Add a row but leave the comment body blank.
    await user.click(screen.getByRole("button", { name: /add comment thread/i }));
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(onRun.mock.calls[0][0].commentThreads).toBeUndefined();
  });

  it("includes a valid comment thread with optional fields when provided", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await user.click(screen.getByRole("button", { name: /add comment thread/i }));

    await user.type(screen.getByLabelText(/file path/i), "app/auth.py");
    await user.type(screen.getByLabelText(/^line/i), "5");
    await user.type(screen.getByLabelText(/author/i), "Reviewer");
    await user.type(
      screen.getByLabelText("Comment"),
      "Can we avoid swallowing this exception?",
    );

    await user.click(screen.getByRole("button", { name: /run review/i }));

    const request = onRun.mock.calls[0][0];
    expect(request.commentThreads).toHaveLength(1);
    const thread = request.commentThreads[0];
    expect(thread.filePath).toBe("app/auth.py");
    expect(thread.line).toBe(5);
    expect(thread.status).toBe("open");
    expect(thread.comments[0].body).toBe(
      "Can we avoid swallowing this exception?",
    );
    expect(thread.comments[0].author).toBe("Reviewer");
  });

  it("stops sending a thread once it is removed", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await user.click(screen.getByRole("button", { name: /add comment thread/i }));
    await user.type(screen.getByLabelText("Comment"), "Please fix this.");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(onRun.mock.calls[0][0].commentThreads).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: /remove thread/i }));
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(onRun.mock.calls[1][0].commentThreads).toBeUndefined();
  });

  // ---- Local import demo integration ----

  const loadImported = async (
    user: ReturnType<typeof userEvent.setup>,
    threads: ImportCommentsResponse["threads"],
  ) => {
    mockImport.mockResolvedValueOnce(importResponse(threads));
    fireEvent.change(screen.getByLabelText(/json payload/i), {
      target: { value: "[]" },
    });
    await user.click(
      screen.getByRole("button", { name: /normalize comments/i }),
    );
    await user.click(
      await screen.findByRole("button", { name: /load imported threads/i }),
    );
  };

  it("includes loaded imported threads in the review request", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await loadImported(user, [importedThread("imp-1", "Imported comment body.")]);

    // The imported group shows the thread.
    expect(
      screen.getByRole("group", { name: /imported comments/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /run review/i }));
    const request = onRun.mock.calls[0][0];
    expect(request.commentThreads).toHaveLength(1);
    expect(request.commentThreads[0].id).toBe("imp-1");
  });

  it("combines imported threads with manual threads", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await loadImported(user, [importedThread("imp-1", "Imported one.")]);

    // Add a manual thread too.
    await user.click(screen.getByRole("button", { name: /add comment thread/i }));
    await user.type(screen.getByLabelText("Comment"), "Manual comment.");

    await user.click(screen.getByRole("button", { name: /run review/i }));
    const request = onRun.mock.calls[0][0];
    const ids = request.commentThreads.map((t: { id: string }) => t.id);
    expect(ids).toContain("imp-1");
    expect(request.commentThreads).toHaveLength(2);
  });

  it("dedupes imported and manual threads by id", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await loadImported(user, [importedThread("dupe-id", "Imported version.")]);

    // Manual thread with the same id should be de-duped (imported wins, first).
    await user.click(screen.getByRole("button", { name: /add comment thread/i }));
    await user.type(screen.getByLabelText(/thread id/i), "dupe-id");
    await user.type(screen.getByLabelText("Comment"), "Manual version.");

    await user.click(screen.getByRole("button", { name: /run review/i }));
    const request = onRun.mock.calls[0][0];
    const matching = request.commentThreads.filter(
      (t: { id: string }) => t.id === "dupe-id",
    );
    expect(matching).toHaveLength(1);
    expect(matching[0].comments[0].body).toBe("Imported version.");
  });

  it("can clear imported threads", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<DiffInputPanel isLoading={false} onRun={onRun} />);

    await loadDemo(user);
    await loadImported(user, [importedThread("imp-1", "Imported one.")]);
    await user.click(screen.getByRole("button", { name: /clear imported/i }));

    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(onRun.mock.calls[0][0].commentThreads).toBeUndefined();
  });
});
