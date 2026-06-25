/**
 * Bundled **synthetic** sample payloads for the local import demo.
 *
 * These let the "Import comments (local demo)" panel be exercised without pasting
 * JSON by hand. Everything here is fabricated for demonstration:
 *   - no real repositories, projects, people, or tokens
 *   - no payloads copied from production GitHub/GitLab
 *   - URLs use the reserved `example.test` domain
 *
 * Clicking a sample only populates the provider, source, and JSON textarea — the
 * user still clicks "Normalize comments", which calls the local-only
 * `POST /api/import-comments`. Nothing is fetched from a provider or posted anywhere.
 */

import type { GitProviderType, ImportSource } from "../types/gitImport";

export interface ImportSample {
  id: string;
  label: string;
  description: string;
  provider: GitProviderType;
  source: ImportSource;
  /** Parsed payload; the panel pretty-prints this into the textarea. */
  payload: unknown;
}

const githubReviewComments: ImportSample = {
  id: "github-review-comments",
  label: "GitHub review comments",
  description:
    "Inline PR review comments, including a reply chain and a resolved thread.",
  provider: "github",
  source: "github_review_comments",
  payload: [
    {
      id: 1001,
      user: { login: "reviewer-alpha" },
      body: "Can we avoid swallowing this exception and add logging instead?",
      created_at: "2026-01-02T10:00:00Z",
      path: "service/auth.py",
      line: 42,
      pull_request_review_id: 555,
      html_url: "https://example.test/demo-org/sample-service/pull/7#discussion_r1001",
    },
    {
      id: 1002,
      in_reply_to_id: 1001,
      user: { login: "reviewer-beta" },
      body: "Agreed — let's log at warning level and re-raise.",
      created_at: "2026-01-02T11:00:00Z",
      path: "service/auth.py",
      line: 42,
      html_url: "https://example.test/demo-org/sample-service/pull/7#discussion_r1002",
    },
    {
      id: 1003,
      user: { login: "reviewer-gamma" },
      body: "This input should be validated before use.",
      created_at: "2026-01-02T12:00:00Z",
      path: "service/api.py",
      line: 18,
      html_url: "https://example.test/demo-org/sample-service/pull/7#discussion_r1003",
    },
    {
      id: 1004,
      user: { login: "reviewer-gamma" },
      body: "Already addressed in an earlier commit — resolving.",
      created_at: "2026-01-03T09:30:00Z",
      path: "service/config.py",
      line: 10,
      resolved: true,
      html_url: "https://example.test/demo-org/sample-service/pull/7#discussion_r1004",
    },
  ],
};

const githubIssueComments: ImportSample = {
  id: "github-issue-comments",
  label: "GitHub issue comments",
  description: "PR conversation comments that are not anchored to a line.",
  provider: "github",
  source: "github_issue_comments",
  payload: [
    {
      id: 2001,
      user: { login: "reviewer-alpha" },
      body: "Overall this looks close. Can we split the migration into its own PR?",
      created_at: "2026-02-01T09:00:00Z",
      html_url: "https://example.test/demo-org/sample-service/pull/7#issuecomment-2001",
    },
    {
      id: 2002,
      user: { login: "reviewer-beta" },
      body: "Please add a changelog entry before merge.",
      created_at: "2026-02-01T10:30:00Z",
      html_url: "https://example.test/demo-org/sample-service/pull/7#issuecomment-2002",
    },
    {
      id: 2003,
      user: { login: "reviewer-gamma" },
      body: "Approving once the changelog is added.",
      created_at: "2026-02-01T11:15:00Z",
      html_url: "https://example.test/demo-org/sample-service/pull/7#issuecomment-2003",
    },
  ],
};

const gitlabDiscussions: ImportSample = {
  id: "gitlab-discussions",
  label: "GitLab discussions",
  description:
    "MR discussions with a positioned thread, a reply, and a resolved thread.",
  provider: "gitlab",
  source: "gitlab_discussions",
  payload: [
    {
      id: "disc-1",
      notes: [
        {
          id: 11,
          system: false,
          author: { username: "alpha" },
          body: "Should we validate this input before using it?",
          created_at: "2026-03-01T09:00:00Z",
          resolvable: true,
          resolved: false,
          position: {
            new_path: "service/api.py",
            new_line: 12,
            old_path: "service/api.py",
            old_line: 10,
          },
          web_url: "https://example.test/demo-group/sample-project/-/merge_requests/3#note_11",
        },
        {
          id: 12,
          system: false,
          author: { username: "beta" },
          body: "Good catch — I'll add a guard clause.",
          created_at: "2026-03-01T09:30:00Z",
          resolvable: true,
          resolved: false,
        },
      ],
    },
    {
      id: "disc-2",
      notes: [
        {
          id: 21,
          system: true,
          body: "changed the description",
          created_at: "2026-03-01T10:00:00Z",
        },
        {
          id: 22,
          system: false,
          author: { username: "gamma" },
          body: "Please rebase onto main before merge.",
          created_at: "2026-03-01T10:30:00Z",
        },
      ],
    },
    {
      id: "disc-3",
      resolved: true,
      notes: [
        {
          id: 31,
          system: false,
          author: { username: "delta" },
          body: "This is handled now — resolving.",
          created_at: "2026-03-02T09:00:00Z",
          resolvable: true,
          resolved: true,
          position: { new_path: "service/config.py", new_line: 5 },
        },
      ],
    },
  ],
};

/** Ordered list shown in the panel's "Load sample payload" section. */
export const IMPORT_SAMPLES: ImportSample[] = [
  githubReviewComments,
  githubIssueComments,
  gitlabDiscussions,
];
