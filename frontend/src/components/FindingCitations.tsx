import type { RetrievedCitation } from "../types/review";
import { formatLineRange, formatScore } from "../lib/reviewLabels";

interface FindingCitationsProps {
  citations?: RetrievedCitation[] | null;
}

/** Build a compact "path · heading · lines" location label for a citation. */
function citationLocation(citation: RetrievedCitation): string | null {
  const parts: string[] = [];
  if (citation.sourcePath) {
    parts.push(citation.sourcePath);
  }
  if (citation.heading) {
    parts.push(citation.heading);
  }
  const range = formatLineRange(citation.startLine, citation.endLine);
  if (range) {
    parts.push(range);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

/**
 * Secondary, expandable "Cited context" detail for a single finding.
 *
 * Hidden when there are no citations. Provenance-only: citations do not imply the
 * retrieved context changed the finding's severity or recommendation.
 */
export function FindingCitations({ citations }: FindingCitationsProps) {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <details className="finding-citations">
      <summary className="finding-citations__summary">
        Cited context
        <span className="finding-citations__count">{citations.length}</span>
      </summary>
      <p className="finding-citations__note">
        Local lexical context (provenance only) — did not change this finding’s
        severity or recommendation.
      </p>
      <ul className="finding-citations__list">
        {citations.map((citation) => {
          const location = citationLocation(citation);
          return (
            <li className="finding-citation" key={citation.chunkId}>
              <div className="finding-citation__head">
                {location && (
                  <span className="finding-citation__loc">{location}</span>
                )}
                <span className="finding-citation__score">
                  score {formatScore(citation.score)}
                </span>
              </div>
              <p className="finding-citation__snippet">{citation.snippet}</p>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
