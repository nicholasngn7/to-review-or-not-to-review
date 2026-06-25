"""Tests for the pure GitLab MR discussions mapper (v0.3, Phase 4).

Fixture-only and network-free. One discussion -> one thread; ordered non-system,
non-empty notes -> ordered comments.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from app.models.comments import CommentThread, CommentThreadStatus
from app.models.git_import import (
    ExternalCommentReference,
    GitProviderType,
    ImportedCommentThread,
)
from app.services.git_import import map_gitlab_discussions_to_threads

FIXTURE = Path(__file__).parent / "fixtures" / "gitlab_mr_discussions.json"

PROJECT = "grp/proj"
MR = 3


def _load() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _map(**kwargs) -> list[ImportedCommentThread]:
    return map_gitlab_discussions_to_threads(
        _load(), project_id=PROJECT, merge_request_iid=MR, **kwargs
    )


def _by_discussion_id(
    threads: list[ImportedCommentThread], discussion_id: str
) -> ImportedCommentThread | None:
    for imported in threads:
        if imported.external_reference.discussion_id == discussion_id:
            return imported
    return None


# 1. Fixture loads successfully.
def test_fixture_loads():
    data = _load()
    assert isinstance(data, list)
    assert len(data) == 8


# 2. Each valid discussion becomes one CommentThread (input order).
def test_each_valid_discussion_becomes_one_thread():
    threads = _map()
    ids = [t.external_reference.discussion_id for t in threads]
    # disc-3 (all empty) and disc-7 (outdated) are dropped by default.
    assert ids == ["disc-1", "disc-2", "disc-4", "disc-5", "disc-6", "disc-8"]


# 3. Notes are ordered and mapped into ThreadComment items.
def test_notes_ordered_into_comments():
    d1 = _by_discussion_id(_map(), "disc-1")
    assert [c.body for c in d1.thread.comments] == [
        "Should we validate this input before using it?",
        "Good catch — I'll add a guard clause.",
    ]
    assert d1.thread.comments[0].author == "alpha"
    assert d1.thread.comments[1].author == "beta"


# 4. System notes are filtered.
def test_system_notes_filtered():
    d2 = _by_discussion_id(_map(), "disc-2")
    assert len(d2.thread.comments) == 1
    assert d2.thread.comments[0].body.startswith("Please rebase")


# 5. Empty-body notes are dropped (but a valid sibling survives).
def test_empty_body_notes_dropped():
    d4 = _by_discussion_id(_map(), "disc-4")
    assert len(d4.thread.comments) == 1
    assert d4.thread.comments[0].body.startswith("Add a test")
    # The first usable note id is the surviving note.
    assert d4.external_reference.note_id == "42"


# 6. Discussion with all dropped notes is skipped.
def test_all_dropped_discussion_skipped():
    assert _by_discussion_id(_map(), "disc-3") is None


# 7. File path and line map from position.new_path / new_line.
def test_position_new_path_line_map():
    d1 = _by_discussion_id(_map(), "disc-1")
    assert d1.thread.file_path == "service/api.py"
    assert d1.thread.line == 12


# 8. Fallback to old_path / old_line works.
def test_position_old_path_line_fallback():
    d6 = _by_discussion_id(_map(), "disc-6")
    assert d6.thread.file_path == "service/legacy.py"
    assert d6.thread.line == 88
    # author falls back to author.name when username is absent.
    assert d6.thread.comments[0].author == "Echo Reviewer"


# 9. Non-positional discussion becomes line-less.
def test_non_positional_discussion_line_less():
    d2 = _by_discussion_id(_map(), "disc-2")
    assert d2.thread.file_path is None
    assert d2.thread.line is None


# 10. Resolved / open / unknown status mapping works.
def test_status_mapping():
    threads = _map()
    assert _by_discussion_id(threads, "disc-1").thread.status is CommentThreadStatus.OPEN
    assert _by_discussion_id(threads, "disc-5").thread.status is CommentThreadStatus.RESOLVED
    assert _by_discussion_id(threads, "disc-2").thread.status is CommentThreadStatus.UNKNOWN
    assert _by_discussion_id(threads, "disc-8").thread.status is CommentThreadStatus.UNKNOWN


# 11. include_resolved=False filters resolved discussions.
def test_include_resolved_false_filters_resolved():
    assert _by_discussion_id(_map(), "disc-5") is not None
    assert _by_discussion_id(_map(include_resolved=False), "disc-5") is None


# 11b. Outdated discussions: skipped by default, includable with a warning.
def test_outdated_skipped_then_included_with_warning():
    assert _by_discussion_id(_map(), "disc-7") is None

    included = _by_discussion_id(_map(include_outdated=True), "disc-7")
    assert included is not None
    assert included.thread.file_path == "service/moved.py"
    assert included.thread.line is None  # stale anchor -> line dropped
    assert included.external_reference.is_outdated is True
    assert any("outdated" in w for w in included.warnings)


# 12. ExternalCommentReference preserves GitLab provenance.
def test_external_reference_provenance():
    ref = _by_discussion_id(_map(), "disc-1").external_reference
    assert ref.provider is GitProviderType.GITLAB
    assert ref.project_id == PROJECT
    assert ref.merge_request_iid == MR
    assert ref.discussion_id == "disc-1"
    assert ref.note_id == "11"
    assert ref.web_url.endswith("#note_11")
    # GitHub-only provenance stays None.
    assert ref.pull_request_number is None
    assert ref.review_id is None


# 13. Missing author / createdAt are handled safely.
def test_missing_author_and_created_at_safe():
    d2 = _by_discussion_id(_map(), "disc-2")
    note = d2.thread.comments[0]
    assert note.author is None
    assert note.created_at is None


# 14. Synthetic ids are deterministic across repeated calls.
def test_synthetic_ids_deterministic():
    first = [t.thread.id for t in _map()]
    second = [t.thread.id for t in _map()]
    assert first == second
    assert _by_discussion_id(_map(), "disc-1").thread.id == "gitlab:grp/proj:3:disc:disc-1"


# 15. Output conforms to ImportedCommentThread / CommentThread models.
def test_output_conforms_to_models():
    for imported in _map(include_outdated=True):
        assert isinstance(imported, ImportedCommentThread)
        assert isinstance(imported.thread, CommentThread)
        assert isinstance(imported.external_reference, ExternalCommentReference)
        ImportedCommentThread.model_validate(imported.model_dump())
        assert imported.thread.comments
        assert all(c.body.strip() for c in imported.thread.comments)


# 16. Unknown/extra fields are ignored safely.
def test_unknown_fields_ignored():
    d8 = _by_discussion_id(_map(), "disc-8")
    assert d8 is not None
    assert d8.thread.comments[0].body.startswith("LGTM")
    assert d8.thread.status is CommentThreadStatus.UNKNOWN


# 17. Mapper requires no network, tokens, or endpoints.
def test_no_network_or_token_surface():
    params = set(inspect.signature(map_gitlab_discussions_to_threads).parameters)
    assert "token" not in params
    assert "url" not in params
    assert map_gitlab_discussions_to_threads([]) == []
