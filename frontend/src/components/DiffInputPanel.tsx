import { useId, useState } from "react";
import type { ChangeEvent } from "react";

import type { ReviewRequest, ReviewerPersona } from "../types/review";
import { SAMPLE_DIFFS, type SampleDiff } from "../samples/sampleDiffs";
import { DEFAULT_PERSONAS, PersonaSelector } from "./PersonaSelector";

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
