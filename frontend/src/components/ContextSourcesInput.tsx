import { useEffect, useId, useState } from "react";

export interface ContextSourcesValue {
  /** One local source path per non-empty line. */
  sources: string[];
  /** Optional local context query; empty means "let the backend derive one". */
  query: string;
}

interface ContextSourcesInputProps {
  onChange: (value: ContextSourcesValue) => void;
  disabled?: boolean;
}

/** Parse a textarea into trimmed, non-empty source paths (order preserved). */
export function parseSourceLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/**
 * Optional, collapsible input for opt-in local retrieval grounding.
 *
 * Retrieval is local, deterministic, and lexical (provenance-only). This input only
 * collects local doc paths and an optional query — it never fetches URLs, never asks
 * for tokens, and does not imply GitHub/GitLab access.
 */
export function ContextSourcesInput({
  onChange,
  disabled,
}: ContextSourcesInputProps) {
  const [sourcesText, setSourcesText] = useState("");
  const [query, setQuery] = useState("");

  const sourcesId = useId();
  const queryId = useId();

  useEffect(() => {
    onChange({ sources: parseSourceLines(sourcesText), query: query.trim() });
  }, [sourcesText, query, onChange]);

  const sourceCount = parseSourceLines(sourcesText).length;

  return (
    <details className="context-input">
      <summary className="context-input__summary">
        <span className="context-input__title">
          Optional local context sources{" "}
          <span className="field__optional">(optional)</span>
        </span>
        {sourceCount > 0 && (
          <span className="threads-panel__count">{sourceCount}</span>
        )}
      </summary>

      <p className="context-input__help">
        Ground the review on local project docs. Retrieved local context is{" "}
        <strong>lexical and provenance-only</strong> — it is not semantic search and
        does not change findings, severity, or the merge recommendation. Files are read
        locally from an allow-list; no URLs are fetched and no tokens are used.
      </p>

      <div className="field">
        <label className="field__label" htmlFor={sourcesId}>
          Source paths <span className="field__optional">(one per line)</span>
        </label>
        <textarea
          id={sourcesId}
          className="input textarea textarea--short"
          placeholder={"README.md\ndocs/project-case-study.md\ndocs/decisions.md"}
          value={sourcesText}
          disabled={disabled}
          spellCheck={false}
          onChange={(e) => setSourcesText(e.target.value)}
        />
        <p className="field__hint">
          Examples: <code>README.md</code>, <code>docs/project-case-study.md</code>,{" "}
          <code>docs/decisions.md</code>.
        </p>
      </div>

      <div className="field">
        <label className="field__label" htmlFor={queryId}>
          Context query{" "}
          <span className="field__optional">(optional, local/lexical)</span>
        </label>
        <input
          id={queryId}
          className="input"
          type="text"
          placeholder="Leave blank to derive from the title, description, and diff"
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
    </details>
  );
}
