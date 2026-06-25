import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SuggestedRepliesPanel } from "./SuggestedRepliesPanel";
import type { CommentThread, SuggestedReply } from "../types/review";

const REPLIES: SuggestedReply[] = [
  {
    id: "reply-t1-security",
    threadId: "t1",
    reviewer: "security",
    suggestedReply: "Thanks for the review comment. Can we confirm the token is safe?",
    rationale: 'The comment mentions "token", which maps to the Security reviewer.',
    confidence: 0.6,
    needsHumanReview: true,
  },
  {
    id: "reply-t1-qa",
    threadId: "t1",
    reviewer: "qa",
    suggestedReply: "Could we add a regression test for this case?",
    rationale: 'The comment mentions "test", which maps to the QA reviewer.',
    confidence: 0.6,
    needsHumanReview: true,
  },
];

const THREADS: CommentThread[] = [
  {
    id: "t1",
    filePath: "app/auth.py",
    line: 5,
    status: "open",
    comments: [{ id: "c1", author: "Reviewer", body: "Is the token safe? add a test" }],
  },
];

describe("SuggestedRepliesPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when there are no replies", () => {
    const { container } = render(<SuggestedRepliesPanel replies={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders replies grouped under their thread with metadata", () => {
    render(
      <SuggestedRepliesPanel replies={REPLIES} commentThreads={THREADS} />,
    );

    expect(screen.getByText("Suggested replies")).toBeInTheDocument();
    expect(
      screen.getByText(/Can we confirm the token is safe\?/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Could we add a regression test/),
    ).toBeInTheDocument();
    // Persona labels and human-review badges.
    expect(screen.getByText("Security")).toBeInTheDocument();
    expect(screen.getByText("QA / Test")).toBeInTheDocument();
    expect(screen.getAllByText(/needs human review/i)).toHaveLength(2);
    // File/line context comes from the thread (one per reply in the thread).
    expect(screen.getAllByText(/app\/auth\.py · line 5/)).toHaveLength(2);
  });

  it("copies only the suggested reply text", async () => {
    const user = userEvent.setup();
    // userEvent.setup() installs a clipboard stub; spy on it.
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    render(
      <SuggestedRepliesPanel replies={[REPLIES[0]]} commentThreads={THREADS} />,
    );

    await user.click(screen.getByRole("button", { name: /copy reply/i }));
    expect(writeText).toHaveBeenCalledWith(REPLIES[0].suggestedReply);
    // Temporary confirmation appears.
    expect(
      await screen.findByRole("button", { name: /copied/i }),
    ).toBeInTheDocument();
  });
});
