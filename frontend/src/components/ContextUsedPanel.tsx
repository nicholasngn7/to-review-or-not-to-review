import type { RetrievalResult } from "../types/review";
import {
  RETRIEVAL_PROVENANCE_NOTE,
  formatLineRange,
  formatScore,
} from "../lib/reviewLabels";

interface ContextUsedPanelProps {
  contextUsed?: RetrievalResult[] | null;
}

/** Build a compact "path · heading · lines" location label for a result. */
function resultLocation(result: RetrievalResult): string | null {
  const parts: string[] = [];
  if (result.sourcePath) {
    parts.push(result.sourcePath);
  }
  if (result.heading) {
    parts.push(result.heading);
  }
  const range = formatLineRange(result.startLine, result.endLine);
  if (range) {
    parts.push(range);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

/**
 * Read-only, collapsible panel listing the local context retrieved for grounding.
 *
 * Hidden entirely when there is no context. Purely provenance: the retrieved
 * snippets do not change findings, severity, or the merge recommendation.
 */
export function ContextUsedPanel({ contextUsed }: ContextUsedPanelProps) {
  if (!contextUsed || contextUsed.length === 0) {
    return null;
  }

  return (
    <details className="context-used" aria-label="Retrieved local context">
      <summary className="context-used__summary">
        <span className="results__section-title">Retrieved local context</span>
        <span className="threads-panel__count">{contextUsed.length}</span>
      </summary>

      <p className="context-used__note">{RETRIEVAL_PROVENANCE_NOTE}</p>

      <ul className="context-used__list">
        {contextUsed.map((result) => {
          const location = resultLocation(result);
          return (
            <li className="context-result" key={result.chunkId}>
              <div className="context-result__head">
                {location ? (
                  <span className="context-result__loc">{location}</span>
                ) : (
                  <span className="context-result__loc context-result__loc--muted">
                    Local context
                  </span>
                )}
                <span
                  className="context-result__score"
                  title="Lexical similarity score"
                >
                  score {formatScore(result.score)}
                </span>
              </div>
              <p className="context-result__snippet">{result.snippet}</p>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
