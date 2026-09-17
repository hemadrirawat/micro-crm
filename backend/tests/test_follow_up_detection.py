"""Identifying follow-up opportunities and clearing them once handled."""

from __future__ import annotations

from .conftest import make_account


def test_question_is_open_until_we_respond():
    asked = make_account("prospect", [
        ("email", "2026-08-25", "Pat asked whether the system supports Spanish."),
    ])
    assert "question_awaiting_answer" in {s.key for s in asked.signals}
    assert asked.suggested_action.title == "Get back to Pat on whether the system supports Spanish"

    answered = make_account("prospect", [
        ("email", "2026-08-25", "Pat asked whether the system supports Spanish."),
        ("email", "2026-08-26", "Sent Spanish configuration options."),
    ])
    assert "question_awaiting_answer" not in {s.key for s in answered.signals}


def test_internal_notes_are_not_treated_as_replies():
    insight = make_account("prospect", [
        ("email", "2026-08-20", "Pat asked whether onboarding can be completed before September 15."),
        ("note", "2026-08-20", "Need to confirm onboarding timeline."),
    ])
    keys = {s.key for s in insight.signals}
    assert {"question_awaiting_answer", "deadline_approaching", "internal_follow_up_flag"} <= keys
    assert insight.suggested_action.signal_key == "deadline_approaching"
    assert insight.suggested_action.title.startswith("Confirm with Pat whether onboarding")


def test_unanswered_proposal_becomes_follow_up_after_grace_period():
    fresh = make_account("prospect", [("email", "2026-08-31", "Sent proposal.")])
    assert "proposal_awaiting_reply" not in {s.key for s in fresh.signals}
    assert "waiting_on_them" in {s.key for s in fresh.signals}

    stale = make_account("prospect", [("email", "2026-08-20", "Sent proposal.")])
    assert stale.suggested_action.signal_key == "proposal_awaiting_reply"
    assert stale.open_follow_up


def test_demo_link_without_booking_is_detected():
    insight = make_account("prospect", [
        ("call", "2026-08-01", "Pat is interested in reducing front desk workload."),
        ("email", "2026-08-02", "Sent demo scheduling link."),
    ])
    assert insight.suggested_action.signal_key == "demo_not_scheduled"


def test_logged_follow_up_clears_the_queue_entry():
    before = make_account("prospect", [
        ("email", "2026-08-31", "Pat asked if we can schedule a short follow-up to discuss implementation."),
    ])
    assert before.open_follow_up
    after = make_account("prospect", [
        ("email", "2026-08-31", "Pat asked if we can schedule a short follow-up to discuss implementation."),
        ("email", "2026-09-01", "Follow-up completed: booked a call for Thursday."),
    ])
    assert not after.open_follow_up
    assert after.suggested_action.signal_key == "waiting_on_them"


def test_quiet_customer_gets_check_in_opportunity():
    insight = make_account("customer", [
        ("call", "2026-03-01", "Pat said the system has reduced missed calls noticeably."),
    ])
    assert insight.suggested_action.signal_key == "customer_check_in_due"
    assert insight.priority_level.value == "check_in"
