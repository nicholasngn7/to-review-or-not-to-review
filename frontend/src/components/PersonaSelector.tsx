import type { ReviewerPersona } from "../types/review";

interface PersonaOption {
  value: ReviewerPersona;
  label: string;
  blurb: string;
}

export const PERSONA_OPTIONS: PersonaOption[] = [
  { value: "architect", label: "Architect", blurb: "Structure & boundaries" },
  { value: "qa", label: "QA / Test", blurb: "Coverage & regressions" },
  { value: "security", label: "Security", blurb: "Secrets & unsafe patterns" },
  { value: "frontend", label: "Frontend", blurb: "UI, state & a11y" },
  { value: "backend", label: "Backend", blurb: "APIs & validation" },
  { value: "sre", label: "SRE / On-call", blurb: "Observability & reliability" },
  { value: "product", label: "Product", blurb: "Clarity & maintainability" },
];

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
        {PERSONA_OPTIONS.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <label
              key={option.value}
              className={`persona-card${checked ? " persona-card--on" : ""}`}
            >
              <input
                type="checkbox"
                className="persona-card__checkbox"
                checked={checked}
                onChange={() => toggle(option.value)}
              />
              <span className="persona-card__label">{option.label}</span>
              <span className="persona-card__blurb">{option.blurb}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
