import type { ReactNode } from "react";

import type { CommentThread, ReviewResponse } from "../types/review";
import type { ReviewStatus } from "../hooks/useReview";
import { ContextUsedPanel } from "./ContextUsedPanel";
import { ExportMarkdownButton } from "./ExportMarkdownButton";
import { FindingsPanel } from "./FindingsPanel";
import { MergeRecommendationBadge } from "./MergeRecommendationBadge";
import { RiskBadge } from "./RiskBadge";
import { SuggestedRepliesPanel } from "./SuggestedRepliesPanel";

interface ReviewSummaryProps {
  status: ReviewStatus;
  result: ReviewResponse | null;
  error: string | null;
  /** MR title from the submitted request, used in the exported report. */
  title?: string | null;
  /** Submitted comment threads, for suggested-reply file/line context. */
  commentThreads?: CommentThread[] | null;
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: "danger";
}) {
  return (
    <div className="stat">
      <span className={`stat__value${tone ? ` stat__value--${tone}` : ""}`}>
        {value}
      </span>
      <span className="stat__label">{label}</span>
    </div>
  );
}

function PanelShell({ children }: { children: ReactNode }) {
  return (
    <section className="panel results">
      <h2 className="panel__title">Review</h2>
      {children}
    </section>
  );
}

export function ReviewSummary({
  status,
  result,
  error,
  title,
  commentThreads,
}: ReviewSummaryProps) {
  if (status === "idle") {
    return (
      <PanelShell>
        <div className="results__empty">
          <p>No review yet.</p>
          <p className="results__empty-hint">
            Add a diff, choose personas, and run a review to see results here.
          </p>
        </div>
      </PanelShell>
    );
  }

  if (status === "loading") {
    return (
      <PanelShell>
        <div className="results__empty">
          <div className="spinner" aria-hidden="true" />
          <p>Running the review council...</p>
        </div>
      </PanelShell>
    );
  }

  if (status === "error") {
    return (
      <PanelShell>
        <div className="results__error" role="alert">
          <p className="results__error-title">Review failed</p>
          <p>{error}</p>
        </div>
      </PanelShell>
    );
  }

  if (!result) {
    return null;
  }

  const { summary, diffStats, findings, personaReviews } = result;
  const highCount = findings.filter((f) => f.severity === "high").length;

  return (
    <PanelShell>
      <div className="results__toolbar">
        <div className="verdict">
          <RiskBadge risk={result.overallRisk} />
          <MergeRecommendationBadge
            recommendation={result.mergeRecommendation}
          />
        </div>
        <ExportMarkdownButton result={result} title={title} />
      </div>

      <h3 className="results__headline">{summary.headline}</h3>
      <p className="results__details">{summary.details}</p>

      <div className="stats">
        <Stat label="Files" value={diffStats.filesChanged} />
        <Stat label="Added" value={`+${diffStats.addedLines}`} />
        <Stat label="Removed" value={`-${diffStats.removedLines}`} />
        <Stat label="Hunks" value={diffStats.totalHunks} />
        <Stat label="Findings" value={summary.totalFindings} />
        <Stat
          label="High"
          value={highCount}
          tone={highCount > 0 ? "danger" : undefined}
        />
        <Stat label="Personas" value={personaReviews.length} />
      </div>

      <FindingsPanel personaReviews={personaReviews} findings={findings} />

      <ContextUsedPanel contextUsed={result.contextUsed} />

      <SuggestedRepliesPanel
        replies={result.suggestedReplies}
        commentThreads={commentThreads}
      />
    </PanelShell>
  );
}
