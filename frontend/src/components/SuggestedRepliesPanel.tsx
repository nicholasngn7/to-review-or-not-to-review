import type { CommentThread, SuggestedReply } from "../types/review";
import { SuggestedReplyCard } from "./SuggestedReplyCard";

interface SuggestedRepliesPanelProps {
  replies: SuggestedReply[];
  /** Original submitted threads, for file/line context (by thread id). */
  commentThreads?: CommentThread[] | null;
}

export function SuggestedRepliesPanel({
  replies,
  commentThreads,
}: SuggestedRepliesPanelProps) {
  if (replies.length === 0) {
    return null;
  }

  const threadsById = new Map<string, CommentThread>();
  for (const thread of commentThreads ?? []) {
    threadsById.set(thread.id, thread);
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

  return (
    <section className="replies" aria-label="Suggested replies">
      <h3 className="results__section-title">Suggested replies</h3>
      <p className="replies__note">
        Draft suggestions for existing comment threads. Nothing is posted
        anywhere — review and edit before sending.
      </p>

      {order.map((threadId) => (
        <div className="reply-thread" key={threadId}>
          <h4 className="reply-thread__title">
            Thread <code>{threadId}</code>
          </h4>
          <div className="reply-thread__cards">
            {byThread.get(threadId)!.map((reply) => (
              <SuggestedReplyCard
                key={reply.id}
                reply={reply}
                thread={threadsById.get(threadId)}
              />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
