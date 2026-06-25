"""Tests for the reviewer tone profile contract (Phase 12).

Tone is presentation/framing only: these tests verify the models validate, that
resolution prefers per-persona over global over default, and crucially that tone
input does NOT change detection results (findings, severity, risk, recommendation).
"""

import pytest
from pydantic import ValidationError

from app.models.enums import ReviewerPersona
from app.models.review import ReviewRequest
from app.models.tone import (
    DEFAULT_TONE_PROFILE,
    ToneProfile,
    ToneStrictness,
    ToneStyle,
    ToneVerbosity,
    resolve_tone_profile,
)
from app.services.review_engine import run_review

DIFF = (
    "diff --git a/app/config.py b/app/config.py\n"
    "--- a/app/config.py\n"
    "+++ b/app/config.py\n"
    "@@ -1,1 +1,3 @@\n"
    " import os\n"
    '+API_TOKEN = "abc123"\n'
    "+result = eval(user_input)\n"
)

PERSONAS = [ReviewerPersona.SECURITY, ReviewerPersona.QA]


# ---- Backward compatibility -------------------------------------------------


def test_request_without_tone_fields_is_valid():
    req = ReviewRequest(diff_text=DIFF, selected_personas=PERSONAS)
    assert req.tone_profile is None
    assert req.persona_tone_profiles is None


def test_tone_profile_has_expected_defaults():
    tone = ToneProfile()
    assert tone.style == ToneStyle.DIRECT
    assert tone.strictness == ToneStrictness.MEDIUM
    assert tone.verbosity == ToneVerbosity.NORMAL
    assert tone.custom_instructions is None


# ---- Validation -------------------------------------------------------------


def test_global_tone_profile_validates():
    req = ReviewRequest(
        diff_text=DIFF,
        selected_personas=PERSONAS,
        tone_profile=ToneProfile(
            style=ToneStyle.SUPPORTIVE, verbosity=ToneVerbosity.BRIEF
        ),
    )
    assert req.tone_profile is not None
    assert req.tone_profile.style == ToneStyle.SUPPORTIVE


def test_persona_tone_profiles_validate():
    req = ReviewRequest(
        diff_text=DIFF,
        selected_personas=PERSONAS,
        persona_tone_profiles={
            ReviewerPersona.SECURITY: ToneProfile(style=ToneStyle.STRICT),
        },
    )
    assert req.persona_tone_profiles is not None
    assert req.persona_tone_profiles[ReviewerPersona.SECURITY].style == ToneStyle.STRICT


def test_camelcase_payload_validates_via_model_validate():
    # Mirrors the JSON the frontend sends.
    req = ReviewRequest.model_validate(
        {
            "diffText": DIFF,
            "selectedPersonas": ["security", "qa"],
            "toneProfile": {
                "style": "executive",
                "strictness": "high",
                "verbosity": "detailed",
                "customInstructions": "Reference the style guide.",
            },
            "personaToneProfiles": {"qa": {"style": "educational"}},
        }
    )
    assert req.tone_profile.style == ToneStyle.EXECUTIVE
    assert req.tone_profile.custom_instructions == "Reference the style guide."
    assert req.persona_tone_profiles[ReviewerPersona.QA].style == ToneStyle.EDUCATIONAL


def test_invalid_tone_style_raises_validation_error():
    with pytest.raises(ValidationError):
        ReviewRequest(
            diff_text=DIFF,
            selected_personas=PERSONAS,
            tone_profile={"style": "angry"},
        )


def test_invalid_strictness_raises_validation_error():
    with pytest.raises(ValidationError):
        ReviewRequest.model_validate(
            {
                "diffText": DIFF,
                "selectedPersonas": ["security"],
                "toneProfile": {"strictness": "extreme"},
            }
        )


# ---- Resolution -------------------------------------------------------------


def test_resolution_prefers_persona_override_then_global_then_default():
    global_tone = ToneProfile(style=ToneStyle.SUPPORTIVE)
    security_tone = ToneProfile(style=ToneStyle.STRICT)
    req = ReviewRequest(
        diff_text=DIFF,
        selected_personas=PERSONAS,
        tone_profile=global_tone,
        persona_tone_profiles={ReviewerPersona.SECURITY: security_tone},
    )
    # Per-persona override wins.
    assert resolve_tone_profile(ReviewerPersona.SECURITY, req) == security_tone
    # Falls back to global for personas without an override.
    assert resolve_tone_profile(ReviewerPersona.QA, req) == global_tone


def test_resolution_falls_back_to_default_when_unset():
    req = ReviewRequest(diff_text=DIFF, selected_personas=PERSONAS)
    assert resolve_tone_profile(ReviewerPersona.SECURITY, req) == DEFAULT_TONE_PROFILE


# ---- Detection invariance (the core architectural rule) ---------------------


def _detection_fingerprint(resp):
    return {
        "overall_risk": resp.overall_risk,
        "merge_recommendation": resp.merge_recommendation,
        "findings_by_severity": resp.summary.findings_by_severity,
        "findings": sorted(
            (f.id, f.reviewer, f.severity, f.title) for f in resp.findings
        ),
    }


def test_tone_does_not_change_detection_results():
    baseline = run_review(ReviewRequest(diff_text=DIFF, selected_personas=PERSONAS))

    toned = run_review(
        ReviewRequest(
            diff_text=DIFF,
            selected_personas=PERSONAS,
            tone_profile=ToneProfile(
                style=ToneStyle.STRICT,
                strictness=ToneStrictness.HIGH,
                verbosity=ToneVerbosity.DETAILED,
                custom_instructions="Be very thorough.",
            ),
            persona_tone_profiles={
                ReviewerPersona.QA: ToneProfile(style=ToneStyle.SUPPORTIVE)
            },
        )
    )

    assert _detection_fingerprint(baseline) == _detection_fingerprint(toned)
    # Phase 12 is fully behavior-neutral: the whole response is identical.
    assert baseline.model_dump() == toned.model_dump()
