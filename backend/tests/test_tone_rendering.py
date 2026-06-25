"""Tests for deterministic tone rendering in the mock provider (Phase 13A).

Tone rewords presentation text only. These tests prove wording changes while the
detection outputs (ids, severity, reviewer, file path, hunk reference, confidence,
overall risk, merge recommendation, diff stats) stay invariant.
"""

from app.models.enums import ReviewerPersona
from app.models.review import ReviewRequest
from app.models.tone import (
    ToneProfile,
    ToneStrictness,
    ToneStyle,
    ToneVerbosity,
)
from app.services.providers.mock_provider import MockReviewProvider
from app.services.review_engine import run_review

# A diff that triggers several personas: security (eval/secret), backend (broad
# except), QA (prod code, no tests), architect (spans areas via two file kinds).
DIFF = (
    "diff --git a/app/api.py b/app/api.py\n"
    "--- a/app/api.py\n"
    "+++ b/app/api.py\n"
    "@@ -1,2 +1,8 @@\n"
    " import os\n"
    '+API_TOKEN = "abc123"\n'
    "+result = eval(user_input)\n"
    "+try:\n"
    "+    do_work()\n"
    "+except Exception:\n"
    "+    handle()\n"
    "diff --git a/ui/App.tsx b/ui/App.tsx\n"
    "--- a/ui/App.tsx\n"
    "+++ b/ui/App.tsx\n"
    "@@ -1,1 +1,2 @@\n"
    " const x = 1;\n"
    "+el.innerHTML = userInput;\n"
)

PERSONAS = [
    ReviewerPersona.SECURITY,
    ReviewerPersona.BACKEND,
    ReviewerPersona.QA,
    ReviewerPersona.FRONTEND,
]


def _req(**kwargs) -> ReviewRequest:
    return ReviewRequest(diff_text=DIFF, selected_personas=PERSONAS, **kwargs)


def _detection_view(resp):
    return {
        "overall_risk": resp.overall_risk,
        "merge_recommendation": resp.merge_recommendation,
        "diff_stats": resp.diff_stats.model_dump(),
        "findings": sorted(
            (
                f.id,
                f.reviewer,
                f.severity,
                f.title,
                f.file_path,
                (f.hunk_reference.model_dump() if f.hunk_reference else None),
                f.confidence,
            )
            for f in resp.findings
        ),
    }


# 1. Default / no-tone output is unchanged vs explicitly passing the default tone.
def test_default_tone_is_a_noop():
    no_tone = run_review(_req())
    default_tone = run_review(_req(tone_profile=ToneProfile()))
    assert no_tone.model_dump() == default_tone.model_dump()


# 2. Tone changes wording for at least one finding.
def test_tone_changes_wording_of_a_finding():
    baseline = run_review(_req())
    toned = run_review(
        _req(tone_profile=ToneProfile(style=ToneStyle.EXECUTIVE))
    )
    base_recs = {f.id: f.recommendation for f in baseline.findings}
    toned_recs = {f.id: f.recommendation for f in toned.findings}
    assert any(base_recs[fid] != toned_recs[fid] for fid in base_recs)
    assert all(r.startswith("Business impact: ") for r in toned_recs.values())


# 3. Tone does not change any detection output.
def test_tone_does_not_change_detection_outputs():
    baseline = run_review(_req())
    toned = run_review(
        _req(
            tone_profile=ToneProfile(
                style=ToneStyle.STRICT,
                strictness=ToneStrictness.HIGH,
                verbosity=ToneVerbosity.DETAILED,
                custom_instructions="Follow the style guide.",
            )
        )
    )
    assert _detection_view(baseline) == _detection_view(toned)


# 4. Per-persona override affects only that persona's wording.
def test_per_persona_override_affects_only_that_persona():
    baseline = run_review(_req())
    toned = run_review(
        _req(
            persona_tone_profiles={
                ReviewerPersona.SECURITY: ToneProfile(style=ToneStyle.STRICT)
            }
        )
    )
    base_by_id = {f.id: f for f in baseline.findings}
    for f in toned.findings:
        if f.reviewer == ReviewerPersona.SECURITY:
            assert f.recommendation.startswith("Required before merge: ")
        else:
            assert f.recommendation == base_by_id[f.id].recommendation


# 5. Global tone affects all selected personas unless overridden.
def test_global_tone_affects_all_unless_overridden():
    toned = run_review(
        _req(
            tone_profile=ToneProfile(style=ToneStyle.SUPPORTIVE),
            persona_tone_profiles={
                ReviewerPersona.SECURITY: ToneProfile(style=ToneStyle.STRICT)
            },
        )
    )
    for f in toned.findings:
        if f.reviewer == ReviewerPersona.SECURITY:
            assert f.recommendation.startswith("Required before merge: ")
        else:
            assert f.recommendation.startswith("To keep things smooth: ")


# 6. Strictness affects wording/emphasis but not severity/risk.
def test_strictness_affects_wording_not_severity():
    low = run_review(_req(tone_profile=ToneProfile(strictness=ToneStrictness.LOW)))
    high = run_review(_req(tone_profile=ToneProfile(strictness=ToneStrictness.HIGH)))

    low_recs = {f.id: f.recommendation for f in low.findings}
    high_recs = {f.id: f.recommendation for f in high.findings}
    assert low_recs != high_recs
    assert all(r.endswith("(lower priority)") for r in low_recs.values())
    assert all(
        r.endswith("This should be resolved before merge.")
        for r in high_recs.values()
    )

    # Severity and overall risk are untouched.
    assert {f.id: f.severity for f in low.findings} == {
        f.id: f.severity for f in high.findings
    }
    assert low.overall_risk == high.overall_risk


# 7. Verbosity affects explanation detail/length but not finding count.
def test_verbosity_affects_detail_not_count():
    brief = run_review(_req(tone_profile=ToneProfile(verbosity=ToneVerbosity.BRIEF)))
    detailed = run_review(
        _req(tone_profile=ToneProfile(verbosity=ToneVerbosity.DETAILED))
    )

    assert len(brief.findings) == len(detailed.findings)

    brief_exp = {f.id: f.explanation for f in brief.findings}
    detailed_exp = {f.id: f.explanation for f in detailed.findings}
    # At least one explanation is strictly longer under "detailed".
    assert any(
        len(detailed_exp[fid]) > len(brief_exp[fid]) for fid in brief_exp
    )
    assert all("reviewer; verify against" in e for e in detailed_exp.values())


# 8. Each ToneStyle produces a deterministic, distinct rendering.
def test_each_style_has_distinct_visible_effect():
    provider = MockReviewProvider()
    from app.services.diff_parser import parse_diff

    parsed = parse_diff(DIFF)
    rendered_recs: set[str] = set()
    for style in ToneStyle:
        reviews = provider.review(
            parsed,
            [ReviewerPersona.SECURITY],
            tone_profiles={ReviewerPersona.SECURITY: ToneProfile(style=style)},
        )
        rec = reviews[0].findings[0].recommendation
        rendered_recs.add(rec)
    # All six styles yield distinct recommendation wording.
    assert len(rendered_recs) == len(list(ToneStyle))


# Determinism: same input twice -> identical output.
def test_tone_rendering_is_deterministic():
    req = _req(tone_profile=ToneProfile(style=ToneStyle.CURIOUS))
    assert run_review(req).model_dump() == run_review(req).model_dump()
