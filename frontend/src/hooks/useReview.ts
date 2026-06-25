/** Hook that manages the lifecycle of a review request. */

import { useCallback, useRef, useState } from "react";

import { ReviewApiError, runReview } from "../api/reviews";
import type { ReviewRequest, ReviewResponse } from "../types/review";

export type ReviewStatus = "idle" | "loading" | "success" | "error";

export interface UseReviewResult {
  status: ReviewStatus;
  result: ReviewResponse | null;
  error: string | null;
  submit: (request: ReviewRequest) => Promise<void>;
  reset: () => void;
}

export function useReview(): UseReviewResult {
  const [status, setStatus] = useState<ReviewStatus>("idle");
  const [result, setResult] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(async (request: ReviewRequest) => {
    // Cancel any in-flight request before starting a new one.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setError(null);

    try {
      const response = await runReview(request, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setResult(response);
      setStatus("success");
    } catch (err) {
      if (controller.signal.aborted) {
        return;
      }
      const message =
        err instanceof ReviewApiError
          ? err.message
          : "Something went wrong while running the review.";
      setError(message);
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, submit, reset };
}
