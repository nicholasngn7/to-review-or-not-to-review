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
    filePath: "app/auth.py",
    line: 5,
  },
  {
    id: "reply-t1-qa",
    threadId: "t1",
    reviewer: "qa",
    suggestedReply: "Could we add a regression test for this case?",
    rationale: 'The comment mentions "test", which maps to the QA reviewer.',
    confidence: 0.6,
    needsHumanReview: true,
    filePath: "app/auth.py",
    line: 5,
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

  it("renders nothing when there are no replies and no threads were submitted", () => {
    const { container } = render(<SuggestedRepliesPanel replies={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an empty state when threads were submitted but no replies generated", () => {
    render(<SuggestedRepliesPanel replies={[]} commentThreads={THREADS} />);
    expect(
      screen.getByText(
        /no suggested replies were generated for the submitted comment threads/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders replies with file/line taken from each reply", () => {
    render(<SuggestedRepliesPanel replies={REPLIES} />);

    expect(screen.getByText("Suggested replies")).toBeInTheDocument();
    expect(
      screen.getByText(/Can we confirm the token is safe\?/),
    ).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
    expect(screen.getByText("QA / Test")).toBeInTheDocument();
    expect(screen.getAllByText(/needs human review/i)).toHaveLength(2);
    // File/line render straight from the reply (no thread lookup).
    expect(screen.getAllByText(/app\/auth\.py · line 5/)).toHaveLength(2);
  });

  it("copies a single reply's text", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    render(<SuggestedRepliesPanel replies={[REPLIES[0]]} />);

    await user.click(screen.getByRole("button", { name: /^copy reply$/i }));
    expect(writeText).toHaveBeenCalledWith(REPLIES[0].suggestedReply);
    expect(
      await screen.findByRole("button", { name: /^copied$/i }),
    ).toBeInTheDocument();
  });

  it("copies all replies for a thread with reviewer labels", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    render(<SuggestedRepliesPanel replies={REPLIES} />);

    await user.click(
      screen.getByRole("button", { name: /copy all replies for this thread/i }),
    );

    const expected =
      `Security: ${REPLIES[0].suggestedReply}\n\n` +
      `QA / Test: ${REPLIES[1].suggestedReply}`;
    expect(writeText).toHaveBeenCalledWith(expected);
    expect(
      await screen.findByRole("button", { name: /copied thread replies/i }),
    ).toBeInTheDocument();
  });
});
