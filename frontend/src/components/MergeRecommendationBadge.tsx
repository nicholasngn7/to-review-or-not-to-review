import type { MergeRecommendation } from "../types/review";
import { RECOMMENDATION_LABELS } from "../lib/reviewLabels";

interface MergeRecommendationBadgeProps {
  recommendation: MergeRecommendation;
}

export function MergeRecommendationBadge({
  recommendation,
}: MergeRecommendationBadgeProps) {
  return (
    <span className={`badge badge--rec-${recommendation}`}>
      {RECOMMENDATION_LABELS[recommendation]}
    </span>
  );
}
