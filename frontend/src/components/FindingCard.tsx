import type { ReviewFinding } from "../types/review";
import { PERSONA_LABELS, SEVERITY_LABELS } from "../lib/reviewLabels";

interface FindingCardProps {
  finding: ReviewFinding;
}

function hunkLocation(finding: ReviewFinding): string | null {
  const ref = finding.hunkReference;
  if (!ref) {
    return null;
  }
  const parts: string[] = [];
  if (ref.header) {
    parts.push(ref.header);
  }
  if (ref.line != null) {
    parts.push(`line ${ref.line}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function FindingCard({ finding }: FindingCardProps) {
  const location = hunkLocation(finding);
  const confidencePct =
    finding.confidence != null
      ? Math.round(finding.confidence * 100)
      : null;

  return (
    <li className={`finding finding--${finding.severity}`}>
      <div className="finding__head">
        <span className={`pill pill--sev-${finding.severity}`}>
          {SEVERITY_LABELS[finding.severity]}
        </span>
        <span className="pill pill--persona">
          {PERSONA_LABELS[finding.reviewer] ?? finding.reviewer}
        </span>
        {confidencePct != null && (
          <span className="pill pill--confidence" title="Model confidence">
            {confidencePct}% confidence
          </span>
        )}
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

      {location && <p className="finding__loc">{location}</p>}
    </li>
  );
}
