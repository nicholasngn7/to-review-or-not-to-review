/**
 * Builds a clean Markdown report from a review result.
 *
 * The output is meant to be pasted into a GitLab MR / GitHub PR comment or saved
 * as a local `.md` artifact. It always reflects the full review (every persona
 * and finding), independent of any UI filters.
 */

import type {
  ReviewFinding,
  ReviewResponse,
  SuggestedReply,
} from "../types/review";
import {
  PERSONA_LABELS,
  PERSONA_ORDER,
  RECOMMENDATION_LABELS,
  RISK_LABELS,
  SEVERITY_LABELS,
} from "./reviewLabels";

const FILENAME_BASE = "mr-review-council-report";

/** A safe download filename, optionally including a slug of the MR title. */
export function buildReportFilename(title?: string | null): string {
  const slug = (title ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "");
  return slug ? `${FILENAME_BASE}-${slug}.md` : `${FILENAME_BASE}.md`;
}

function hunkLocation(finding: ReviewFinding): string | null {
  const ref = finding.hunkReference;
  if (!ref) {
    return null;
  }
  const parts: string[] = [];
  if (ref.header) {
    parts.push(ref.header);
  }
  if (ref.line != null) {
    parts.push(`line ${ref.line}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

function findingBlock(finding: ReviewFinding): string[] {
  const lines: string[] = [];
  lines.push(`#### [${SEVERITY_LABELS[finding.severity]}] ${finding.title}`);
  lines.push("");

  const meta: string[] = [];
  if (finding.filePath) {
    meta.push(`**File:** \`${finding.filePath}\``);
  }
  const location = hunkLocation(finding);
  if (location) {
    meta.push(`**Location:** ${location}`);
  }
  if (finding.confidence != null) {
    meta.push(`**Confidence:** ${Math.round(finding.confidence * 100)}%`);
  }
  if (meta.length > 0) {
    // Two trailing spaces force a hard line break in Markdown.
    lines.push(meta.join("  \n"));
    lines.push("");
  }

  lines.push(`**Explanation:** ${finding.explanation}`);
  lines.push("");
  lines.push(`**Recommendation:** ${finding.recommendation}`);
  lines.push("");
  return lines;
}

function suggestedRepliesSection(replies: SuggestedReply[]): string[] {
  const lines: string[] = [];
  lines.push("## Suggested replies");
  lines.push("");
  lines.push(
    "_Draft, copy-only replies to existing comment threads. Nothing is posted " +
      "anywhere; review and edit before sending._",
  );
  lines.push("");

  // Group by thread id, preserving first-seen order.
  const order: string[] = [];
  const byThread = new Map<string, SuggestedReply[]>();
  for (const reply of replies) {
    if (!byThread.has(reply.threadId)) {
      byThread.set(reply.threadId, []);
      order.push(reply.threadId);
    }
    byThread.get(reply.threadId)!.push(reply);
  }

  for (const threadId of order) {
    lines.push(`### Thread \`${threadId}\``);
    lines.push("");
    for (const reply of byThread.get(threadId)!) {
      lines.push(`#### ${PERSONA_LABELS[reply.reviewer]}`);
      lines.push("");

      const loc: string[] = [];
      if (reply.filePath) {
        loc.push(`\`${reply.filePath}\``);
      }
      if (reply.line != null) {
        loc.push(`line ${reply.line}`);
      }
      if (loc.length > 0) {
        lines.push(`**Location:** ${loc.join(" · ")}`);
        lines.push("");
      }

      lines.push(`> ${reply.suggestedReply}`);
      lines.push("");
      lines.push(`**Rationale:** ${reply.rationale}`);
      if (reply.confidence != null) {
        lines.push("");
        lines.push(`**Confidence:** ${Math.round(reply.confidence * 100)}%`);
      }
      lines.push("");
      lines.push("**Needs human review before sending.**");
      lines.push("");
    }
  }

  return lines;
}

/** Render a `ReviewResponse` as a Markdown report string. */
export function exportReviewMarkdown(
  result: ReviewResponse,
  title?: string | null,
): string {
  const mrTitle = (title ?? "").trim() || "Untitled merge request";
  const personasUsed =
    result.personaReviews.map((pr) => PERSONA_LABELS[pr.persona]).join(", ") ||
    "None";

  const lines: string[] = [];

  lines.push("# MR Review Council Report");
  lines.push("");
  lines.push(`**Merge request:** ${mrTitle}`);
  lines.push("");

  // Metadata
  lines.push("## Overview");
  lines.push("");
  lines.push(`- **Generated:** ${new Date().toISOString()}`);
  lines.push(`- **Overall risk:** ${RISK_LABELS[result.overallRisk]}`);
  lines.push(
    `- **Merge recommendation:** ${RECOMMENDATION_LABELS[result.mergeRecommendation]}`,
  );
  lines.push(`- **Personas used:** ${personasUsed}`);
  lines.push(`- **Files changed:** ${result.diffStats.filesChanged}`);
  lines.push(`- **Added lines:** ${result.diffStats.addedLines}`);
  lines.push(`- **Removed lines:** ${result.diffStats.removedLines}`);
  lines.push(`- **Total hunks:** ${result.diffStats.totalHunks}`);
  lines.push(`- **Total findings:** ${result.summary.totalFindings}`);
  lines.push("");

  // Summary
  lines.push("## Summary");
  lines.push("");
  lines.push(`**${result.summary.headline}**`);
  lines.push("");
  lines.push(result.summary.details);
  lines.push("");

  // Findings grouped by reviewer
  lines.push("## Findings");
  lines.push("");
  if (result.findings.length === 0) {
    lines.push("No findings found.");
    lines.push("");
  } else {
    const personas = PERSONA_ORDER.filter((p) =>
      result.personaReviews.some((pr) => pr.persona === p),
    );
    for (const persona of personas) {
      const review = result.personaReviews.find((pr) => pr.persona === persona);
      if (!review) {
        continue;
      }
      lines.push(`### ${PERSONA_LABELS[persona]}`);
      lines.push("");
      if (review.summary) {
        lines.push(`_${review.summary}_`);
        lines.push("");
      }
      if (review.findings.length === 0) {
        lines.push("No findings from this reviewer.");
        lines.push("");
      } else {
        for (const finding of review.findings) {
          lines.push(...findingBlock(finding));
        }
      }
    }
  }

  // Suggested replies (only when present)
  if (result.suggestedReplies.length > 0) {
    lines.push(...suggestedRepliesSection(result.suggestedReplies));
  }

  // Footer
  lines.push("---");
  lines.push("");
  lines.push(
    "_Generated locally by MR Review Council using a deterministic mock review " +
      "engine (no AI). This report is meant to support, not replace, human review._",
  );
  lines.push("");

  return lines.join("\n");
}
