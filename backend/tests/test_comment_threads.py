"""Tests for the existing-comment-thread contract (Phase 14).

Comment threads are captured as structured input on `ReviewRequest`. The API
accepts and validates them but does not yet generate suggested replies — the
response carries an empty `suggestedReplies` list until Phase 15.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.comments import CommentThread, CommentThreadStatus, ThreadComment
from app.models.review import ReviewRequest

client = TestClient(app)

DIFF = (
    "diff --git a/app/auth.py b/app/auth.py\n"
    "--- a/app/auth.py\n"
    "+++ b/app/auth.py\n"
    "@@ -1,2 +1,4 @@\n"
    " import os\n"
    "+try:\n"
    "+    do_login()\n"
    "+except Exception:\n"
    "+    pass\n"
)


def _thread(**overrides) -> dict:
    base = {
        "id": "t1",
        "filePath": "app/auth.py",
        "line": 5,
        "status": "open",
        "comments": [
            {
                "id": "c1",
                "author": "Reviewer",
                "body": "Can we avoid swallowing this exception?",
            }
        ],
    }
    base.update(overrides)
    return base


# 1. Validates without commentThreads.
def test_request_without_comment_threads_is_valid():
    req = ReviewRequest(diff_text=DIFF, selected_personas=["security"])
    assert req.comment_threads is None


# 2. Validates with one comment thread.
def test_request_with_one_comment_thread_validates():
    thread = CommentThread(
        id="t1",
        file_path="app/auth.py",
        line=5,
        status=CommentThreadStatus.OPEN,
        comments=[ThreadComment(id="c1", author="Reviewer", body="Please fix.")],
    )
    req = ReviewRequest(
        diff_text=DIFF, selected_personas=["security"], comment_threads=[thread]
    )
    assert req.comment_threads is not None
    assert req.comment_threads[0].comments[0].body == "Please fix."


# 3a. Empty comment body fails validation.
def test_empty_comment_body_fails_validation():
    with pytest.raises(ValidationError):
        ThreadComment(id="c1", body="   ")


# 3b. A thread with no comments fails validation.
def test_thread_without_comments_fails_validation():
    with pytest.raises(ValidationError):
        CommentThread(id="t1", comments=[])


# Body is trimmed on the way in.
def test_comment_body_is_trimmed():
    comment = ThreadComment(id="c1", body="  trim me  ")
    assert comment.body == "trim me"


# 4. /api/reviews accepts commentThreads and returns empty suggestedReplies.
def test_reviews_route_accepts_comment_threads():
    resp = client.post(
        "/api/reviews",
        json={
            "diffText": DIFF,
            "selectedPersonas": ["security", "sre"],
            "commentThreads": [_thread()],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Normal review output is present...
    assert "overallRisk" in body
    assert "findings" in body
    # ...and suggestedReplies is present as a list (populated as of Phase 15).
    assert isinstance(body["suggestedReplies"], list)


# 5. Existing behavior unchanged when commentThreads omitted.
def test_response_unchanged_without_comment_threads():
    payload = {"diffText": DIFF, "selectedPersonas": ["security", "sre"]}
    without = client.post("/api/reviews", json=payload).json()
    with_threads = client.post(
        "/api/reviews", json={**payload, "commentThreads": [_thread()]}
    ).json()

    # Comment threads must not influence detection or aggregation.
    without.pop("suggestedReplies", None)
    with_threads.pop("suggestedReplies", None)
    assert without == with_threads


# Invalid comment body via the route surfaces as a 422.
def test_reviews_route_rejects_empty_comment_body():
    resp = client.post(
        "/api/reviews",
        json={
            "diffText": DIFF,
            "selectedPersonas": ["security"],
            "commentThreads": [_thread(comments=[{"id": "c1", "body": "  "}])],
        },
    )
    assert resp.status_code == 422
