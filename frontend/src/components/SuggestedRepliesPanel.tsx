import { useState } from "react";
import type { ReactNode } from "react";

import type { CommentThread, SuggestedReply } from "../types/review";
import { PERSONA_LABELS } from "../lib/reviewLabels";
import { SuggestedReplyCard } from "./SuggestedReplyCard";

interface SuggestedRepliesPanelProps {
  replies: SuggestedReply[];
  /** Submitted threads — used only to decide whether to show an empty state. */
  commentThreads?: CommentThread[] | null;
}

const PANEL_NOTE =
  "Draft suggestions for existing comment threads. Nothing is posted anywhere — " +
  "review and edit before sending.";

/** One reply text per line, prefixed with the reviewer so paste is readable. */
function buildThreadCopyText(replies: SuggestedReply[]): string {
  return replies
    .map((r) => `${PERSONA_LABELS[r.reviewer]}: ${r.suggestedReply}`)
    .join("\n\n");
}

function PanelShell({ children }: { children: ReactNode }) {
  return (
    <section className="replies" aria-label="Suggested replies">
      <h3 className="results__section-title">Suggested replies</h3>
      <p className="replies__note">{PANEL_NOTE}</p>
      {children}
    </section>
  );
}

export function SuggestedRepliesPanel({
  replies,
  commentThreads,
}: SuggestedRepliesPanelProps) {
  const [copiedThreadId, setCopiedThreadId] = useState<string | null>(null);
  const threadsSubmitted = (commentThreads?.length ?? 0) > 0;

  if (replies.length === 0) {
    // Only surface an (empty) section when the user actually submitted threads.
    if (!threadsSubmitted) {
      return null;
    }
    return (
      <PanelShell>
        <p className="replies__empty">
          No suggested replies were generated for the submitted comment threads.
        </p>
      </PanelShell>
    );
  }

  // Group replies by thread id, preserving first-seen order.
  const order: string[] = [];
  const byThread = new Map<string, SuggestedReply[]>();
  for (const reply of replies) {
    if (!byThread.has(reply.threadId)) {
      byThread.set(reply.threadId, []);
      order.push(reply.threadId);
    }
    byThread.get(reply.threadId)!.push(reply);
  }

  const copyThread = async (threadId: string, group: SuggestedReply[]) => {
    try {
      await navigator.clipboard.writeText(buildThreadCopyText(group));
      setCopiedThreadId(threadId);
      window.setTimeout(() => setCopiedThreadId(null), 1500);
    } catch {
      setCopiedThreadId(null);
    }
  };

  return (
    <PanelShell>
      {order.map((threadId) => {
        const group = byThread.get(threadId)!;
        return (
          <div className="reply-thread" key={threadId}>
            <div className="reply-thread__head">
              <h4 className="reply-thread__title">
                Thread <code>{threadId}</code>
              </h4>
              <button
                type="button"
                className="link-button"
                onClick={() => copyThread(threadId, group)}
              >
                {copiedThreadId === threadId
                  ? "Copied thread replies"
                  : "Copy all replies for this thread"}
              </button>
            </div>
            <div className="reply-thread__cards">
              {group.map((reply) => (
                <SuggestedReplyCard key={reply.id} reply={reply} />
              ))}
            </div>
          </div>
        );
      })}
    </PanelShell>
  );
}
