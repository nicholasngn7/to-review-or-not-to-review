/**
 * Git provider comment-import contract types (v0.3).
 *
 * These mirror the backend Pydantic models in `backend/app/models/git_import.py`
 * (camelCase JSON). They support a **local, fixture-based** import demo only:
 * pasted provider-shaped JSON is normalized through `POST /api/import-comments`.
 * Nothing here fetches from GitHub/GitLab, uses tokens/OAuth, or posts comments.
 */

import type { CommentThread } from "./review";

export type GitProviderType = "github" | "gitlab";

export type ImportSource =
  | "github_review_comments"
  | "github_issue_comments"
  | "gitlab_discussions";

export interface ExternalCommentReference {
  provider: GitProviderType;
  repository?: string | null;
  projectId?: string | null;
  pullRequestNumber?: number | null;
  mergeRequestIid?: number | null;
  discussionId?: string | null;
  reviewId?: string | null;
  commentId?: string | null;
  noteId?: string | null;
  webUrl?: string | null;
  isOutdated?: boolean | null;
}

export interface ImportedCommentThread {
  thread: CommentThread;
  externalReference: ExternalCommentReference;
  warnings: string[];
}

export interface ImportCommentsRequest {
  provider: GitProviderType;
  source?: ImportSource | null;
  /** Already-parsed provider JSON (array or object). Never a URL or token. */
  rawPayload?: unknown;
}

export interface ImportCommentsResponse {
  provider: GitProviderType;
  threads: ImportedCommentThread[];
  warnings: string[];
}
