"""Tests for the Git comment-import contract models (v0.3, Phase 1).

Contracts only: no mappers, no fixtures, no network, no tokens, no endpoints. These
tests pin down the model shapes and camelCase serialization that a future mapping
layer will produce.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    CommentThread,
    ExternalCommentReference,
    GitProviderType,
    ImportCommentsRequest,
    ImportCommentsResponse,
    ImportedCommentThread,
    ThreadComment,
)


def _thread(tid: str = "t1") -> CommentThread:
    return CommentThread(
        id=tid,
        file_path="app/auth.py",
        line=5,
        comments=[ThreadComment(id="c1", author="Reviewer", body="Please fix.")],
    )


# 1. GitProviderType accepts github/gitlab and rejects invalid providers.
def test_git_provider_type_accepts_known_and_rejects_unknown():
    assert GitProviderType("github") is GitProviderType.GITHUB
    assert GitProviderType("gitlab") is GitProviderType.GITLAB

    with pytest.raises(ValueError):
        GitProviderType("bitbucket")

    # Through a model field, an unknown provider is a validation error.
    with pytest.raises(ValidationError):
        ExternalCommentReference(provider="bitbucket")


# 2. ExternalCommentReference serializes camelCase fields.
def test_external_reference_serializes_camel_case():
    ref = ExternalCommentReference(
        provider=GitProviderType.GITHUB,
        repository="acme/widgets",
        pull_request_number=42,
        comment_id="rc-1",
        review_id="rev-9",
        web_url="https://github.com/acme/widgets/pull/42",
        is_outdated=False,
    )
    data = ref.model_dump(by_alias=True)
    assert data["provider"] == "github"
    assert data["pullRequestNumber"] == 42
    assert data["commentId"] == "rc-1"
    assert data["reviewId"] == "rev-9"
    assert data["webUrl"] == "https://github.com/acme/widgets/pull/42"
    assert data["isOutdated"] is False
    # snake_case keys should not leak into the serialized JSON.
    assert "pull_request_number" not in data


# 3. ImportedCommentThread wraps an existing CommentThread and external reference.
def test_imported_thread_wraps_thread_and_reference():
    imported = ImportedCommentThread(
        thread=_thread(),
        external_reference=ExternalCommentReference(
            provider=GitProviderType.GITLAB,
            project_id="group/proj",
            merge_request_iid=7,
            discussion_id="disc-1",
        ),
        warnings=["line was outdated; dropped"],
    )
    assert isinstance(imported.thread, CommentThread)
    assert imported.thread.id == "t1"
    assert imported.external_reference.provider is GitProviderType.GITLAB

    data = imported.model_dump(by_alias=True)
    assert data["externalReference"]["mergeRequestIid"] == 7
    assert data["thread"]["filePath"] == "app/auth.py"
    assert data["warnings"] == ["line was outdated; dropped"]


# 4. ImportCommentsRequest accepts provider and raw_payload but has no token field.
def test_import_request_accepts_payload_and_has_no_token():
    req = ImportCommentsRequest(
        provider=GitProviderType.GITHUB,
        source="fixture",
        raw_payload={"comments": [{"id": "1", "body": "hi"}]},
    )
    assert req.provider is GitProviderType.GITHUB
    assert req.raw_payload == {"comments": [{"id": "1", "body": "hi"}]}

    # A list payload is also acceptable.
    req_list = ImportCommentsRequest(
        provider=GitProviderType.GITLAB, raw_payload=[{"id": "d1"}]
    )
    assert req_list.raw_payload == [{"id": "d1"}]

    # No token field exists anywhere on the contract.
    assert "token" not in ImportCommentsRequest.model_fields
    assert "token" not in req.model_dump(by_alias=True)


# 5. ImportCommentsResponse serializes threads and warnings.
def test_import_response_serializes_threads_and_warnings():
    resp = ImportCommentsResponse(
        provider=GitProviderType.GITHUB,
        threads=[
            ImportedCommentThread(
                thread=_thread(),
                external_reference=ExternalCommentReference(
                    provider=GitProviderType.GITHUB, comment_id="rc-1"
                ),
            )
        ],
        warnings=["1 system note skipped"],
    )
    data = resp.model_dump(by_alias=True)
    assert data["provider"] == "github"
    assert len(data["threads"]) == 1
    assert data["threads"][0]["externalReference"]["commentId"] == "rc-1"
    assert data["warnings"] == ["1 system note skipped"]

    # Defaults: empty threads/warnings lists.
    empty = ImportCommentsResponse(provider=GitProviderType.GITLAB)
    assert empty.threads == []
    assert empty.warnings == []


# 6. Minimal GitHub-style reference validates.
def test_minimal_github_reference_validates():
    ref = ExternalCommentReference(
        provider=GitProviderType.GITHUB,
        repository="acme/widgets",
        pull_request_number=42,
        comment_id="rc-1",
    )
    assert ref.repository == "acme/widgets"
    assert ref.merge_request_iid is None  # GitLab-only fields stay None


# 7. Minimal GitLab-style reference validates.
def test_minimal_gitlab_reference_validates():
    ref = ExternalCommentReference(
        provider=GitProviderType.GITLAB,
        project_id="group/proj",
        merge_request_iid=7,
        discussion_id="disc-1",
        note_id="note-1",
    )
    assert ref.merge_request_iid == 7
    assert ref.pull_request_number is None  # GitHub-only fields stay None


# 8. Optional fields may be omitted without breaking validation.
def test_optional_fields_may_be_omitted():
    ref = ExternalCommentReference(provider=GitProviderType.GITHUB)
    assert ref.repository is None
    assert ref.web_url is None
    assert ref.is_outdated is None

    # Provider is the only required field; everything else defaults.
    with pytest.raises(ValidationError):
        ExternalCommentReference()
