import type {
  FindingSeverity,
  MergeRecommendation,
  ReviewFinding,
  ReviewResponse,
  ReviewerPersona,
  RiskLevel,
} from "../types/review";
import type { ReviewStatus } from "../hooks/useReview";
import { PERSONA_OPTIONS } from "./PersonaSelector";

const PERSONA_LABELS: Record<ReviewerPersona, string> = Object.fromEntries(
  PERSONA_OPTIONS.map((o) => [o.value, o.label]),
) as Record<ReviewerPersona, string>;

const RISK_LABELS: Record<RiskLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

const RECOMMENDATION_LABELS: Record<MergeRecommendation, string> = {
  ready: "Ready",
  ready_with_followups: "Ready with follow-ups",
  needs_changes: "Needs changes",
  needs_human_review: "Needs human review",
};

const SEVERITY_LABELS: Record<FindingSeverity, string> = {
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
};

interface ReviewSummaryProps {
  status: ReviewStatus;
  result: ReviewResponse | null;
  error: string | null;
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat">
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  );
}

function FindingCard({ finding }: { finding: ReviewFinding }) {
  return (
    <li className={`finding finding--${finding.severity}`}>
      <div className="finding__head">
        <span className={`pill pill--sev-${finding.severity}`}>
          {SEVERITY_LABELS[finding.severity]}
        </span>
        <span className="pill pill--persona">
          {PERSONA_LABELS[finding.reviewer] ?? finding.reviewer}
        </span>
        {finding.filePath && (
          <span className="finding__path">{finding.filePath}</span>
        )}
      </div>
      <h4 className="finding__title">{finding.title}</h4>
      <p className="finding__text">{finding.explanation}</p>
      <p className="finding__rec">
        <span className="finding__rec-label">Recommendation:</span>{" "}
        {finding.recommendation}
      </p>
    </li>
  );
}

export function ReviewSummary({ status, result, error }: ReviewSummaryProps) {
  if (status === "idle") {
    return (
      <section className="panel results">
        <h2 className="panel__title">Review</h2>
        <div className="results__empty">
          <p>No review yet.</p>
          <p className="results__empty-hint">
            Add a diff, choose personas, and run a review to see results here.
          </p>
        </div>
      </section>
    );
  }

  if (status === "loading") {
    return (
      <section className="panel results">
        <h2 className="panel__title">Review</h2>
        <div className="results__empty">
          <div className="spinner" aria-hidden="true" />
          <p>Running the review council...</p>
        </div>
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className="panel results">
        <h2 className="panel__title">Review</h2>
        <div className="results__error" role="alert">
          <p className="results__error-title">Review failed</p>
          <p>{error}</p>
        </div>
      </section>
    );
  }

  if (!result) {
    return null;
  }

  const { summary, diffStats, findings } = result;

  return (
    <section className="panel results">
      <h2 className="panel__title">Review</h2>

      <div className="verdict">
        <span className={`badge badge--risk-${result.overallRisk}`}>
          Risk: {RISK_LABELS[result.overallRisk]}
        </span>
        <span className={`badge badge--rec-${result.mergeRecommendation}`}>
          {RECOMMENDATION_LABELS[result.mergeRecommendation]}
        </span>
      </div>

      <h3 className="results__headline">{summary.headline}</h3>
      <p className="results__details">{summary.details}</p>

      <div className="stats">
        <Stat label="Files" value={diffStats.filesChanged} />
        <Stat label="Added" value={`+${diffStats.addedLines}`} />
        <Stat label="Removed" value={`-${diffStats.removedLines}`} />
        <Stat label="Findings" value={summary.totalFindings} />
      </div>

      <h3 className="results__section-title">
        Findings ({findings.length})
      </h3>
      {findings.length === 0 ? (
        <p className="results__empty-hint">
          No findings from the selected personas. Looks clean.
        </p>
      ) : (
        <ul className="finding-list">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </ul>
      )}
    </section>
  );
}
