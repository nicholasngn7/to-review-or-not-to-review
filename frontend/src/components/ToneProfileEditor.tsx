import { useId } from "react";

import type {
  ToneProfile,
  ToneStrictness,
  ToneStyle,
  ToneVerbosity,
} from "../types/review";
import {
  TONE_STRICTNESS_LABELS,
  TONE_STRICTNESS_ORDER,
  TONE_STYLE_BLURBS,
  TONE_STYLE_LABELS,
  TONE_STYLE_ORDER,
  TONE_VERBOSITY_LABELS,
  TONE_VERBOSITY_ORDER,
} from "../lib/reviewLabels";

interface ToneProfileEditorProps {
  value: ToneProfile;
  onChange: (next: ToneProfile) => void;
  disabled?: boolean;
  /** Hide the custom instructions textarea (e.g. for compact per-persona rows). */
  showCustomInstructions?: boolean;
}

export function ToneProfileEditor({
  value,
  onChange,
  disabled,
  showCustomInstructions = true,
}: ToneProfileEditorProps) {
  const styleId = useId();
  const strictnessId = useId();
  const verbosityId = useId();
  const customId = useId();

  return (
    <div className="tone-editor">
      <div className="tone-editor__grid">
        <div className="tone-field">
          <label className="tone-field__label" htmlFor={styleId}>
            Tone
          </label>
          <select
            id={styleId}
            className="input tone-field__select"
            value={value.style}
            disabled={disabled}
            onChange={(e) =>
              onChange({ ...value, style: e.target.value as ToneStyle })
            }
          >
            {TONE_STYLE_ORDER.map((style) => (
              <option key={style} value={style}>
                {TONE_STYLE_LABELS[style]}
              </option>
            ))}
          </select>
          <p className="tone-field__hint">{TONE_STYLE_BLURBS[value.style]}</p>
        </div>

        <div className="tone-field">
          <label className="tone-field__label" htmlFor={strictnessId}>
            Strictness
          </label>
          <select
            id={strictnessId}
            className="input tone-field__select"
            value={value.strictness}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                ...value,
                strictness: e.target.value as ToneStrictness,
              })
            }
          >
            {TONE_STRICTNESS_ORDER.map((level) => (
              <option key={level} value={level}>
                {TONE_STRICTNESS_LABELS[level]}
              </option>
            ))}
          </select>
        </div>

        <div className="tone-field">
          <label className="tone-field__label" htmlFor={verbosityId}>
            Verbosity
          </label>
          <select
            id={verbosityId}
            className="input tone-field__select"
            value={value.verbosity}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                ...value,
                verbosity: e.target.value as ToneVerbosity,
              })
            }
          >
            {TONE_VERBOSITY_ORDER.map((level) => (
              <option key={level} value={level}>
                {TONE_VERBOSITY_LABELS[level]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {showCustomInstructions && (
        <div className="tone-field tone-field--custom">
          <label className="tone-field__label" htmlFor={customId}>
            Custom reviewer instructions{" "}
            <span className="field__optional">(optional)</span>
          </label>
          <textarea
            id={customId}
            className="input textarea textarea--short"
            placeholder="e.g. Reference our style guide and keep wording encouraging."
            value={value.customInstructions ?? ""}
            disabled={disabled}
            onChange={(e) =>
              onChange({ ...value, customInstructions: e.target.value })
            }
          />
        </div>
      )}
    </div>
  );
}
