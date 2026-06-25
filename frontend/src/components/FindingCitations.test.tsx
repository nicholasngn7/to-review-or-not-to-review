import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { FindingCitations } from "./FindingCitations";
import { mockCitation } from "../test/fixtures";

describe("FindingCitations", () => {
  it("renders citation location, score, and snippet when present", () => {
    render(<FindingCitations citations={[mockCitation]} />);

    expect(screen.getByText("Cited context")).toBeInTheDocument();
    expect(
      screen.getByText(/docs\/decisions\.md · Authentication · lines 12–18/),
    ).toBeInTheDocument();
    expect(screen.getByText(/score 0\.42/)).toBeInTheDocument();
    expect(
      screen.getByText(/Avoid eval\(\); parse input with a safe/),
    ).toBeInTheDocument();
  });

  it("uses provenance-only wording and does not imply severity changes", () => {
    render(<FindingCitations citations={[mockCitation]} />);
    expect(
      screen.getByText(/provenance only.*did not change/i),
    ).toBeInTheDocument();
  });

  it("renders nothing when citations are empty", () => {
    const { container } = render(<FindingCitations citations={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when citations are absent", () => {
    const { container } = render(<FindingCitations citations={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
