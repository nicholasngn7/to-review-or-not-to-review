import type { RiskLevel } from "../types/review";
import { RISK_LABELS } from "../lib/reviewLabels";

interface RiskBadgeProps {
  risk: RiskLevel;
}

export function RiskBadge({ risk }: RiskBadgeProps) {
  return (
    <span className={`badge badge--risk-${risk}`}>
      Risk: {RISK_LABELS[risk]}
    </span>
  );
}
