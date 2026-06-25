import { useState } from "react";

import type { CommentThread, SuggestedReply } from "../types/review";
import { PERSONA_LABELS } from "../lib/reviewLabels";

interface SuggestedReplyCardProps {
  reply: SuggestedReply;
  thread?: CommentThread;
}

export function SuggestedReplyCard({ reply, thread }: SuggestedReplyCardProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(reply.suggestedReply);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be unavailable (e.g. insecure context); fail quietly.
      setCopied(false);
    }
  };

  const location: string[] = [];
  if (thread?.filePath) {
    location.push(thread.filePath);
  }
  if (thread?.line != null) {
    location.push(`line ${thread.line}`);
  }

  return (
    <div className="reply-card">
      <div className="reply-card__head">
        <span className="pill pill--persona">
          {PERSONA_LABELS[reply.reviewer]}
        </span>
        <span className="pill reply-card__badge" title="Always required">
          Needs human review
        </span>
        {reply.confidence != null && (
          <span className="pill pill--confidence">
            {Math.round(reply.confidence * 100)}% confidence
          </span>
        )}
        <button
          type="button"
          className="link-button reply-card__copy"
          onClick={copy}
        >
          {copied ? "Copied" : "Copy reply"}
        </button>
      </div>

      <blockquote className="reply-card__text">
        {reply.suggestedReply}
      </blockquote>

      <p className="reply-card__rationale">
        <span className="reply-card__rationale-label">Why:</span>{" "}
        {reply.rationale}
      </p>

      {location.length > 0 && (
        <p className="reply-card__loc">{location.join(" · ")}</p>
      )}
    </div>
  );
}
