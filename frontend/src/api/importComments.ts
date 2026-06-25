/**
 * Typed client for the local-only comment-import API.
 *
 * Calls `POST /api/import-comments` through the Vite dev proxy. The endpoint
 * normalizes a caller-supplied, fixture-shaped payload — it does NOT fetch from
 * GitHub/GitLab, use tokens/OAuth, or post anything.
 */

import type {
  ImportCommentsRequest,
  ImportCommentsResponse,
} from "../types/gitImport";

/** Raised when the import API responds with a non-2xx status. */
export class ImportApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ImportApiError";
    this.status = status;
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  // FastAPI errors usually arrive as JSON `{ detail: ... }`.
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first?.msg) {
        const loc = Array.isArray(first.loc) ? first.loc.join(".") : "";
        return loc ? `${first.msg} (${loc})` : first.msg;
      }
    }
    return JSON.stringify(data);
  } catch {
    return response.statusText || "Request failed";
  }
}

/** Normalize a caller-supplied provider comment payload into comment threads. */
export async function importComments(
  request: ImportCommentsRequest,
  signal?: AbortSignal,
): Promise<ImportCommentsResponse> {
  let response: Response;
  try {
    response = await fetch("/api/import-comments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (cause) {
    throw new ImportApiError(
      "Could not reach the import service. Is the backend running on port 8000?",
      0,
    );
  }

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new ImportApiError(message, response.status);
  }

  return (await response.json()) as ImportCommentsResponse;
}
