import { useCallback, useId, useState } from "react";
import type { ChangeEvent } from "react";

import type {
  CommentThread,
  ReviewRequest,
  ReviewerPersona,
  ToneProfile,
} from "../types/review";
import { SAMPLE_DIFFS, type SampleDiff } from "../samples/sampleDiffs";
import {
  DEFAULT_TONE_PROFILE,
  isDefaultTone,
  toRequestTone,
} from "../lib/reviewLabels";
import { CommentThreadsInput } from "./CommentThreadsInput";
import {
  ContextSourcesInput,
  type ContextSourcesValue,
} from "./ContextSourcesInput";
import { ImportCommentsPanel } from "./ImportCommentsPanel";
import { DEFAULT_PERSONAS, PersonaSelector } from "./PersonaSelector";
import { ReviewerTonePanel } from "./ReviewerTonePanel";

interface DiffInputPanelProps {
  isLoading: boolean;
  onRun: (request: ReviewRequest) => void;
}

export function DiffInputPanel({ isLoading, onRun }: DiffInputPanelProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [diffText, setDiffText] = useState("");
  const [personas, setPersonas] =
    useState<ReviewerPersona[]>(DEFAULT_PERSONAS);
  const [fileName, setFileName] = useState<string | null>(null);
  const [globalTone, setGlobalTone] =
    useState<ToneProfile>(DEFAULT_TONE_PROFILE);
  const [toneOverrides, setToneOverrides] = useState<
    Partial<Record<ReviewerPersona, ToneProfile>>
  >({});
  const [commentThreads, setCommentThreads] = useState<CommentThread[]>([]);
  const [importedThreads, setImportedThreads] = useState<CommentThread[]>([]);
  const [contextSources, setContextSources] = useState<ContextSourcesValue>({
    sources: [],
    query: "",
  });

  const handleCommentThreadsChange = useCallback((threads: CommentThread[]) => {
    setCommentThreads(threads);
  }, []);

  const handleContextSourcesChange = useCallback(
    (value: ContextSourcesValue) => {
      setContextSources(value);
    },
    [],
  );

  const handleLoadImported = useCallback((threads: CommentThread[]) => {
    // Loading replaces the imported set (the on-submit dedupe is a backstop).
    setImportedThreads(threads);
  }, []);

  const removeImported = (id: string) => {
    setImportedThreads((prev) => prev.filter((t) => t.id !== id));
  };

  const clearImported = () => setImportedThreads([]);

  const titleId = useId();
  const descId = useId();
  const diffId = useId();

  const trimmedDiff = diffText.trim();
  const hasDiff = trimmedDiff.length > 0;
  const hasPersonas = personas.length > 0;
  const canRun = hasDiff && hasPersonas && !isLoading;

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const text = await file.text();
    setDiffText(text);
    setFileName(file.name);
    // Allow re-uploading the same file name later.
    event.target.value = "";
  };

  const loadSample = (sample: SampleDiff) => {
    setTitle(sample.title);
    setDescription(sample.description);
    setDiffText(sample.diffText);
    setPersonas(sample.recommendedPersonas);
    setFileName(null);
  };

  const toggleOverride = (persona: ReviewerPersona, enabled: boolean) => {
    setToneOverrides((prev) => {
      const next = { ...prev };
      if (enabled) {
        // Seed a new override from the current global voice as a starting point.
        next[persona] = { ...globalTone };
      } else {
        delete next[persona];
      }
      return next;
    });
  };

  const updateOverride = (persona: ReviewerPersona, tone: ToneProfile) => {
    setToneOverrides((prev) => ({ ...prev, [persona]: tone }));
  };

  const handleSubmit = () => {
    if (!canRun) {
      return;
    }
    const request: ReviewRequest = {
      diffText: trimmedDiff,
      selectedPersonas: personas,
      title: title.trim() || undefined,
      description: description.trim() || undefined,
    };

    // Only send a global tone when it differs from the default voice, so an
    // untouched form reproduces the original payload exactly.
    if (!isDefaultTone(globalTone)) {
      request.toneProfile = toRequestTone(globalTone);
    }

    // Include overrides only for personas that are still selected.
    const personaToneProfiles: Partial<Record<ReviewerPersona, ToneProfile>> =
      {};
    for (const persona of personas) {
      const override = toneOverrides[persona];
      if (override) {
        personaToneProfiles[persona] = toRequestTone(override);
      }
    }
    if (Object.keys(personaToneProfiles).length > 0) {
      request.personaToneProfiles = personaToneProfiles;
    }

    // Merge imported (loaded from the local import demo) and manual threads into a
    // single list, de-duped by id. Imported threads come first.
    const merged: CommentThread[] = [];
    const seenIds = new Set<string>();
    for (const thread of [...importedThreads, ...commentThreads]) {
      if (seenIds.has(thread.id)) {
        continue;
      }
      seenIds.add(thread.id);
      merged.push(thread);
    }
    if (merged.length > 0) {
      request.commentThreads = merged;
    }

    // Opt-in local retrieval grounding. Only attach knowledge sources (and an
    // optional query) when the user actually entered local source paths, so an
    // untouched form sends exactly the original payload.
    if (contextSources.sources.length > 0) {
      request.knowledgeSources = contextSources.sources;
      if (contextSources.query) {
        request.retrieval = { query: contextSources.query };
      }
    }

    onRun(request);
  };

  return (
    <section className="panel">
      <h2 className="panel__title">Merge request</h2>

      <div className="demo-bar">
        <span className="demo-bar__label">
          Load a demo diff
          <span className="demo-bar__tag">sample data</span>
        </span>
        <div className="demo-bar__buttons">
          {SAMPLE_DIFFS.map((sample) => (
            <button
              key={sample.id}
              type="button"
              className="chip"
              onClick={() => loadSample(sample)}
              disabled={isLoading}
              title={sample.description}
            >
              {sample.label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label className="field__label" htmlFor={titleId}>
          Title
        </label>
        <input
          id={titleId}
          className="input"
          type="text"
          placeholder="e.g. Add rate limiting to the login endpoint"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isLoading}
        />
      </div>

      <div className="field">
        <label className="field__label" htmlFor={descId}>
          Description <span className="field__optional">(optional)</span>
        </label>
        <textarea
          id={descId}
          className="input textarea textarea--short"
          placeholder="What is this change about?"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={isLoading}
        />
      </div>

      <div className="field">
        <div className="field__header">
          <label className="field__label" htmlFor={diffId}>
            Diff
          </label>
          <label className="file-upload">
            <input
              type="file"
              accept=".diff,.patch"
              onChange={handleFile}
              disabled={isLoading}
            />
            <span className="file-upload__button">Upload .diff / .patch</span>
          </label>
        </div>
        <textarea
          id={diffId}
          className="input textarea textarea--code"
          placeholder={"Paste a unified diff here, e.g.\ndiff --git a/app.py b/app.py\n@@ -1,3 +1,4 @@"}
          value={diffText}
          onChange={(e) => {
            setDiffText(e.target.value);
            if (fileName) {
              setFileName(null);
            }
          }}
          disabled={isLoading}
          spellCheck={false}
        />
        {fileName && (
          <p className="field__hint">Loaded from {fileName}</p>
        )}
      </div>

      <PersonaSelector
        selected={personas}
        onChange={setPersonas}
        disabled={isLoading}
      />

      <ReviewerTonePanel
        globalTone={globalTone}
        onGlobalToneChange={setGlobalTone}
        selectedPersonas={personas}
        overrides={toneOverrides}
        onToggleOverride={toggleOverride}
        onOverrideChange={updateOverride}
        disabled={isLoading}
      />

      <CommentThreadsInput
        onChange={handleCommentThreadsChange}
        disabled={isLoading}
      />

      <ContextSourcesInput
        onChange={handleContextSourcesChange}
        disabled={isLoading}
      />

      <ImportCommentsPanel
        onLoadThreads={handleLoadImported}
        disabled={isLoading}
      />

      {importedThreads.length > 0 && (
        <div
          className="imported-group"
          role="group"
          aria-label="Imported comments"
        >
          <div className="imported-group__head">
            <span className="imported-group__title">
              Imported comments
              <span className="threads-panel__count">
                {importedThreads.length}
              </span>
            </span>
            <button
              type="button"
              className="link-button"
              onClick={clearImported}
              disabled={isLoading}
            >
              Clear imported
            </button>
          </div>
          <p className="field__hint">
            Loaded from the local import demo (read-only). Included alongside any
            manual threads when you run the review.
          </p>
          <ul className="imported-list">
            {importedThreads.map((thread) => {
              const loc: string[] = [];
              if (thread.filePath) {
                loc.push(thread.filePath);
              }
              if (thread.line != null) {
                loc.push(`line ${thread.line}`);
              }
              return (
                <li className="imported-item" key={thread.id}>
                  <div className="imported-item__info">
                    <code className="import-preview__id">{thread.id}</code>
                    <span className="import-preview__meta">
                      {thread.comments.length} comment
                      {thread.comments.length === 1 ? "" : "s"}
                      {loc.length > 0 ? ` · ${loc.join(" · ")}` : ""}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => removeImported(thread.id)}
                    disabled={isLoading}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="run-row">
        <button
          type="button"
          className="button button--primary"
          onClick={handleSubmit}
          disabled={!canRun}
        >
          {isLoading ? "Running review..." : "Run Review"}
        </button>
        {!hasDiff && (
          <span className="run-row__note">Paste or upload a diff to begin.</span>
        )}
        {hasDiff && !hasPersonas && (
          <span className="run-row__note run-row__note--warn">
            Select at least one reviewer persona.
          </span>
        )}
      </div>
    </section>
  );
}
