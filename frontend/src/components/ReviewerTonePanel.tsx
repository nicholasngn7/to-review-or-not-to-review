import type { ReviewerPersona, ToneProfile } from "../types/review";
import {
  isDefaultTone,
  PERSONA_LABELS,
  PERSONA_ORDER,
} from "../lib/reviewLabels";
import { ToneProfileEditor } from "./ToneProfileEditor";

interface ReviewerTonePanelProps {
  globalTone: ToneProfile;
  onGlobalToneChange: (next: ToneProfile) => void;
  selectedPersonas: ReviewerPersona[];
  overrides: Partial<Record<ReviewerPersona, ToneProfile>>;
  onToggleOverride: (persona: ReviewerPersona, enabled: boolean) => void;
  onOverrideChange: (persona: ReviewerPersona, next: ToneProfile) => void;
  disabled?: boolean;
}

export function ReviewerTonePanel({
  globalTone,
  onGlobalToneChange,
  selectedPersonas,
  overrides,
  onToggleOverride,
  onOverrideChange,
  disabled,
}: ReviewerTonePanelProps) {
  // Only offer overrides for personas that are currently selected, in canonical
  // order. Overrides for deselected personas are ignored when the request is built.
  const overridablePersonas = PERSONA_ORDER.filter((p) =>
    selectedPersonas.includes(p),
  );

  const customized = !isDefaultTone(globalTone);

  return (
    <details className="tone-panel">
      <summary className="tone-panel__summary">
        <span className="tone-panel__title">Reviewer voice</span>
        <span
          className={`tone-panel__state${
            customized ? " tone-panel__state--on" : ""
          }`}
        >
          {customized ? "Customized" : "Default"}
        </span>
      </summary>

      <p className="tone-panel__help">
        Tone changes the <strong>wording and framing</strong> of feedback only. It
        does not change risk scoring, severities, or which issues are detected.
        Per-reviewer overrides win over the global voice.
      </p>

      <fieldset className="tone-panel__group" disabled={disabled}>
        <legend className="field__label">Global voice</legend>
        <ToneProfileEditor value={globalTone} onChange={onGlobalToneChange} />
      </fieldset>

      <fieldset className="tone-panel__group" disabled={disabled}>
        <legend className="field__label">
          Per-reviewer overrides{" "}
          <span className="field__optional">(optional)</span>
        </legend>

        {overridablePersonas.length === 0 ? (
          <p className="field__hint">
            Select at least one reviewer persona to configure overrides.
          </p>
        ) : (
          <div className="tone-overrides">
            {overridablePersonas.map((persona) => {
              const override = overrides[persona];
              const enabled = Boolean(override);
              return (
                <div className="tone-override" key={persona}>
                  <label className="tone-override__toggle">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) =>
                        onToggleOverride(persona, e.target.checked)
                      }
                    />
                    <span className="tone-override__name">
                      {PERSONA_LABELS[persona]}
                    </span>
                  </label>
                  {enabled && override && (
                    <ToneProfileEditor
                      value={override}
                      onChange={(next) => onOverrideChange(persona, next)}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </fieldset>
    </details>
  );
}
