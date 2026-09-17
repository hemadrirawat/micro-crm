"""Relationship priority scoring against the supplied dataset and synthetic accounts."""

from __future__ import annotations

from datetime import date

from app.intelligence.scoring import NEEDS_ATTENTION, PriorityLevel

from .conftest import make_account


def rank(insights):
    return sorted(insights, key=lambda name: -insights[name].priority_score)


def test_hot_prospects_are_act_now(seeded_insights):
    for name in ["Central Avenue Dentistry", "Parkview Dental Studio", "Northstar Dental Group",
                 "Riverbend Orthodontics"]:
        assert seeded_insights[name].priority_level == PriorityLevel.ACT_NOW, name


def test_decision_this_month_needs_attention(seeded_insights):
    brightsmile = seeded_insights["BrightSmile Dental"]
    assert brightsmile.priority_level in NEEDS_ATTENTION
    assert "decision_window" in {s.key for s in brightsmile.signals}


def test_do_not_push_suppresses_priority(seeded_insights):
    evergreen = seeded_insights["Evergreen Dental Partners"]
    assert evergreen.on_hold
    assert evergreen.priority_level == PriorityLevel.MONITOR
    assert evergreen.follow_ups == []
    assert "Hold" in evergreen.suggested_action.title
    assert any("approval" in b.text for b in evergreen.blockers)


def test_resolved_issue_with_no_follow_up_note_is_not_an_alert(seeded_insights):
    oak = seeded_insights["Oak & Pine Family Dental"]
    keys = {s.key for s in oak.signals}
    assert oak.priority_level == PriorityLevel.MONITOR
    assert "unresolved_issue" not in keys
    assert "no_follow_up_needed" in keys
    assert oak.relationship_health == "healthy"


def test_happy_customers_never_outrank_urgent_prospects(seeded_insights):
    urgent = [n for n, i in seeded_insights.items() if i.priority_level in NEEDS_ATTENTION]
    customers = ["Maple Grove Orthodontics", "Willow Creek Dental", "Greenfield Pediatrics",
                 "Sunrise Pediatric Dentistry"]
    lowest_urgent = min(seeded_insights[n].priority_score for n in urgent)
    for name in customers:
        assert seeded_insights[name].priority_score < lowest_urgent, name
    assert seeded_insights["Maple Grove Orthodontics"].priority_level == PriorityLevel.MONITOR
    assert seeded_insights["Willow Creek Dental"].priority_level == PriorityLevel.CHECK_IN


def test_customer_question_is_a_request_not_a_sales_follow_up(seeded_insights):
    greenfield = seeded_insights["Greenfield Pediatrics"]
    assert greenfield.suggested_action.signal_key == "customer_request_open"
    assert "SMS" in greenfield.suggested_action.title
    assert greenfield.priority_level == PriorityLevel.CHECK_IN


def test_stale_pricing_is_re_engagement(seeded_insights):
    lakeside = seeded_insights["Lakeside Dental Care"]
    assert lakeside.suggested_action.signal_key == "outreach_gone_cold"
    assert lakeside.relationship_health == "at_risk"


def test_score_is_sum_of_signal_points(seeded_insights):
    for insight in seeded_insights.values():
        assert insight.priority_score == max(0, sum(s.points for s in insight.signals))


# --- synthetic accounts: the rules are not tied to the sample data -------------------

def test_new_account_with_explicit_request_is_prioritised():
    insight = make_account("prospect", [
        ("email", "2026-08-30", "Pat requested a demo after a referral."),
        ("meeting", "2026-08-31", "Demo went well. Pat asked for a proposal for two locations."),
        ("email", "2026-08-31", "Pat asked if we can set up a call on Friday to go over onboarding."),
    ])
    assert insight.priority_level == PriorityLevel.ACT_NOW
    assert insight.suggested_action.signal_key == "follow_up_requested"
    assert insight.buying_intent == "high"


def test_unresolved_customer_issue_is_flagged_and_resolution_clears_it():
    open_issue = make_account("customer", [
        ("email", "2026-08-28", "Pat reported that call summaries show the wrong patient names."),
        ("call", "2026-08-29", "Pat said the transcription issue is causing problems at the front desk."),
    ])
    assert "unresolved_issue" in {s.key for s in open_issue.signals}
    assert open_issue.relationship_health == "at_risk"

    resolved = make_account("customer", [
        ("call", "2026-08-20", "Pat said the transcription issue is causing problems at the front desk."),
        ("email", "2026-08-25", "Pat confirmed the problem is resolved."),
    ])
    assert "unresolved_issue" not in {s.key for s in resolved.signals}


def test_hold_expires_after_the_stated_month():
    notes = [
        ("call", "2026-06-10", "Pat said budget is delayed until July."),
        ("note", "2026-06-10", "Do not push before July."),
    ]
    during = make_account("prospect", notes, today=date(2026, 7, 5))
    after = make_account("prospect", notes, today=date(2026, 8, 5))
    assert during.on_hold and during.priority_level == PriorityLevel.MONITOR
    assert not after.on_hold


def test_new_request_overrides_old_no_follow_up_note():
    insight = make_account("customer", [
        ("note", "2026-07-01", "No additional follow-up required."),
        ("email", "2026-08-31", "Pat asked if we can schedule a call about adding a new location."),
    ])
    assert "no_follow_up_needed" not in {s.key for s in insight.signals}
    assert insight.priority_level in NEEDS_ATTENTION


def test_account_without_interactions_is_handled():
    insight = make_account("prospect", [])
    assert insight.last_interaction_at is None
    assert insight.priority_level == PriorityLevel.MONITOR
    assert "no recorded interactions" in insight.summary
