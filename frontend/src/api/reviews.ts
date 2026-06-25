/**
 * Typed client for the review API.
 *
 * Calls the backend through the Vite dev proxy (`/api/*` -> `http://localhost:8000`),
 * so no base URL or CORS handling is needed in the client.
 */

import type { ReviewRequest, ReviewResponse } from "../types/review";

/** Raised when the API responds with a non-2xx status. */
export class ReviewApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ReviewApiError";
    this.status = status;
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  // FastAPI validation/errors usually arrive as JSON `{ detail: ... }`.
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

/** Run a multi-persona review for the given request. */
export async function runReview(
  request: ReviewRequest,
  signal?: AbortSignal,
): Promise<ReviewResponse> {
  let response: Response;
  try {
    response = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (cause) {
    throw new ReviewApiError(
      "Could not reach the review service. Is the backend running on port 8000?",
      0,
    );
  }

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new ReviewApiError(message, response.status);
  }

  return (await response.json()) as ReviewResponse;
}
