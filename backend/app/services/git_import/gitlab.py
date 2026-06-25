"""Pure GitLab MR discussions mapper (v0.3, Phase 4).

Normalizes already-parsed, GitLab-style merge-request *discussion* dicts into the
existing `ImportedCommentThread` / `CommentThread` contract. Strictly:

* no network calls, no HTTP clients, no tokens,
* defensive `.get(...)` parsing (the exact provider shape is still to be verified
  against official GitLab docs — see `docs/v0.3-plan-git-comment-import-mappers.md`),
* one discussion -> one thread; ordered `notes[]` -> ordered comments,
* deterministic output ordered by input discussion order.

Conservative outdated handling (mirrors the GitHub mapper): an outdated position is
skipped by default, and only included when `include_outdated=True` — in which case the
line is nulled (the current anchor is unreliable) and a warning is recorded.
"""

from __future__ import annotations

from typing import Optional

from app.models.comments import CommentThread, ThreadComment
from app.models.git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportedCommentThread,
)

from .common import (
    first_present,
    resolve_status,
    synthetic_thread_id,
    to_thread_comment,
)


def _as_int(value: object) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _is_system(note: dict) -> bool:
    return note.get("system") is True


def _author(note: dict) -> Optional[str]:
    author = note.get("author")
    if isinstance(author, dict):
        name = author.get("username") or author.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return author.strip() if isinstance(author, str) and author.strip() else None


def _created_at(note: dict) -> Optional[str]:
    value = first_present(note, "created_at", "createdAt")
    return value if isinstance(value, str) else None


def _web_url(*sources: dict) -> Optional[str]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        value = first_present(source, "web_url", "webUrl")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _raw_notes(discussion: dict) -> list[dict]:
    notes = discussion.get("notes")
    if not isinstance(notes, list):
        return []
    return [n for n in notes if isinstance(n, dict)]


def _extract_position(discussion: dict, raw_notes: list[dict]) -> Optional[dict]:
    for note in raw_notes:
        position = note.get("position")
        if isinstance(position, dict):
            return position
    position = discussion.get("position")
    return position if isinstance(position, dict) else None


def _file_and_line(position: Optional[dict]) -> tuple[Optional[str], Optional[int]]:
    if not position:
        return None, None
    new_path = first_present(position, "new_path", "newPath")
    old_path = first_present(position, "old_path", "oldPath")
    file_path = new_path if isinstance(new_path, str) else old_path
    file_path = file_path if isinstance(file_path, str) and file_path.strip() else None

    new_line = _as_int(first_present(position, "new_line", "newLine"))
    old_line = _as_int(first_present(position, "old_line", "oldLine"))
    line = new_line if new_line is not None else old_line
    return file_path, line


def _resolution(discussion: dict, raw_notes: list[dict]) -> Optional[bool]:
    """Derive a discussion's resolved state from its notes (or discussion-level).

    * any resolvable notes, all resolved -> True (resolved)
    * any resolvable notes, not all resolved -> False (open)
    * no resolvable signal anywhere -> None (unknown)
    """
    resolvable_present = False
    all_resolved = True
    for note in raw_notes:
        if note.get("resolvable") is True:
            resolvable_present = True
            if not bool(note.get("resolved")):
                all_resolved = False

    if not resolvable_present:
        if discussion.get("resolvable") is True:
            resolvable_present = True
            all_resolved = bool(discussion.get("resolved"))
        elif discussion.get("resolved") is not None:
            return bool(discussion.get("resolved"))

    if not resolvable_present:
        return None
    return all_resolved


def _outdated(discussion: dict, raw_notes: list[dict], position: Optional[dict]) -> Optional[bool]:
    found: Optional[bool] = None
    candidates: list[dict] = [discussion]
    candidates.extend(raw_notes)
    if isinstance(position, dict):
        candidates.append(position)
    for source in candidates:
        value = first_present(source, "outdated", "is_outdated", "isOutdated")
        if value is not None:
            found = bool(value)
    return found


def map_gitlab_discussions_to_threads(
    discussions: list[dict],
    *,
    project_id: Optional[str] = None,
    merge_request_iid: Optional[int] = None,
    include_resolved: bool = True,
    include_outdated: bool = False,
) -> list[ImportedCommentThread]:
    """Normalize GitLab MR discussions into `ImportedCommentThread`s.

    Each discussion becomes one thread; its non-system, non-empty notes become ordered
    comments. Discussions with no usable notes are dropped. Output follows input
    discussion order.
    """
    if not discussions:
        return []

    results: list[ImportedCommentThread] = []
    for discussion in discussions:
        if not isinstance(discussion, dict):
            continue

        raw_notes = _raw_notes(discussion)
        comments: list[ThreadComment] = []
        first_note_id: Optional[str] = None
        for note in raw_notes:
            if _is_system(note):
                continue
            comment_obj = to_thread_comment(
                comment_id=note.get("id"),
                body=note.get("body"),
                author=_author(note),
                created_at=_created_at(note),
                is_resolved=(
                    bool(note.get("resolved"))
                    if note.get("resolved") is not None
                    else None
                ),
            )
            if comment_obj is None:
                continue
            if first_note_id is None:
                first_note_id = str(note.get("id"))
            comments.append(comment_obj)

        if not comments:
            continue  # all notes filtered/dropped -> drop the discussion.

        resolved = _resolution(discussion, raw_notes)
        if resolved and not include_resolved:
            continue

        position = _extract_position(discussion, raw_notes)
        outdated = _outdated(discussion, raw_notes, position)
        if outdated and not include_outdated:
            continue

        warnings: list[str] = []
        file_path, line = _file_and_line(position)
        if outdated and include_outdated:
            line = None
            warnings.append(
                "discussion position is outdated; line context was dropped"
            )

        discussion_id = str(discussion.get("id"))
        thread = CommentThread(
            id=synthetic_thread_id(
                GitProviderType.GITLAB,
                project_id,
                merge_request_iid,
                "disc",
                discussion_id,
            ),
            file_path=file_path,
            line=line,
            status=resolve_status(resolved),
            comments=comments,
            source="gitlab",
        )
        external = ExternalCommentReference(
            provider=GitProviderType.GITLAB,
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            discussion_id=discussion_id,
            note_id=first_note_id,
            web_url=_web_url(discussion, *raw_notes),
            is_outdated=outdated,
        )
        results.append(
            ImportedCommentThread(
                thread=thread,
                external_reference=external,
                warnings=warnings,
            )
        )

    return results
