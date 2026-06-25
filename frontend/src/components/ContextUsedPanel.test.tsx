import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ContextUsedPanel } from "./ContextUsedPanel";
import { mockRetrievalResult } from "../test/fixtures";

describe("ContextUsedPanel", () => {
  it("renders sourcePath, heading, line range, score, and snippet", () => {
    render(<ContextUsedPanel contextUsed={[mockRetrievalResult]} />);

    // Location combines path · heading · line range.
    expect(
      screen.getByText(/docs\/decisions\.md · Authentication · lines 12–18/),
    ).toBeInTheDocument();
    // Score is rounded to two decimals.
    expect(screen.getByText(/score 0\.42/)).toBeInTheDocument();
    expect(
      screen.getByText(/Avoid eval\(\); parse input with a safe/),
    ).toBeInTheDocument();
  });

  it("uses honest, provenance-only wording", () => {
    render(<ContextUsedPanel contextUsed={[mockRetrievalResult]} />);
    // Title (exact) plus the provenance note both mention local context.
    expect(screen.getByText("Retrieved local context")).toBeInTheDocument();
    expect(
      screen.getByText(/lexical, provenance-only/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/not semantic search/i)).toBeInTheDocument();
  });

  it("renders nothing when contextUsed is empty", () => {
    const { container } = render(<ContextUsedPanel contextUsed={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when contextUsed is absent", () => {
    const { container } = render(<ContextUsedPanel contextUsed={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
