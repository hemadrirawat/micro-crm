"""Relationship intelligence: turns an account's raw history into an explainable insight.

`analyze_account` is a pure function of (customer, contacts, interactions, today), which
keeps it trivially testable and lets the AI layer reuse the exact same structured view.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from ..models import AccountStatus, Contact, Customer, Interaction
from . import scoring
from . import text as t
from .scoring import WEIGHTS, PriorityLevel

Health = Literal["healthy", "watch", "at_risk"]
Intent = Literal["high", "medium", "low", "unknown", "existing_customer"]


class Signal(BaseModel):
    key: str
    label: str
    points: int
    detail: str
    evidence_ids: list[str]


class Fact(BaseModel):
    category: str
    text: str
    evidence_id: str
    occurred_at: date


class Blocker(BaseModel):
    text: str
    evidence_id: str


class SuggestedAction(BaseModel):
    title: str
    signal_key: str | None
    contact_id: str | None
    contact_name: str | None


class FollowUp(BaseModel):
    title: str
    detail: str
    signal_key: str
    evidence_ids: list[str]


class AccountInsight(BaseModel):
    customer_id: str
    last_interaction_at: date | None
    days_since_last_interaction: int | None
    last_interaction_id: str | None
    interaction_count: int
    priority_score: int
    priority_level: PriorityLevel
    on_hold: bool
    open_follow_up: bool
    follow_ups: list[FollowUp]
    buying_intent: Intent
    urgency: str
    relationship_health: Health
    reason: str
    suggested_action: SuggestedAction
    signals: list[Signal]
    blockers: list[Blocker]
    key_facts: list[Fact]
    summary: str


@dataclass
class _Found:
    """A detected signal before it is turned into the public model."""

    key: str
    label: str
    detail: str
    evidence: list[Interaction]
    action: str | None = None
    contact_id: str | None = None

    @property
    def points(self) -> int:
        return WEIGHTS[self.key]


# Order used to pick the primary driver among equally weighted signals.
ACTIONABLE_ORDER = [
    "follow_up_requested", "deadline_approaching", "unresolved_issue", "proposal_awaiting_reply",
    "question_awaiting_answer", "demo_not_scheduled", "decision_window", "decision_overdue",
    "internal_follow_up_flag", "outreach_awaiting_reply", "customer_expansion",
    "customer_request_open", "decision_upcoming",
    "outreach_gone_cold", "customer_check_in_due", "expansion_opportunity", "prospect_dormant",
]


@dataclass
class _Context:
    customer: Customer
    contacts: dict[str, Contact]
    touches: list[t.Touch]
    today: date
    found: list[_Found] = field(default_factory=list)

    @property
    def is_prospect(self) -> bool:
        return self.customer.status == AccountStatus.PROSPECT

    def name_of(self, contact_id: str | None) -> str:
        contact = self.contacts.get(contact_id or "")
        return t.first_name(contact.name if contact else None)

    def ours_after(self, index: int) -> bool:
        return any(x.ours for x in self.touches[index + 1:])

    def theirs_after(self, index: int) -> bool:
        return any(x.theirs for x in self.touches[index + 1:])

    def days_ago(self, d: date) -> int:
        return (self.today - d).days

    def add(self, key: str, label: str, detail: str, evidence: list[Interaction],
            action: str | None = None, contact_id: str | None = None) -> None:
        if not any(f.key == key for f in self.found):
            self.found.append(_Found(key, label, detail, evidence, action, contact_id))


def analyze_account(
    customer: Customer,
    contacts: list[Contact],
    interactions: list[Interaction],
    today: date,
) -> AccountInsight:
    ordered = sorted((i for i in interactions if i.occurred_at <= today),
                     key=lambda i: (i.occurred_at, i.seq))
    ctx = _Context(customer, {c.id: c for c in contacts},
                   [t.classify(i, n) for n, i in enumerate(ordered)], today)

    if ctx.is_prospect:
        ctx.add("prospect_stage", "Open prospect", "Prospects need active nurturing to close.", [])

    _detect_asks(ctx)
    _detect_outreach_state(ctx)
    _detect_timing(ctx)
    _detect_momentum(ctx)
    _detect_issues(ctx)
    _detect_dormancy(ctx)
    _detect_internal_notes(ctx)
    hold_until = _detect_suppressors(ctx)

    score = max(0, sum(f.points for f in ctx.found))
    capped = any(f.key in scoring.LEVEL_CAPS for f in ctx.found)
    level = scoring.level_for(score, capped)
    on_hold = any(f.key == "do_not_push" for f in ctx.found)

    driver = _primary_driver(ctx)
    action = _suggested_action(ctx, driver, level, hold_until)
    follow_ups = [] if capped else _follow_ups(ctx)
    last = _last_contact(ctx)
    facts = _key_facts(ctx)
    intent = _buying_intent(ctx)
    health = _health(ctx)
    reason = _reason(ctx, driver, level)

    return AccountInsight(
        customer_id=customer.id,
        last_interaction_at=last.occurred_at if last else None,
        days_since_last_interaction=ctx.days_ago(last.occurred_at) if last else None,
        last_interaction_id=last.id if last else None,
        interaction_count=len(ordered),
        priority_score=score,
        priority_level=level,
        on_hold=on_hold,
        open_follow_up=bool(follow_ups) and level != PriorityLevel.MONITOR,
        follow_ups=follow_ups,
        buying_intent=intent,
        urgency=scoring.urgency_for(level),
        relationship_health=health,
        reason=reason,
        suggested_action=action,
        signals=sorted(
            (Signal(key=f.key, label=f.label, points=f.points, detail=f.detail,
                    evidence_ids=[e.id for e in f.evidence]) for f in ctx.found),
            key=lambda s: -abs(s.points),
        ),
        blockers=_blockers(ctx),
        key_facts=facts,
        summary=_summary(ctx, intent, facts, driver, level, hold_until),
    )


# --- detectors -----------------------------------------------------------------------

def _detect_asks(ctx: _Context) -> None:
    """Explicit follow-up requests and questions the account is still waiting on."""
    open_questions: list[tuple[t.Touch, str]] = []
    for touch in ctx.touches:
        for sentence in touch.their_sentences():
            if t.FOLLOW_UP_REQUEST.search(sentence):
                if not ctx.ours_after(touch.index):
                    who = ctx.name_of(touch.interaction.contact_id)
                    topic = t.FOLLOW_UP_TOPIC.search(sentence)
                    action = f"Book the follow-up {who} asked for"
                    if topic:
                        action += f" to discuss {topic.group(1).strip()}"
                    ctx.add("follow_up_requested", "Asked for a follow-up", sentence,
                            [touch.interaction], action, touch.interaction.contact_id)
            elif t.QUESTION.search(sentence) and not ctx.ours_after(touch.index):
                open_questions.append((touch, sentence))

    if not open_questions:
        return
    touch, sentence = open_questions[-1]
    who = ctx.name_of(touch.interaction.contact_id)
    action = _answer_action(who, sentence)
    evidence = [q.interaction for q, _ in open_questions]
    if ctx.is_prospect:
        ctx.add("question_awaiting_answer", "Question awaiting answer", sentence, evidence,
                action, touch.interaction.contact_id)
    else:
        ctx.add("customer_request_open", "Customer request to answer", sentence, evidence,
                action, touch.interaction.contact_id)


def _answer_action(who: str, sentence: str) -> str:
    clause = t.question_clause(sentence)
    if clause is None:
        return f"Answer {who}'s open question"
    connector, rest = clause
    if connector == "whether":
        return f"Get back to {who} on whether {rest}"
    if connector == "about":
        return f"Get back to {who} about {rest}"
    return f"Send {who} {rest}"


def _detect_outreach_state(ctx: _Context) -> None:
    """Things we sent (proposal, pricing, demo link…) that haven't had a reply."""
    for touch in reversed(ctx.touches):
        if touch.is_note or not touch.ours:
            continue
        if touch.theirs and touch.interaction.type.value in ("call", "meeting"):
            return  # the latest exchange was a live conversation: nothing is pending
        outbound = [s for s in touch.sentences if t.OUTBOUND_START.search(s)]
        if not outbound or ctx.theirs_after(touch.index):
            return
        item = touch.interaction
        days = ctx.days_ago(item.occurred_at)
        who = ctx.name_of(item.contact_id)
        sent = t.fmt_date(item.occurred_at)

        if any(t.DEMO_LINK_SENT.search(s) for s in outbound):
            if days >= scoring.STALE_REPLY_DAYS:
                ctx.add("demo_not_scheduled", "Demo not booked",
                        f"Demo link sent {sent}; no demo booked in {days} days.", [item],
                        f"Re-send the demo link to {who} with two suggested times", item.contact_id)
            return

        kind = next((k for k, p in t.DELIVERABLE_KINDS for s in outbound if p.search(s)), None)
        if kind is None:
            # Generic outreach only expects a reply from prospects, and not when the
            # same exchange already contains their response ("Checked in. Megan said…").
            if touch.theirs or not ctx.is_prospect:
                return
            kind = "last message"
        if days < scoring.STALE_REPLY_DAYS:
            if days <= scoring.WAITING_ON_THEM_DAYS and not touch.theirs:
                ctx.add("waiting_on_them", "Waiting on their reply",
                        f"You followed up on {sent}. Give them a few days to reply.", [item],
                        f"Wait for {who} to reply to your {kind}", item.contact_id)
            return
        if days > scoring.COLD_REPLY_DAYS:
            ctx.add("outreach_gone_cold", "Gone quiet after outreach",
                    f"{kind.capitalize()} sent {sent}; no reply in {days} days.", [item],
                    f"Re-engage {who}: {kind} went out {sent} with no reply since", item.contact_id)
        elif kind == "proposal":
            ctx.add("proposal_awaiting_reply", "Proposal awaiting reply",
                    f"Proposal sent {sent}; no reply in {days} days.", [item],
                    f"Follow up with {who} on the proposal sent {sent}", item.contact_id)
        else:
            ctx.add("outreach_awaiting_reply", "Awaiting reply",
                    f"{kind.capitalize()} sent {sent}; no reply in {days} days.", [item],
                    f"Follow up with {who} on the {kind} sent {sent}", item.contact_id)
        return


def _detect_timing(ctx: _Context) -> None:
    for touch in ctx.touches:
        item = touch.interaction
        who = ctx.name_of(item.contact_id)
        for sentence in touch.their_sentences():
            if m := t.DEADLINE.search(sentence):
                month, day = t.month_number(m.group(1)), int(m.group(2))
                deadline = date(t.infer_year(month, item.occurred_at), month, day)
                days_left = (deadline - ctx.today).days
                open_q = t.QUESTION.search(sentence) and not ctx.ours_after(touch.index)
                if 0 <= days_left <= scoring.DEADLINE_WINDOW_DAYS or (days_left < 0 and open_q):
                    when = f"{days_left} days away" if days_left >= 0 else "already passed"
                    clause = t.question_clause(sentence) if open_q else None
                    detail = (f"{who} asked {clause[0]} {clause[1]}. Still unanswered, deadline {when}."
                              if clause else f"{who} mentioned a {t.fmt_date(deadline)} deadline ({when}).")
                    action = _answer_action(who, sentence) if open_q else None
                    if action and action.startswith("Get back to"):
                        action = action.replace("Get back to", "Confirm with", 1).replace(" on whether", " whether", 1)
                    ctx.add("deadline_approaching", "Deadline approaching", detail, [item],
                            action or f"Confirm the {t.fmt_date(deadline)} timeline with {who}", item.contact_id)

            if m := t.DECISION_MONTH.search(sentence):
                month = t.month_number(m.group(1))
                year = t.infer_year(month, item.occurred_at)
                start, end = date(year, month, 1), t.end_of_month(year, month)
                label = m.group(1).capitalize()
                if start <= ctx.today <= end:
                    ctx.add("decision_window", "Decision due this month",
                            f"{who} expects to decide in {label}, which is now.", [item],
                            f"Check in with {who} ahead of their {label} decision", item.contact_id)
                elif start - timedelta(days=31) <= ctx.today < start:
                    ctx.add("decision_upcoming", "Decision coming up",
                            f"{who} expects to decide in {label}.", [item],
                            f"Check in with {who} ahead of their {label} decision", item.contact_id)
                elif ctx.today > end and not ctx.theirs_after(touch.index):
                    ctx.add("decision_overdue", "Decision date passed",
                            f"{who} expected to decide in {label}; nothing recorded since.", [item],
                            f"Ask {who} where the {label} decision landed", item.contact_id)

            if ctx.is_prospect and (m := t.MONTH_MENTION.search(sentence)) and t.EXPANSION.search(sentence):
                month = t.month_number(m.group(1))
                target = date(t.infer_year(month, item.occurred_at), month, 1)
                if ctx.today <= t.end_of_month(target.year, target.month):
                    ctx.add("upcoming_timeline", "Upcoming milestone", sentence, [item])


def _detect_momentum(ctx: _Context) -> None:
    last_theirs = next((x for x in reversed(ctx.touches) if x.theirs), None)
    last_ours = next((x for x in reversed(ctx.touches) if x.ours), None)
    if last_theirs and ctx.days_ago(last_theirs.interaction.occurred_at) <= scoring.RECENT_ENGAGEMENT_DAYS:
        if last_ours is None or last_ours.index <= last_theirs.index:
            ctx.add("recent_engagement", "Recently engaged",
                    f"Heard from them {t.fmt_date(last_theirs.interaction.occurred_at)}.",
                    [last_theirs.interaction])

    for touch in ctx.touches:
        item = touch.interaction
        if ctx.is_prospect and t.DEMO_DONE.search(item.notes):
            ctx.add("demo_completed", "Demo completed", f"Demo held {t.fmt_date(item.occurred_at)}.", [item])
        recent = ctx.days_ago(item.occurred_at) <= 30
        scan = touch.sentences if touch.is_note else tuple(touch.their_sentences())
        for sentence in scan:
            if recent and t.IMPLEMENTATION.search(sentence):
                ctx.add("implementation_discussion", "Talking implementation", sentence, [item])
            if not touch.is_note and t.EXPANSION.search(sentence):
                if ctx.is_prospect:
                    ctx.add("expansion_opportunity", "Multi-location opportunity", sentence, [item])
                else:
                    ctx.add("customer_expansion", "Expansion opportunity", sentence, [item],
                            f"Ask {ctx.name_of(item.contact_id)} about their expansion plans",
                            item.contact_id)

    if ctx.is_prospect:
        points, evidence = _intent_points(ctx)
        if points >= scoring.HIGH_INTENT_POINTS:
            ctx.add("high_intent", "High buying intent", "Strong buying signals across recent conversations.", evidence)
        elif points >= scoring.MEDIUM_INTENT_POINTS:
            ctx.add("medium_intent", "Some buying interest", "Showed interest, not yet strong commitment.", evidence)


def _intent_points(ctx: _Context) -> tuple[int, list[Interaction]]:
    points, evidence = 0, []
    for touch in ctx.touches:
        scan = touch.sentences if touch.is_note else touch.their_sentences()
        gained = sum(w for s in scan for p, w in t.INTENT_PHRASES if p.search(s))
        if gained:
            points += gained
            evidence.append(touch.interaction)
    return points, evidence


def _detect_issues(ctx: _Context) -> None:
    for touch in ctx.touches:
        for sentence in touch.their_sentences():
            if t.ISSUE.search(sentence) and not t.RESOLVED.search(sentence) and not _resolved_later(ctx, touch):
                who = ctx.name_of(touch.interaction.contact_id)
                ctx.add("unresolved_issue", "Unresolved issue", sentence, [touch.interaction],
                        f"Check with {who} on the issue they reported", touch.interaction.contact_id)


def _resolved_later(ctx: _Context, touch: t.Touch) -> bool:
    return any(t.RESOLVED.search(s) for x in ctx.touches[touch.index + 1:] for s in x.sentences)


def _detect_dormancy(ctx: _Context) -> None:
    last = _last_contact(ctx)
    if last is None:
        return
    days = ctx.days_ago(last.occurred_at)
    who = ctx.name_of(_main_contact_id(ctx))
    if ctx.is_prospect and days > scoring.DORMANT_PROSPECT_DAYS:
        ctx.add("prospect_dormant", "Gone quiet", f"No contact for {days} days.", [last],
                f"Re-engage {who} with a short check-in", _main_contact_id(ctx))
    elif not ctx.is_prospect and days > scoring.CUSTOMER_CHECK_IN_DAYS:
        ctx.add("customer_check_in_due", "Check-in opportunity",
                f"No contact for {days} days.", [last],
                f"Send {who} a quick check-in", _main_contact_id(ctx))


def _detect_internal_notes(ctx: _Context) -> None:
    """Our own notes: 'need to confirm X', 'no response yet' — until someone acts on them."""
    for touch in ctx.touches:
        if not touch.is_note:
            continue
        item = touch.interaction
        who = ctx.name_of(item.contact_id)
        for sentence in touch.sentences:
            if t.INTERNAL_FLAG.search(sentence) and not ctx.ours_after(touch.index):
                need = t.NEED_TO.search(sentence)
                action = (f"{need.group(1)[0].upper()}{need.group(1)[1:]} with {who}" if need
                          else f"Follow up with {who}")
                ctx.add("internal_follow_up_flag", "Flagged in your notes", sentence, [item],
                        action, item.contact_id)
            if t.STALL.search(sentence) and not ctx.ours_after(touch.index) and not ctx.theirs_after(touch.index):
                ctx.add("stalled_note", "Noted as stalled", sentence, [item])


def _detect_suppressors(ctx: _Context) -> str | None:
    """Explicit instructions that should keep an account off the urgent list."""
    hold_until: str | None = None
    for touch in ctx.touches:
        item = touch.interaction
        for sentence in touch.sentences:
            if t.HOLD.search(sentence) and not _new_asks_after(ctx, touch):
                m = t.HOLD_UNTIL_MONTH.search(sentence)
                if m:
                    month = t.month_number(m.group(1))
                    expires = t.end_of_month(t.infer_year(month, item.occurred_at), month)
                    label = m.group(1).capitalize()
                else:
                    expires = item.occurred_at + timedelta(days=scoring.HOLD_DEFAULT_DAYS)
                    label = None
                if ctx.today <= expires:
                    hold_until = label or hold_until
                    ctx.add("do_not_push", "Hold: don't push", sentence, [item])
            if t.NO_FOLLOW_UP.search(sentence) and not _new_asks_after(ctx, touch):
                ctx.add("no_follow_up_needed", "No follow-up needed", sentence, [item])
    return hold_until


def _new_asks_after(ctx: _Context, touch: t.Touch) -> bool:
    """A later question, request or issue from the account overrides an old 'leave it' note."""
    patterns = (t.FOLLOW_UP_REQUEST, t.QUESTION, t.ISSUE)
    return any(p.search(s) for x in ctx.touches[touch.index + 1:]
               for s in x.their_sentences() for p in patterns)


# --- derived views ----------------------------------------------------------------------

def _last_contact(ctx: _Context) -> Interaction | None:
    """Most recent real touchpoint; internal notes only count if nothing else exists."""
    real = [x.interaction for x in ctx.touches if not x.is_note]
    if real:
        return real[-1]
    return ctx.touches[-1].interaction if ctx.touches else None


def _main_contact_id(ctx: _Context) -> str | None:
    for touch in reversed(ctx.touches):
        if touch.interaction.contact_id:
            return touch.interaction.contact_id
    return next(iter(ctx.contacts), None)


def _primary_driver(ctx: _Context) -> _Found | None:
    actionable = [f for f in ctx.found if f.key in ACTIONABLE_ORDER and f.action]
    if not actionable:
        return None
    return max(actionable, key=lambda f: (f.points, -ACTIONABLE_ORDER.index(f.key)))


def _suggested_action(ctx: _Context, driver: _Found | None, level: PriorityLevel,
                      hold_until: str | None) -> SuggestedAction:
    def make(title: str, key: str | None, contact_id: str | None) -> SuggestedAction:
        contact = ctx.contacts.get(contact_id or "")
        return SuggestedAction(title=title, signal_key=key, contact_id=contact_id,
                               contact_name=contact.name if contact else None)

    by_key = {f.key: f for f in ctx.found}
    if hold := by_key.get("do_not_push"):
        who = ctx.name_of(hold.evidence[0].contact_id)
        when = f"after their {hold_until} planning" if hold_until else "until the hold lifts"
        return make(f"Hold outreach; check in with {who} {when}", "do_not_push", hold.evidence[0].contact_id)
    if "no_follow_up_needed" in by_key:
        return make("No action needed. Reopen only if the issue returns", "no_follow_up_needed", None)
    if waiting := by_key.get("waiting_on_them"):
        return make(waiting.action or "Wait for their reply", "waiting_on_them", waiting.contact_id)
    if driver:
        return make(driver.action or driver.label, driver.key, driver.contact_id)
    if ctx.is_prospect and level != PriorityLevel.MONITOR:
        who_id = _main_contact_id(ctx)
        return make(f"Propose a clear next step to {ctx.name_of(who_id)}", None, who_id)
    return make("No action needed right now", None, None)


def _follow_ups(ctx: _Context) -> list[FollowUp]:
    items = [f for f in ctx.found if f.key in ACTIONABLE_ORDER and f.action]
    items.sort(key=lambda f: (-f.points, ACTIONABLE_ORDER.index(f.key)))
    seen: set[str] = set()
    result = []
    for f in items:
        if f.action in seen:
            continue
        seen.add(f.action)
        result.append(FollowUp(title=f.action, detail=f.detail, signal_key=f.key,
                               evidence_ids=[e.id for e in f.evidence]))
    return result


def _reason(ctx: _Context, driver: _Found | None, level: PriorityLevel) -> str:
    by_key = {f.key: f for f in ctx.found}
    for key in ("do_not_push", "no_follow_up_needed", "waiting_on_them"):
        if key in by_key:
            return by_key[key].detail
    if driver:
        return driver.detail
    if not ctx.is_prospect:
        positive = [s for x in ctx.touches for s in x.their_sentences() if t.POSITIVE.search(s)]
        if positive:
            return positive[-1]
    return "No open asks or risks detected." if level == PriorityLevel.MONITOR else "Active prospect."


def _buying_intent(ctx: _Context) -> Intent:
    if not ctx.is_prospect:
        return "existing_customer"
    points, _ = _intent_points(ctx)
    if points >= scoring.HIGH_INTENT_POINTS:
        return "high"
    if points >= scoring.MEDIUM_INTENT_POINTS:
        return "medium"
    return "low" if points > 0 else "unknown"


def _health(ctx: _Context) -> Health:
    keys = {f.key for f in ctx.found}
    if "unresolved_issue" in keys or "outreach_gone_cold" in keys:
        return "at_risk"
    if ctx.is_prospect and "prospect_dormant" in keys and "do_not_push" not in keys:
        return "at_risk"
    watch = {"proposal_awaiting_reply", "outreach_awaiting_reply", "demo_not_scheduled",
             "customer_check_in_due", "decision_overdue", "stalled_note"}
    if "no_follow_up_needed" in keys:
        watch.discard("customer_check_in_due")
    if keys & watch or _blockers(ctx):
        return "watch"
    return "healthy"


def _blockers(ctx: _Context) -> list[Blocker]:
    result: list[Blocker] = []
    for touch in ctx.touches:
        for sentence in touch.their_sentences():
            if t.OBJECTION.search(sentence) and not _objection_resolved(ctx, touch):
                result.append(Blocker(text=sentence, evidence_id=touch.interaction.id))
            elif t.APPROVAL.search(sentence) or t.BUDGET.search(sentence):
                result.append(Blocker(text=sentence, evidence_id=touch.interaction.id))
    return result


def _objection_resolved(ctx: _Context, touch: t.Touch) -> bool:
    return any(t.RESOLVED.search(s) for x in ctx.touches[touch.index + 1:] for s in x.their_sentences())


def _key_facts(ctx: _Context, limit: int = 6) -> list[Fact]:
    """Relationship facts, quoted from the notes so they are grounded by construction."""
    candidates: list[tuple[int, Fact]] = []
    seen: set[str] = set()
    for touch in reversed(ctx.touches):  # newest first
        if touch.is_note:
            continue
        for sentence in touch.their_sentences():
            if len(sentence.split()) < 5 or sentence in seen:
                continue
            for rank, (category, pattern) in enumerate(t.FACT_RULES):
                if pattern.search(sentence):
                    seen.add(sentence)
                    candidates.append((rank, Fact(category=category, text=sentence,
                                                  evidence_id=touch.interaction.id,
                                                  occurred_at=touch.interaction.occurred_at)))
                    break
    candidates.sort(key=lambda c: c[0])
    chosen = [f for _, f in candidates[:limit]]
    return sorted(chosen, key=lambda f: f.occurred_at, reverse=True)


SUMMARY_STATE_KEYS = [
    "follow_up_requested", "deadline_approaching", "proposal_awaiting_reply", "demo_not_scheduled",
    "decision_window", "decision_overdue", "outreach_awaiting_reply", "outreach_gone_cold",
    "unresolved_issue", "question_awaiting_answer", "customer_request_open", "customer_expansion",
]


STARTS_WITH_PRONOUN = re.compile(r"^(she|he|they|it)\b", re.IGNORECASE)


def _article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"


def _latest_deliverable(ctx: _Context) -> tuple[str, Interaction] | None:
    """The most recent proposal/pricing/contract/reference we sent, if any."""
    for touch in reversed(ctx.touches):
        if touch.is_note or not touch.ours:
            continue
        for s in touch.sentences:
            if t.OUTBOUND_START.search(s):
                kind = next((k for k, p in t.DELIVERABLE_KINDS if p.search(s)), None)
                if kind:
                    return kind, touch.interaction
    return None


def _summary(ctx: _Context, intent: Intent, facts: list[Fact], driver: _Found | None,
             level: PriorityLevel, hold_until: str | None) -> str:
    """A short, template-based account brief built only from detected signals and quoted notes."""
    name = ctx.customer.name
    if not ctx.touches:
        return f"{name} has no recorded interactions yet."

    parts: list[str] = []
    locations = next((f"{m.group(1)} locations" for x in ctx.touches for s in x.their_sentences()
                      if (m := t.LOCATION_COUNT.search(s))), None)
    scale = f" ({locations})" if locations else ""
    if ctx.is_prospect:
        adjective = {"high": "high-intent", "medium": "interested", "low": "early-stage"}.get(intent)
        noun = f"{adjective} prospect" if adjective else "prospect"
        parts.append(f"{name} is {_article(noun)} {noun}{scale}.")
    else:
        parts.append(f"{name} is an existing customer{scale}.")

    by_key = {f.key: f for f in ctx.found}
    state = next((by_key[k] for k in SUMMARY_STATE_KEYS if k in by_key), None)
    if state is None and "no_follow_up_needed" not in by_key:
        state = by_key.get("prospect_dormant") or by_key.get("customer_check_in_due")
    state_ids = {e.id for e in state.evidence} if state else set()

    # One "what they care about" fact and one "context" fact, quoted from notes.
    for categories in (("Needs", "Sentiment"), ("Scale", "Timeline", "Decision")):
        # Quotes that open with a bare pronoun read ambiguously out of context, so skip them here.
        fact = next((f for f in facts if f.category in categories and not STARTS_WITH_PRONOUN.match(f.text)
                     and f.evidence_id not in state_ids and f.text not in parts), None)
        if fact:
            parts.append(fact.text)
    sent = _latest_deliverable(ctx)
    if sent and sent[1].id not in state_ids:
        parts.append(f"{sent[0].capitalize()} {'were' if sent[0].endswith('details') else 'was'} "
                     f"sent {t.fmt_date(sent[1].occurred_at)}.")
    stated = bool(state)
    if state:
        parts.append(state.detail)

    if "do_not_push" in by_key:
        parts.append(f"They asked for space{f' until {hold_until}' if hold_until else ''}, so hold outreach.")
    elif "no_follow_up_needed" in by_key:
        parts.append("The earlier issue was resolved and no follow-up is required.")
    elif level == PriorityLevel.MONITOR and not stated:
        parts.append("Nothing needs your attention right now.")
    return " ".join(parts)
