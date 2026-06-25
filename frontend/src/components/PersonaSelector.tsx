import type { ReviewerPersona } from "../types/review";
import {
  PERSONA_BLURBS,
  PERSONA_LABELS,
  PERSONA_ORDER,
} from "../lib/reviewLabels";

export const DEFAULT_PERSONAS: ReviewerPersona[] = [
  "architect",
  "qa",
  "security",
  "backend",
  "sre",
];

interface PersonaSelectorProps {
  selected: ReviewerPersona[];
  onChange: (next: ReviewerPersona[]) => void;
  disabled?: boolean;
}

export function PersonaSelector({
  selected,
  onChange,
  disabled,
}: PersonaSelectorProps) {
  const toggle = (persona: ReviewerPersona) => {
    if (selected.includes(persona)) {
      onChange(selected.filter((p) => p !== persona));
    } else {
      onChange([...selected, persona]);
    }
  };

  return (
    <fieldset className="persona-selector" disabled={disabled}>
      <legend className="field__label">Reviewer personas</legend>
      <div className="persona-grid">
        {PERSONA_ORDER.map((persona) => {
          const checked = selected.includes(persona);
          return (
            <label
              key={persona}
              className={`persona-card${checked ? " persona-card--on" : ""}`}
            >
              <input
                type="checkbox"
                className="persona-card__checkbox"
                checked={checked}
                onChange={() => toggle(persona)}
              />
              <span className="persona-card__label">
                {PERSONA_LABELS[persona]}
              </span>
              <span className="persona-card__blurb">
                {PERSONA_BLURBS[persona]}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
