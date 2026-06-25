import { useEffect, useRef, useState } from "react";

import type { CommentThread, CommentThreadStatus } from "../types/review";

interface CommentThreadsInputProps {
  onChange: (threads: CommentThread[]) => void;
  disabled?: boolean;
}

interface ThreadDraft {
  key: string;
  id: string;
  filePath: string;
  line: string;
  status: CommentThreadStatus;
  author: string;
  body: string;
}

const STATUS_OPTIONS: { value: CommentThreadStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
  { value: "unknown", label: "Unknown" },
];

function emptyDraft(key: string): ThreadDraft {
  return {
    key,
    id: "",
    filePath: "",
    line: "",
    status: "open",
    author: "",
    body: "",
  };
}

/** Build the wire `CommentThread[]` from drafts, dropping rows with no body. */
function buildThreads(drafts: ThreadDraft[]): CommentThread[] {
  const threads: CommentThread[] = [];
  drafts.forEach((draft, index) => {
    const body = draft.body.trim();
    if (!body) {
      return; // Empty comment threads are never sent.
    }
    const threadId = draft.id.trim() || `thread-${index + 1}`;
    const author = draft.author.trim();
    const filePath = draft.filePath.trim();
    const lineNum = Number.parseInt(draft.line.trim(), 10);

    const thread: CommentThread = {
      id: threadId,
      status: draft.status,
      comments: [
        {
          id: `${threadId}-c1`,
          body,
          ...(author ? { author } : {}),
        },
      ],
    };
    if (filePath) {
      thread.filePath = filePath;
    }
    if (Number.isFinite(lineNum) && draft.line.trim() !== "") {
      thread.line = lineNum;
    }
    threads.push(thread);
  });
  return threads;
}

export function CommentThreadsInput({
  onChange,
  disabled,
}: CommentThreadsInputProps) {
  const counter = useRef(0);
  const [drafts, setDrafts] = useState<ThreadDraft[]>([]);

  useEffect(() => {
    onChange(buildThreads(drafts));
  }, [drafts, onChange]);

  const addThread = () => {
    counter.current += 1;
    setDrafts((prev) => [...prev, emptyDraft(`draft-${counter.current}`)]);
  };

  const removeThread = (key: string) => {
    setDrafts((prev) => prev.filter((d) => d.key !== key));
  };

  const update = (key: string, patch: Partial<ThreadDraft>) => {
    setDrafts((prev) =>
      prev.map((d) => (d.key === key ? { ...d, ...patch } : d)),
    );
  };

  return (
    <details className="threads-panel">
      <summary className="threads-panel__summary">
        <span className="threads-panel__title">
          Existing comment threads{" "}
          <span className="field__optional">(optional)</span>
        </span>
        {drafts.length > 0 && (
          <span className="threads-panel__count">{drafts.length}</span>
        )}
      </summary>

      <p className="threads-panel__help">
        Paste existing MR/PR discussion comments here as structured input. They are
        captured for <strong>future suggested replies</strong> (a later, copy-only
        feature) — nothing is posted back to GitHub/GitLab, and no replies are
        generated yet. Comment threads are optional and not required to run a review.
      </p>

      {drafts.length === 0 ? (
        <p className="field__hint">No comment threads added.</p>
      ) : (
        <div className="threads-list">
          {drafts.map((draft) => (
            <div className="thread-card" key={draft.key}>
              <div className="thread-card__row">
                <div className="thread-field">
                  <label
                    className="tone-field__label"
                    htmlFor={`${draft.key}-id`}
                  >
                    Thread ID
                  </label>
                  <input
                    id={`${draft.key}-id`}
                    className="input"
                    placeholder="auto if blank"
                    value={draft.id}
                    disabled={disabled}
                    onChange={(e) => update(draft.key, { id: e.target.value })}
                  />
                </div>
                <div className="thread-field">
                  <label
                    className="tone-field__label"
                    htmlFor={`${draft.key}-status`}
                  >
                    Status
                  </label>
                  <select
                    id={`${draft.key}-status`}
                    className="input"
                    value={draft.status}
                    disabled={disabled}
                    onChange={(e) =>
                      update(draft.key, {
                        status: e.target.value as CommentThreadStatus,
                      })
                    }
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="thread-card__row">
                <div className="thread-field">
                  <label
                    className="tone-field__label"
                    htmlFor={`${draft.key}-file`}
                  >
                    File path <span className="field__optional">(optional)</span>
                  </label>
                  <input
                    id={`${draft.key}-file`}
                    className="input"
                    placeholder="e.g. app/auth.py"
                    value={draft.filePath}
                    disabled={disabled}
                    onChange={(e) =>
                      update(draft.key, { filePath: e.target.value })
                    }
                  />
                </div>
                <div className="thread-field thread-field--line">
                  <label
                    className="tone-field__label"
                    htmlFor={`${draft.key}-line`}
                  >
                    Line <span className="field__optional">(optional)</span>
                  </label>
                  <input
                    id={`${draft.key}-line`}
                    className="input"
                    type="number"
                    inputMode="numeric"
                    placeholder="e.g. 5"
                    value={draft.line}
                    disabled={disabled}
                    onChange={(e) => update(draft.key, { line: e.target.value })}
                  />
                </div>
                <div className="thread-field">
                  <label
                    className="tone-field__label"
                    htmlFor={`${draft.key}-author`}
                  >
                    Author <span className="field__optional">(optional)</span>
                  </label>
                  <input
                    id={`${draft.key}-author`}
                    className="input"
                    placeholder="e.g. Reviewer"
                    value={draft.author}
                    disabled={disabled}
                    onChange={(e) =>
                      update(draft.key, { author: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="thread-field">
                <label
                  className="tone-field__label"
                  htmlFor={`${draft.key}-body`}
                >
                  Comment
                </label>
                <textarea
                  id={`${draft.key}-body`}
                  className="input textarea textarea--short"
                  placeholder="e.g. Can we avoid swallowing this exception?"
                  value={draft.body}
                  disabled={disabled}
                  onChange={(e) => update(draft.key, { body: e.target.value })}
                />
              </div>

              <div className="thread-card__actions">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => removeThread(draft.key)}
                  disabled={disabled}
                >
                  Remove thread
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        className="button button--secondary threads-panel__add"
        onClick={addThread}
        disabled={disabled}
      >
        + Add comment thread
      </button>
    </details>
  );
}
