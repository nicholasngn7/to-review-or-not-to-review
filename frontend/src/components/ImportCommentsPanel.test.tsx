import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ImportCommentsPanel } from "./ImportCommentsPanel";
import { ImportApiError, importComments } from "../api/importComments";
import type { ImportCommentsResponse } from "../types/gitImport";

vi.mock("../api/importComments", async (orig) => {
  const actual = await orig<typeof import("../api/importComments")>();
  return { ...actual, importComments: vi.fn() };
});

const mockImport = vi.mocked(importComments);

/** Set the JSON textarea directly (avoids userEvent's special-char parsing). */
function setJson(value: string) {
  fireEvent.change(screen.getByLabelText(/json payload/i), {
    target: { value },
  });
}

function importedThread(id: string, body: string, extra = {}) {
  return {
    thread: {
      id,
      status: "unknown" as const,
      comments: [{ id: `${id}-c1`, body }],
      ...extra,
    },
    externalReference: { provider: "github" as const, commentId: id },
    warnings: [] as string[],
  };
}

function response(
  overrides: Partial<ImportCommentsResponse> = {},
): ImportCommentsResponse {
  return { provider: "github", threads: [], warnings: [], ...overrides };
}

describe("ImportCommentsPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders provider/source controls and the JSON textarea", () => {
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);
    expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    expect(screen.getByLabelText("Source")).toBeInTheDocument();
    expect(screen.getByLabelText(/json payload/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /normalize comments/i }),
    ).toBeInTheDocument();
  });

  it("filters source options by provider", async () => {
    const user = userEvent.setup();
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    const sourceSelect = screen.getByLabelText("Source");
    expect(within(sourceSelect).getAllByRole("option")).toHaveLength(2);

    await user.selectOptions(screen.getByLabelText("Provider"), "gitlab");
    const gitlabOptions = within(screen.getByLabelText("Source")).getAllByRole(
      "option",
    );
    expect(gitlabOptions).toHaveLength(1);
    expect(gitlabOptions[0]).toHaveTextContent(/MR discussions/i);
  });

  it("shows an error and does not call the API for invalid JSON", async () => {
    const user = userEvent.setup();
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    setJson("not json {");
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/valid json/i);
    expect(mockImport).not.toHaveBeenCalled();
  });

  it("calls the API with a camelCase request", async () => {
    const user = userEvent.setup();
    mockImport.mockResolvedValueOnce(response());
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    setJson('[{"id": 1, "body": "hi"}]');
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));

    expect(mockImport).toHaveBeenCalledTimes(1);
    expect(mockImport).toHaveBeenCalledWith({
      provider: "github",
      source: "github_review_comments",
      rawPayload: [{ id: 1, body: "hi" }],
    });
  });

  it("renders the count, warnings, and a preview after success", async () => {
    const user = userEvent.setup();
    mockImport.mockResolvedValueOnce(
      response({
        threads: [
          importedThread("t-1", "Please validate this input.", {
            filePath: "app/api.py",
            line: 12,
          }),
          importedThread("t-2", "Add a regression test."),
        ],
        warnings: ["reply 1007 references missing root 9999"],
      }),
    );
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    setJson("[]");
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));

    expect(await screen.findByText(/2 threads normalized/i)).toBeInTheDocument();
    expect(
      screen.getByText(/references missing root 9999/i),
    ).toBeInTheDocument();
    // Preview content.
    expect(screen.getByText("t-1")).toBeInTheDocument();
    expect(screen.getByText(/Please validate this input/i)).toBeInTheDocument();
    expect(screen.getByText(/app\/api\.py · line 12/i)).toBeInTheDocument();
  });

  it("loads imported threads as CommentThread[] via onLoadThreads", async () => {
    const user = userEvent.setup();
    const onLoad = vi.fn();
    mockImport.mockResolvedValueOnce(
      response({ threads: [importedThread("t-1", "Body one")] }),
    );
    render(<ImportCommentsPanel onLoadThreads={onLoad} />);

    setJson("[]");
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));
    await user.click(
      await screen.findByRole("button", { name: /load imported threads/i }),
    );

    expect(onLoad).toHaveBeenCalledTimes(1);
    const loaded = onLoad.mock.calls[0][0];
    expect(loaded).toHaveLength(1);
    expect(loaded[0].id).toBe("t-1");
    expect(loaded[0].comments[0].body).toBe("Body one");
  });

  it("disables Load when no threads were produced", async () => {
    const user = userEvent.setup();
    mockImport.mockResolvedValueOnce(
      response({ warnings: ["nothing usable in payload"] }),
    );
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    setJson("[]");
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));

    expect(
      await screen.findByText(/no comment threads were produced/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /load imported threads/i }),
    ).toBeDisabled();
  });

  it("renders a friendly message on API error", async () => {
    const user = userEvent.setup();
    mockImport.mockRejectedValueOnce(new ImportApiError("Unsupported source", 400));
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    setJson("[]");
    await user.click(screen.getByRole("button", { name: /normalize comments/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /unsupported source/i,
    );
  });

  it("exposes no token or URL input", () => {
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);
    expect(screen.queryByLabelText(/token/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/url/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/oauth/i)).not.toBeInTheDocument();
  });
});
