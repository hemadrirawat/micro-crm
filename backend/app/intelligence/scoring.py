"""Scoring policy: every weight and threshold lives here so it can be read and tuned in one place.

A priority score is simply the sum of the points of all active signals. Levels come from
thresholds, and a few explicit instructions ("do not push", "no follow-up required",
"we just reached out") cap the level no matter how many points an account has.
"""

from __future__ import annotations

from enum import StrEnum


class PriorityLevel(StrEnum):
    ACT_NOW = "act_now"      # do it today
    THIS_WEEK = "this_week"  # needs attention soon
    CHECK_IN = "check_in"    # relationship opportunity, not urgent
    MONITOR = "monitor"      # nothing to do right now


NEEDS_ATTENTION = (PriorityLevel.ACT_NOW, PriorityLevel.THIS_WEEK)

WEIGHTS: dict[str, int] = {
    # explicit asks from the account
    "follow_up_requested": 35,
    "deadline_approaching": 25,
    "question_awaiting_answer": 20,
    "customer_request_open": 12,
    "unresolved_issue": 25,
    # deal stage & momentum
    "prospect_stage": 10,
    "proposal_awaiting_reply": 25,
    "outreach_awaiting_reply": 15,
    "outreach_gone_cold": 12,
    "demo_not_scheduled": 20,
    "decision_window": 25,
    "decision_upcoming": 12,
    "decision_overdue": 15,
    "internal_follow_up_flag": 15,
    "stalled_note": 10,
    "demo_completed": 10,
    "high_intent": 15,
    "medium_intent": 8,
    "implementation_discussion": 15,
    "expansion_opportunity": 10,
    "customer_expansion": 15,
    "upcoming_timeline": 5,
    "recent_engagement": 10,
    # relationship maintenance
    "prospect_dormant": 10,
    "customer_check_in_due": 12,
    # suppressors
    "waiting_on_them": -20,
    "do_not_push": -45,
    "no_follow_up_needed": -30,
}

# Signals that cap the level at MONITOR regardless of score.
LEVEL_CAPS = {"do_not_push", "no_follow_up_needed", "waiting_on_them"}

THRESHOLDS: list[tuple[int, PriorityLevel]] = [
    (70, PriorityLevel.ACT_NOW),
    (40, PriorityLevel.THIS_WEEK),
    (12, PriorityLevel.CHECK_IN),
]

# Timing rules (days)
STALE_REPLY_DAYS = 5          # outreach unanswered this long becomes a follow-up
COLD_REPLY_DAYS = 30          # after this, it's re-engagement rather than a follow-up
DEADLINE_WINDOW_DAYS = 21     # stated deadlines within this window drive urgency
RECENT_ENGAGEMENT_DAYS = 3
WAITING_ON_THEM_DAYS = 2      # we just reached out; give them room
DORMANT_PROSPECT_DAYS = 30
CUSTOMER_CHECK_IN_DAYS = 60
HOLD_DEFAULT_DAYS = 60        # a "do not push" note without a date expires after this

HIGH_INTENT_POINTS = 5
MEDIUM_INTENT_POINTS = 2


def level_for(score: int, capped: bool) -> PriorityLevel:
    if capped:
        return PriorityLevel.MONITOR
    for threshold, level in THRESHOLDS:
        if score >= threshold:
            return level
    return PriorityLevel.MONITOR


def urgency_for(level: PriorityLevel) -> str:
    return {
        PriorityLevel.ACT_NOW: "high",
        PriorityLevel.THIS_WEEK: "medium",
    }.get(level, "low")
