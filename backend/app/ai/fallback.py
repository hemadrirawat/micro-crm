"""Deterministic brief provider. Always available; used when no LLM is configured or it fails.

Everything here is composed from the rules engine's insight plus quoted interaction notes,
so it cannot state a fact that isn't in the history.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..intelligence import text as t
from ..intelligence.analyzer import AccountInsight
from .context import AccountContext
from .schema import AccountBrief, Evidence, Recipient

SIGN_OFF = "\n\nBest,"


def build_rules_brief(ctx: AccountContext, fallback_reason: str | None = None) -> AccountBrief:
    ins = ctx.insight
    action = ins.suggested_action
    contact = ctx.contact(action.contact_id)
    subject, message = _draft_message(ctx, ins, contact.name if contact else None)

    return AccountBrief(
        customer_id=ctx.customer.id,
        summary=ins.summary,
        key_facts=[f.text for f in ins.key_facts],
        intent=ins.buying_intent,
        urgency=ins.urgency,  # type: ignore[arg-type]
        blockers=[b.text for b in ins.blockers],
        next_action=action.title,
        reason=_reason(ins),
        evidence=build_evidence(ctx, _evidence_ids(ins)),
        recipient=_recipient(contact),
        message_subject=subject,
        suggested_message=message,
        talking_points=_talking_points(ins),
        insufficient_information=not ctx.interactions,
        source="rules",
        fallback_reason=fallback_reason,
        generated_at=datetime.now(UTC),
    )


def build_evidence(ctx: AccountContext, ids: list[str]) -> list[Evidence]:
    evidence = []
    for interaction_id in dict.fromkeys(ids):
        item = ctx.interaction(interaction_id)
        if item:
            evidence.append(Evidence(interaction_id=item.id, occurred_at=item.occurred_at,
                                     type=item.type.value, quote=item.notes))
    return sorted(evidence, key=lambda e: e.occurred_at)


def _recipient(contact) -> Recipient | None:
    if contact is None:
        return None
    return Recipient(contact_id=contact.id, name=contact.name, email=contact.email, role=contact.role)


def _evidence_ids(ins: AccountInsight) -> list[str]:
    key = ins.suggested_action.signal_key
    primary = next((s for s in ins.signals if s.key == key), None)
    ids = list(primary.evidence_ids) if primary else []
    for signal in ins.signals:
        if len(ids) >= 4:
            break
        if signal.key != key and signal.points > 0:
            ids.extend(i for i in signal.evidence_ids[-1:] if i not in ids)
    return ids[:4]


def _reason(ins: AccountInsight) -> str:
    supporting = [s.label.lower() for s in ins.signals
                  if s.points > 0 and s.key not in ("prospect_stage", ins.suggested_action.signal_key)][:3]
    reason = ins.reason
    if supporting and ins.priority_level.value != "monitor":
        reason += f" Also: {', '.join(supporting)}."
    return reason


def _talking_points(ins: AccountInsight) -> list[str]:
    points = [f.text for f in ins.key_facts[:3]]
    points += [f"Address: {b.text}" for b in ins.blockers[:2]]
    return points[:5]


def _proposal_scope(ctx: AccountContext) -> str:
    """' for the 3 locations' when the history states what the proposal covered, else ''."""
    for item in reversed(ctx.interactions):
        if "proposal" in item.notes.lower() and (m := t.LOCATION_COUNT.search(item.notes)):
            return f" for the {m.group(1)} locations"
    return ""


def _draft_message(ctx: AccountContext, ins: AccountInsight, contact_name: str | None) -> tuple[str, str]:
    """Signal-specific outreach templates. They reference only dates and asks from the history."""
    key = ins.suggested_action.signal_key
    if key in (None, "no_follow_up_needed", "waiting_on_them") or contact_name is None:
        return "", ""

    first = t.first_name(contact_name)
    signal = next((s for s in ins.signals if s.key == key), None)
    item = ctx.interaction(signal.evidence_ids[-1]) if signal and signal.evidence_ids else None
    sent = t.fmt_date(item.occurred_at) if item else "recently"
    note = item.notes if item else ""
    hi = f"Hi {first},\n\n"

    if key == "follow_up_requested":
        topic = t.FOLLOW_UP_TOPIC.search(note)
        about = f" to talk through {topic.group(1).strip()}" if topic else ""
        return ("Scheduling our follow-up",
                hi + f"Thanks for reaching out. I'd be glad to set up a short follow-up{about}. "
                "What times work for you this week? I'll send an invite as soon as I hear back." + SIGN_OFF)

    if key in ("deadline_approaching", "question_awaiting_answer", "customer_request_open"):
        clause = next((c for s in t.sentences(note) if (c := t.question_clause(s))), None)
        topic = f"{clause[0]} {clause[1]}" if clause else "your recent question"
        if key == "customer_request_open":
            return ("Re: your question",
                    hi + f"Thanks for asking {topic}. I'm checking on the latest and will come back to you "
                    "with a clear answer. In the meantime, let me know if there's anything else your team needs."
                    + SIGN_OFF)
        return ("Re: your timeline",
                hi + f"Thanks for your patience on your question {topic}. I want to make sure we give you a "
                "firm answer. Do you have 15 minutes this week to confirm the plan together?" + SIGN_OFF)

    if key == "proposal_awaiting_reply":
        scope = _proposal_scope(ctx)
        return ("Checking in on the proposal",
                hi + f"I wanted to check in on the proposal{scope} I sent on {sent}. Happy to answer any questions "
                "that came up during your review, or walk through it together on a quick call. "
                "What would be most helpful?" + SIGN_OFF)

    if key in ("outreach_awaiting_reply", "internal_follow_up_flag"):
        return ("Following up",
                hi + f"Following up on my note from {sent}. Is there anything I can clarify or help with "
                "as you think through next steps?" + SIGN_OFF)

    if key in ("outreach_gone_cold", "prospect_dormant"):
        return ("Checking back in",
                hi + f"It's been a little while since we last connected ({sent}), so I wanted to check back in. "
                "Is this still something you're exploring? If anything has changed on your side, "
                "I'm happy to answer questions or pick things up whenever it suits you." + SIGN_OFF)

    if key == "demo_not_scheduled":
        return ("Finding a time for your demo",
                hi + f"Following up on the demo link I sent on {sent}. If it's easier, I'm happy to find a "
                "time for you. Would a 20-minute walkthrough later this week or early next week work?" + SIGN_OFF)

    if key in ("decision_window", "decision_upcoming", "decision_overdue"):
        month = t.DECISION_MONTH.search(note)
        when = f" in {month.group(1).capitalize()}" if month else ""
        return ("Anything you need before deciding?",
                hi + f"You mentioned you expected to make a decision{when}, so I wanted to check in. "
                "Is there anything else you need from us to make that call, or any open questions "
                "I can help with?" + SIGN_OFF)

    if key == "customer_expansion":
        return ("Planning for your growth",
                hi + "You mentioned your practice may be growing. I'd love to hear how those plans are shaping "
                "up and make sure your setup is ready when the time comes. Open to a quick chat?" + SIGN_OFF)

    if key == "customer_check_in_due":
        return ("Quick check-in",
                hi + "It's been a little while since we last talked, so I wanted to check in. How is everything "
                "working for your team? Is there anything we could improve?" + SIGN_OFF)

    if key == "unresolved_issue":
        return ("Checking on the issue you reported",
                hi + "I wanted to check in on the issue you reported. Is it still happening? "
                "I'd like to make sure it's fully resolved." + SIGN_OFF)

    if key == "do_not_push":
        return ("For later: light check-in",
                hi + "I hope your planning went well. Whenever the timing is right, I'm happy to help with "
                "anything your team needs to move forward. No rush on our side." + SIGN_OFF)

    return "", ""
