import type { ReviewerPersona } from "../types/review";

export type ReviewerFilter = ReviewerPersona | "all";

export interface ReviewerTab {
  key: ReviewerFilter;
  label: string;
  count: number;
}

interface ReviewerTabsProps {
  tabs: ReviewerTab[];
  active: ReviewerFilter;
  onSelect: (key: ReviewerFilter) => void;
}

export function ReviewerTabs({ tabs, active, onSelect }: ReviewerTabsProps) {
  return (
    <div className="tabs" role="tablist" aria-label="Reviewer">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={active === tab.key}
          className={`tab${active === tab.key ? " tab--active" : ""}`}
          onClick={() => onSelect(tab.key)}
        >
          {tab.label}
          <span className="tab__count">{tab.count}</span>
        </button>
      ))}
    </div>
  );
}
