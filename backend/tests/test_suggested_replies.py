"""Tests for deterministic suggested-reply generation (Phase 15).

Replies are copy-only drafts derived from comment threads. They must never change
detection, risk, finding count, severity, or the merge recommendation.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.comments import CommentThread, ThreadComment
from app.models.enums import ReviewerPersona
from app.models.review import ReviewRequest
from app.models.tone import ToneProfile, ToneStrictness, ToneStyle
from app.services.review_engine import run_review

client = TestClient(app)

DIFF = (
    "diff --git a/app/auth.py b/app/auth.py\n"
    "--- a/app/auth.py\n"
    "+++ b/app/auth.py\n"
    "@@ -1,2 +1,5 @@\n"
    " import os\n"
    "+try:\n"
    "+    do_login()\n"
    "+except Exception:\n"
    "+    pass\n"
)


def _thread(
    body: str,
    *,
    tid: str = "t1",
    author: str = "Reviewer",
    file_path: str | None = "app/auth.py",
    line: int | None = 5,
) -> CommentThread:
    return CommentThread(
        id=tid,
        file_path=file_path,
        line=line,
        comments=[ThreadComment(id=f"{tid}-c1", author=author, body=body)],
    )


def _request(
    body: str | None,
    personas: list[ReviewerPersona],
    **kwargs,
) -> ReviewRequest:
    threads = [_thread(body)] if body is not None else None
    return ReviewRequest(
        diff_text=DIFF,
        selected_personas=personas,
        comment_threads=threads,
        **kwargs,
    )


# 1. No comment threads -> no replies.
def test_no_comment_threads_returns_empty_replies():
    resp = run_review(_request(None, [ReviewerPersona.SECURITY]))
    assert resp.suggested_replies == []


# 2. QA terms -> QA reply when QA selected.
def test_qa_terms_generate_qa_reply():
    resp = run_review(
        _request(
            "Can we add a regression test for coverage here?",
            [ReviewerPersona.QA, ReviewerPersona.BACKEND],
        )
    )
    reviewers = {r.reviewer for r in resp.suggested_replies}
    assert ReviewerPersona.QA in reviewers


# 3. Security terms -> Security reply when Security selected.
def test_security_terms_generate_security_reply():
    resp = run_review(
        _request(
            "Does this leak the auth token or any secret?",
            [ReviewerPersona.SECURITY, ReviewerPersona.QA],
        )
    )
    reviewers = {r.reviewer for r in resp.suggested_replies}
    assert ReviewerPersona.SECURITY in reviewers


# Relevant-but-unselected personas are not used.
def test_only_selected_personas_get_replies():
    resp = run_review(
        _request(
            "Does this leak the auth token?",  # security keywords
            [ReviewerPersona.QA],  # security NOT selected
        )
    )
    # No security keyword match among selected -> falls back to QA (first selected).
    assert all(r.reviewer == ReviewerPersona.QA for r in resp.suggested_replies)


# 4. Fallback when no keyword matches.
def test_fallback_when_no_keyword_matches():
    resp = run_review(
        _request(
            "Looks fine to me overall.",  # no routing keywords
            [ReviewerPersona.BACKEND, ReviewerPersona.PRODUCT],
        )
    )
    assert len(resp.suggested_replies) == 1
    reply = resp.suggested_replies[0]
    # Product is preferred for fallback when selected.
    assert reply.reviewer == ReviewerPersona.PRODUCT
    assert reply.confidence == 0.3


def test_fallback_uses_first_selected_when_no_product_or_architect():
    resp = run_review(
        _request("Looks fine.", [ReviewerPersona.BACKEND, ReviewerPersona.SRE])
    )
    assert len(resp.suggested_replies) == 1
    assert resp.suggested_replies[0].reviewer == ReviewerPersona.BACKEND


# 5. Tone changes wording but not selection/count/confidence.
def test_tone_changes_wording_not_selection_or_confidence():
    personas = [ReviewerPersona.SECURITY, ReviewerPersona.QA]
    body = "Does this leak the auth token, and can we add a test?"
    baseline = run_review(_request(body, personas))
    toned = run_review(
        _request(
            body,
            personas,
            tone_profile=ToneProfile(
                style=ToneStyle.SUPPORTIVE, strictness=ToneStrictness.HIGH
            ),
        )
    )

    def fingerprint(resp):
        return [
            (r.id, r.thread_id, r.reviewer, r.confidence, r.needs_human_review)
            for r in resp.suggested_replies
        ]

    assert fingerprint(baseline) == fingerprint(toned)
    # ...but at least one reply's wording differs.
    base_text = [r.suggested_reply for r in baseline.suggested_replies]
    toned_text = [r.suggested_reply for r in toned.suggested_replies]
    assert base_text != toned_text
    assert all(t.startswith("To keep things smooth: ") for t in toned_text)


# 6. Suggested replies do not change findings/risk/merge recommendation.
def test_replies_do_not_change_detection():
    personas = [ReviewerPersona.SECURITY, ReviewerPersona.SRE]
    without = run_review(_request(None, personas))
    with_threads = run_review(
        _request("Can we avoid swallowing this exception and add logging?", personas)
    )

    assert without.overall_risk == with_threads.overall_risk
    assert without.merge_recommendation == with_threads.merge_recommendation
    assert [f.id for f in without.findings] == [
        f.id for f in with_threads.findings
    ]
    assert without.diff_stats == with_threads.diff_stats
    # The only difference is the presence of suggested replies.
    assert without.suggested_replies == []
    assert len(with_threads.suggested_replies) >= 1


# 7. needsHumanReview is always true.
def test_replies_always_need_human_review():
    resp = run_review(
        _request(
            "Can we avoid swallowing this exception and add logging?",
            [ReviewerPersona.BACKEND, ReviewerPersona.SRE],
        )
    )
    assert resp.suggested_replies
    assert all(r.needs_human_review is True for r in resp.suggested_replies)


# Multiple selected personas relevant to one thread each get a reply.
def test_multiple_relevant_personas_each_reply():
    resp = run_review(
        _request(
            "Can we avoid swallowing this exception and add logging?",
            [ReviewerPersona.BACKEND, ReviewerPersona.SRE],
        )
    )
    reviewers = {r.reviewer for r in resp.suggested_replies}
    assert ReviewerPersona.BACKEND in reviewers
    assert ReviewerPersona.SRE in reviewers


# 8. /api/reviews returns suggestedReplies for valid commentThreads.
def test_reviews_route_returns_suggested_replies():
    resp = client.post(
        "/api/reviews",
        json={
            "diffText": DIFF,
            "selectedPersonas": ["backend", "sre"],
            "commentThreads": [
                {
                    "id": "t1",
                    "filePath": "app/auth.py",
                    "line": 5,
                    "status": "open",
                    "comments": [
                        {
                            "id": "c1",
                            "author": "Reviewer",
                            "body": "Avoid swallowing this exception and add logging?",
                        }
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 200
    replies = resp.json()["suggestedReplies"]
    assert len(replies) >= 1
    first = replies[0]
    assert first["threadId"] == "t1"
    assert first["needsHumanReview"] is True
    assert "suggestedReply" in first and first["suggestedReply"]


# Phase 16: replies carry source-thread file/line context.
def test_reply_includes_file_and_line_from_thread():
    resp = run_review(
        _request(
            "Can we avoid swallowing this exception and add logging?",
            [ReviewerPersona.BACKEND, ReviewerPersona.SRE],
        )
    )
    assert resp.suggested_replies
    assert all(r.file_path == "app/auth.py" for r in resp.suggested_replies)
    assert all(r.line == 5 for r in resp.suggested_replies)


def test_reply_omits_file_and_line_when_thread_lacks_them():
    req = ReviewRequest(
        diff_text=DIFF,
        selected_personas=[ReviewerPersona.BACKEND],
        comment_threads=[
            _thread("Avoid swallowing this exception.", file_path=None, line=None)
        ],
    )
    resp = run_review(req)
    assert resp.suggested_replies
    assert all(r.file_path is None for r in resp.suggested_replies)
    assert all(r.line is None for r in resp.suggested_replies)


def test_file_line_context_does_not_change_routing_or_detection():
    personas = [ReviewerPersona.BACKEND, ReviewerPersona.SRE]
    body = "Can we avoid swallowing this exception and add logging?"
    with_ctx = run_review(_request(body, personas))
    without_ctx = run_review(
        _request(body, personas, file_path=None, line=None)
    )

    def routing(resp):
        return [
            (r.reviewer, r.confidence, r.needs_human_review)
            for r in resp.suggested_replies
        ]

    # Routing/selection/confidence identical regardless of file/line context.
    assert routing(with_ctx) == routing(without_ctx)
    # Detection unaffected.
    assert with_ctx.overall_risk == without_ctx.overall_risk
    assert with_ctx.merge_recommendation == without_ctx.merge_recommendation
    assert [f.id for f in with_ctx.findings] == [
        f.id for f in without_ctx.findings
    ]


def test_route_returns_file_and_line_in_replies():
    resp = client.post(
        "/api/reviews",
        json={
            "diffText": DIFF,
            "selectedPersonas": ["backend"],
            "commentThreads": [
                {
                    "id": "t1",
                    "filePath": "app/auth.py",
                    "line": 5,
                    "status": "open",
                    "comments": [
                        {"id": "c1", "body": "Handle this exception explicitly."}
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 200
    reply = resp.json()["suggestedReplies"][0]
    assert reply["filePath"] == "app/auth.py"
    assert reply["line"] == 5


# Determinism: identical inputs -> identical replies.
def test_reply_generation_is_deterministic():
    req = _request(
        "Does this leak the auth token, and can we add a test?",
        [ReviewerPersona.SECURITY, ReviewerPersona.QA],
    )
    a = run_review(req)
    b = run_review(req)
    assert a.model_dump() == b.model_dump()
