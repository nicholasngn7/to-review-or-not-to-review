import { useId, useState } from "react";

import type { CommentThread } from "../types/review";
import type {
  GitProviderType,
  ImportCommentsResponse,
  ImportSource,
} from "../types/gitImport";
import { ImportApiError, importComments } from "../api/importComments";
import { IMPORT_SAMPLES, type ImportSample } from "../fixtures/importSamples";

interface ImportCommentsPanelProps {
  onLoadThreads: (threads: CommentThread[]) => void;
  disabled?: boolean;
}

const PROVIDER_OPTIONS: { value: GitProviderType; label: string }[] = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
];

const SOURCE_OPTIONS: Record<
  GitProviderType,
  { value: ImportSource; label: string }[]
> = {
  github: [
    { value: "github_review_comments", label: "PR review comments" },
    { value: "github_issue_comments", label: "PR issue comments" },
  ],
  gitlab: [{ value: "gitlab_discussions", label: "MR discussions" }],
};

function threadLocation(thread: CommentThread): string | null {
  const parts: string[] = [];
  if (thread.filePath) {
    parts.push(thread.filePath);
  }
  if (thread.line != null) {
    parts.push(`line ${thread.line}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function ImportCommentsPanel({
  onLoadThreads,
  disabled,
}: ImportCommentsPanelProps) {
  const [provider, setProvider] = useState<GitProviderType>("github");
  const [source, setSource] = useState<ImportSource>("github_review_comments");
  const [rawText, setRawText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [result, setResult] = useState<ImportCommentsResponse | null>(null);

  const providerId = useId();
  const sourceId = useId();
  const jsonId = useId();

  const handleProviderChange = (next: GitProviderType) => {
    setProvider(next);
    // Reset the source to the first valid option for the new provider.
    setSource(SOURCE_OPTIONS[next][0].value);
    setResult(null);
    setApiError(null);
  };

  const handleLoadSample = (sample: ImportSample) => {
    // Only populate the form — the user still clicks "Normalize comments". This
    // keeps it explicit that we normalize supplied JSON rather than fetch anything.
    setProvider(sample.provider);
    setSource(sample.source);
    setRawText(`${JSON.stringify(sample.payload, null, 2)}\n`);
    setJsonError(null);
    setApiError(null);
    setResult(null);
  };

  const handleNormalize = async () => {
    setJsonError(null);
    setApiError(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(rawText);
    } catch {
      setResult(null);
      setJsonError(
        "That doesn't look like valid JSON. Paste a provider-shaped array or object.",
      );
      return;
    }

    setIsImporting(true);
    try {
      const response = await importComments({
        provider,
        source,
        rawPayload: parsed,
      });
      setResult(response);
    } catch (error) {
      setResult(null);
      const message =
        error instanceof ImportApiError
          ? error.message
          : "Something went wrong while normalizing the payload.";
      setApiError(message);
    } finally {
      setIsImporting(false);
    }
  };

  const handleLoad = () => {
    if (!result || result.threads.length === 0) {
      return;
    }
    onLoadThreads(result.threads.map((imported) => imported.thread));
  };

  const threadCount = result?.threads.length ?? 0;
  const hasThreads = threadCount > 0;

  return (
    <details className="threads-panel import-panel">
      <summary className="threads-panel__summary">
        <span className="threads-panel__title">
          Import comments{" "}
          <span className="field__optional">(local demo)</span>
        </span>
      </summary>

      <p className="threads-panel__help">
        Paste provider-shaped JSON. <strong>Nothing is fetched or posted.</strong>{" "}
        No tokens, OAuth, or GitHub/GitLab API calls are used — this is a local
        normalization demo, not live GitHub/GitLab integration.
      </p>

      <div className="import-samples" role="group" aria-label="Load sample payload">
        <span className="import-samples__label">Load sample payload</span>
        <div className="import-samples__buttons">
          {IMPORT_SAMPLES.map((sample) => (
            <button
              type="button"
              key={sample.id}
              className="button button--secondary import-samples__button"
              title={sample.description}
              disabled={disabled || isImporting}
              onClick={() => handleLoadSample(sample)}
            >
              {sample.label}
            </button>
          ))}
        </div>
        <p className="field__hint">
          Fills the form with synthetic JSON. You still click “Normalize comments”.
        </p>
      </div>

      <div className="thread-card__row">
        <div className="thread-field">
          <label className="tone-field__label" htmlFor={providerId}>
            Provider
          </label>
          <select
            id={providerId}
            className="input"
            value={provider}
            disabled={disabled || isImporting}
            onChange={(e) =>
              handleProviderChange(e.target.value as GitProviderType)
            }
          >
            {PROVIDER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="thread-field">
          <label className="tone-field__label" htmlFor={sourceId}>
            Source
          </label>
          <select
            id={sourceId}
            className="input"
            value={source}
            disabled={disabled || isImporting}
            onChange={(e) => setSource(e.target.value as ImportSource)}
          >
            {SOURCE_OPTIONS[provider].map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="thread-field">
        <label className="tone-field__label" htmlFor={jsonId}>
          Provider JSON payload
        </label>
        <textarea
          id={jsonId}
          className="input textarea textarea--code"
          placeholder={'Paste a fixture-shaped array, e.g.\n[\n  { "id": 1, "body": "..." }\n]'}
          value={rawText}
          disabled={disabled || isImporting}
          spellCheck={false}
          onChange={(e) => setRawText(e.target.value)}
        />
      </div>

      <div className="import-panel__actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={handleNormalize}
          disabled={disabled || isImporting}
        >
          {isImporting ? "Normalizing..." : "Normalize comments"}
        </button>
      </div>

      {jsonError && (
        <p className="import-warning import-warning--error" role="alert">
          {jsonError}
        </p>
      )}
      {apiError && (
        <p className="import-warning import-warning--error" role="alert">
          {apiError}
        </p>
      )}

      {result && (
        <div className="import-result">
          <p className="import-result__count">
            {hasThreads
              ? `${threadCount} thread${threadCount === 1 ? "" : "s"} normalized.`
              : "No comment threads were produced from this payload."}
          </p>

          {result.warnings.length > 0 && (
            <ul className="import-result__warnings">
              {result.warnings.map((warning, index) => (
                <li className="import-warning" key={`${index}-${warning}`}>
                  {warning}
                </li>
              ))}
            </ul>
          )}

          {hasThreads && (
            <ul className="import-preview">
              {result.threads.map((imported) => {
                const { thread } = imported;
                const location = threadLocation(thread);
                return (
                  <li className="import-preview__item" key={thread.id}>
                    <div className="import-preview__head">
                      <code className="import-preview__id">{thread.id}</code>
                      <span className="import-preview__meta">
                        {thread.comments.length} comment
                        {thread.comments.length === 1 ? "" : "s"}
                        {location ? ` · ${location}` : ""}
                      </span>
                    </div>
                    <p className="import-preview__snippet">
                      {thread.comments[0]?.body}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}

          <button
            type="button"
            className="button button--primary import-result__load"
            onClick={handleLoad}
            disabled={disabled || !hasThreads}
          >
            Load imported threads
          </button>
        </div>
      )}
    </details>
  );
}
