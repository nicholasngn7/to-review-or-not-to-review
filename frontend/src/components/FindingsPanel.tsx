import { useMemo, useState } from "react";

import type {
  FindingSeverity,
  PersonaReview,
  ReviewFinding,
} from "../types/review";
import {
  PERSONA_LABELS,
  PERSONA_ORDER,
  SEVERITY_LABELS,
  SEVERITY_ORDER,
} from "../lib/reviewLabels";
import { FindingCard } from "./FindingCard";
import {
  ReviewerTabs,
  type ReviewerFilter,
  type ReviewerTab,
} from "./ReviewerTabs";

type SeverityFilter = FindingSeverity | "all";

interface FindingsPanelProps {
  personaReviews: PersonaReview[];
  findings: ReviewFinding[];
}

export function FindingsPanel({ personaReviews, findings }: FindingsPanelProps) {
  const [reviewer, setReviewer] = useState<ReviewerFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");

  const orderedPersonas = useMemo(
    () => PERSONA_ORDER.filter((p) => personaReviews.some((pr) => pr.persona === p)),
    [personaReviews],
  );

  // Severity is applied first so the tab counts reflect the active severity.
  const severityFiltered = useMemo(
    () =>
      severity === "all"
        ? findings
        : findings.filter((f) => f.severity === severity),
    [findings, severity],
  );

  const visible = useMemo(
    () =>
      reviewer === "all"
        ? severityFiltered
        : severityFiltered.filter((f) => f.reviewer === reviewer),
    [severityFiltered, reviewer],
  );

  const tabs: ReviewerTab[] = useMemo(() => {
    const personaTabs = orderedPersonas.map((p) => ({
      key: p,
      label: PERSONA_LABELS[p],
      count: severityFiltered.filter((f) => f.reviewer === p).length,
    }));
    return [
      { key: "all", label: "All", count: severityFiltered.length },
      ...personaTabs,
    ];
  }, [orderedPersonas, severityFiltered]);

  const filtersActive = reviewer !== "all" || severity !== "all";

  const clearFilters = () => {
    setReviewer("all");
    setSeverity("all");
  };

  // Review-level empty state: nothing was found at all.
  if (findings.length === 0) {
    return (
      <div className="findings">
        <h3 className="results__section-title">Findings</h3>
        <div className="empty empty--positive">
          <span className="empty__icon" aria-hidden="true">
            ✓
          </span>
          <p className="empty__title">No findings found</p>
          <p className="empty__hint">
            The selected reviewers did not flag anything in this diff.
          </p>
        </div>
      </div>
    );
  }

  const severityChoices: SeverityFilter[] = ["all", ...SEVERITY_ORDER];

  return (
    <div className="findings">
      <div className="findings__bar">
        <h3 className="results__section-title">Findings ({findings.length})</h3>
        <div className="filters">
          <div
            className="filter-group"
            role="group"
            aria-label="Filter by severity"
          >
            {severityChoices.map((choice) => (
              <button
                key={choice}
                type="button"
                className={`chip${severity === choice ? " chip--active" : ""}`}
                onClick={() => setSeverity(choice)}
              >
                {choice === "all" ? "All severities" : SEVERITY_LABELS[choice]}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="link-button"
            onClick={clearFilters}
            disabled={!filtersActive}
          >
            Clear filters
          </button>
        </div>
      </div>

      <ReviewerTabs tabs={tabs} active={reviewer} onSelect={setReviewer} />

      {visible.length > 0 ? (
        <ul className="finding-list">
          {visible.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </ul>
      ) : severity === "all" && reviewer !== "all" ? (
        <div className="empty empty--positive">
          <span className="empty__icon" aria-hidden="true">
            ✓
          </span>
          <p className="empty__title">
            No findings from the {PERSONA_LABELS[reviewer]} reviewer
          </p>
          <p className="empty__hint">Looks clean from this perspective.</p>
        </div>
      ) : (
        <div className="empty">
          <p className="empty__title">No findings match the current filters.</p>
          <button type="button" className="link-button" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
