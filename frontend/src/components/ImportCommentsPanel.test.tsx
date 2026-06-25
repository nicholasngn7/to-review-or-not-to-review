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

  // ---- Bundled sample payloads ----

  it("renders a button for each bundled sample", () => {
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);
    const group = screen.getByRole("group", { name: /load sample payload/i });
    expect(
      within(group).getByRole("button", { name: /github review comments/i }),
    ).toBeInTheDocument();
    expect(
      within(group).getByRole("button", { name: /github issue comments/i }),
    ).toBeInTheDocument();
    expect(
      within(group).getByRole("button", { name: /gitlab discussions/i }),
    ).toBeInTheDocument();
  });

  it("loads the GitHub review sample into provider/source/JSON without calling the API", async () => {
    const user = userEvent.setup();
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    await user.click(
      screen.getByRole("button", { name: /github review comments/i }),
    );

    expect(screen.getByLabelText("Provider")).toHaveValue("github");
    expect(screen.getByLabelText("Source")).toHaveValue("github_review_comments");
    const json = screen.getByLabelText(/json payload/i) as HTMLTextAreaElement;
    expect(json.value).toContain("in_reply_to_id");
    expect(json.value).toContain("service/auth.py");
    // Pretty-printed (indented) JSON, and the API is untouched until Normalize.
    expect(json.value).toContain("\n  ");
    expect(mockImport).not.toHaveBeenCalled();
  });

  it("loads the GitHub issue sample into provider/source/JSON", async () => {
    const user = userEvent.setup();
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    await user.click(
      screen.getByRole("button", { name: /github issue comments/i }),
    );

    expect(screen.getByLabelText("Provider")).toHaveValue("github");
    expect(screen.getByLabelText("Source")).toHaveValue("github_issue_comments");
    const json = screen.getByLabelText(/json payload/i) as HTMLTextAreaElement;
    expect(json.value).toContain("issuecomment-2001");
    expect(mockImport).not.toHaveBeenCalled();
  });

  it("loads the GitLab sample into provider/source/JSON", async () => {
    const user = userEvent.setup();
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    await user.click(
      screen.getByRole("button", { name: /gitlab discussions/i }),
    );

    expect(screen.getByLabelText("Provider")).toHaveValue("gitlab");
    expect(screen.getByLabelText("Source")).toHaveValue("gitlab_discussions");
    const json = screen.getByLabelText(/json payload/i) as HTMLTextAreaElement;
    expect(json.value).toContain("disc-1");
    expect(mockImport).not.toHaveBeenCalled();
  });

  it("requires an explicit Normalize click after loading a sample", async () => {
    const user = userEvent.setup();
    mockImport.mockResolvedValueOnce(
      response({ threads: [importedThread("t-1", "Sample body")] }),
    );
    render(<ImportCommentsPanel onLoadThreads={vi.fn()} />);

    await user.click(
      screen.getByRole("button", { name: /github review comments/i }),
    );
    expect(mockImport).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /normalize comments/i }));
    expect(mockImport).toHaveBeenCalledTimes(1);
    expect(mockImport.mock.calls[0][0].provider).toBe("github");
    expect(mockImport.mock.calls[0][0].source).toBe("github_review_comments");
  });
});
