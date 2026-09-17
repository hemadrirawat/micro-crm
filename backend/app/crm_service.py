"""Application service: combines storage, relationship intelligence and AI briefs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Literal

from .ai.context import AccountContext
from .ai.schema import AccountBrief
from .ai.service import BriefService
from .intelligence.analyzer import analyze_account
from .intelligence.scoring import NEEDS_ATTENTION, PriorityLevel
from .models import AccountStatus, Contact, Customer, Interaction, InteractionType
from .repository import CrmRepository
from .schemas import (
    AccountDetail,
    AccountListItem,
    ActivityItem,
    Dashboard,
    HealthSummary,
    LastInteraction,
    LevelCounts,
    TimelineEntry,
)

View = Literal["all", "prospects", "customers", "needs_attention"]
Sort = Literal["priority", "last_interaction", "status", "name"]

LEVEL_RANK = {PriorityLevel.ACT_NOW: 0, PriorityLevel.THIS_WEEK: 1,
              PriorityLevel.CHECK_IN: 2, PriorityLevel.MONITOR: 3}


class CrmService:
    def __init__(self, repo: CrmRepository, briefs: BriefService, today: Callable[[], date]):
        self.repo = repo
        self.briefs = briefs
        self.today = today

    # --- queries ---------------------------------------------------------------------

    def list_accounts(self, view: View = "all", query: str = "", sort: Sort = "priority") -> list[AccountListItem]:
        items = self._all_items()
        if view == "prospects":
            items = [i for i in items if i.customer.status == AccountStatus.PROSPECT]
        elif view == "customers":
            items = [i for i in items if i.customer.status == AccountStatus.CUSTOMER]
        elif view == "needs_attention":
            items = [i for i in items if i.insight.priority_level in NEEDS_ATTENTION]

        if q := query.strip().lower():
            items = [i for i in items if _matches(i, q)]

        if sort == "last_interaction":
            items.sort(key=lambda i: i.insight.last_interaction_at or date.min, reverse=True)
        elif sort == "status":
            items.sort(key=lambda i: (i.customer.status.value, _priority_key(i)))
        elif sort == "name":
            items.sort(key=lambda i: i.customer.name.lower())
        else:
            items.sort(key=_priority_key)
        return items

    def get_account(self, customer_id: str) -> AccountDetail:
        ctx = self._context(customer_id)
        by_id = {c.id: c for c in ctx.contacts}
        timeline = [_timeline_entry(i, by_id) for i in reversed(ctx.interactions)]
        return AccountDetail(customer=ctx.customer, contacts=ctx.contacts, insight=ctx.insight, timeline=timeline)

    def get_brief(self, customer_id: str, refresh: bool = False) -> AccountBrief:
        return self.briefs.brief(self._context(customer_id), refresh=refresh)

    def dashboard(self) -> Dashboard:
        items = sorted(self._all_items(), key=_priority_key)
        levels = [i.insight.priority_level for i in items]
        health = [i.insight.relationship_health for i in items]
        customers = {c.id: c for c in self.repo.list_customers()}
        contacts = {c.id: c for c in self.repo.list_contacts()}
        recent = sorted(self.repo.list_interactions(), key=lambda i: (i.occurred_at, i.seq), reverse=True)
        recent = [i for i in recent if i.occurred_at <= self.today()][:8]
        return Dashboard(
            today=self.today(),
            level_counts=LevelCounts(**{lvl.value: levels.count(lvl) for lvl in PriorityLevel}),
            health=HealthSummary(healthy=health.count("healthy"), watch=health.count("watch"),
                                 at_risk=health.count("at_risk")),
            prospects=sum(1 for i in items if i.customer.status == AccountStatus.PROSPECT),
            customers=sum(1 for i in items if i.customer.status == AccountStatus.CUSTOMER),
            needs_attention=[i for i in items if i.insight.priority_level in NEEDS_ATTENTION],
            opportunities=[i for i in items if i.insight.priority_level == PriorityLevel.CHECK_IN],
            on_hold=[i for i in items if i.insight.priority_level == PriorityLevel.MONITOR],
            recent_activity=[
                ActivityItem(interaction=_timeline_entry(i, contacts), customer_id=i.customer_id,
                             customer_name=customers[i.customer_id].name)
                for i in recent
            ],
        )

    # --- commands --------------------------------------------------------------------

    def complete_follow_up(self, customer_id: str, note: str | None,
                           channel: InteractionType) -> tuple[Interaction, AccountListItem]:
        """Mock of 'I did the follow-up': recorded locally as an outbound interaction."""
        ctx = self._context(customer_id)
        action = ctx.insight.suggested_action
        contact_id = action.contact_id or (ctx.contacts[0].id if ctx.contacts else None)
        text = f"Follow-up completed: {action.title}."
        if note:
            text += f" {note}"
        interaction = self.repo.add_interaction(customer_id, channel, text, self.today(), contact_id)
        return interaction, self._item(customer_id)

    def log_interaction(self, customer_id: str, type_: InteractionType, notes: str,
                        contact_id: str | None, occurred_at: date | None) -> tuple[Interaction, AccountListItem]:
        when = occurred_at or self.today()
        if when > self.today():
            raise ValueError("Interactions cannot be logged in the future")
        interaction = self.repo.add_interaction(customer_id, type_, notes, when, contact_id)
        return interaction, self._item(customer_id)

    def undo_interaction(self, interaction_id: str) -> AccountListItem:
        removed = self.repo.delete_user_interaction(interaction_id)
        return self._item(removed.customer_id)

    # --- internals -------------------------------------------------------------------

    def _context(self, customer_id: str) -> AccountContext:
        customer = self.repo.get_customer(customer_id)
        contacts = self.repo.list_contacts(customer_id)
        interactions = [i for i in self.repo.list_interactions(customer_id) if i.occurred_at <= self.today()]
        insight = analyze_account(customer, contacts, interactions, self.today())
        return AccountContext(customer, contacts, interactions, insight, self.today())

    def _item(self, customer_id: str) -> AccountListItem:
        customer = self.repo.get_customer(customer_id)
        return self._build_item(customer, self.repo.list_contacts(customer_id),
                                self.repo.list_interactions(customer_id))

    def _all_items(self) -> list[AccountListItem]:
        contacts = self.repo.list_contacts()
        interactions = self.repo.list_interactions()
        return [
            self._build_item(c, [x for x in contacts if x.customer_id == c.id],
                             [x for x in interactions if x.customer_id == c.id])
            for c in self.repo.list_customers()
        ]

    def _build_item(self, customer: Customer, contacts: list[Contact],
                    interactions: list[Interaction]) -> AccountListItem:
        interactions = [i for i in interactions if i.occurred_at <= self.today()]
        insight = analyze_account(customer, contacts, interactions, self.today())
        by_id = {c.id: c for c in contacts}
        last = next((i for i in interactions if i.id == insight.last_interaction_id), None)
        primary = by_id.get(insight.suggested_action.contact_id or "") or (contacts[0] if contacts else None)
        return AccountListItem(
            customer=customer,
            primary_contact=primary,
            last_interaction=LastInteraction(
                id=last.id, type=last.type, occurred_at=last.occurred_at, notes=last.notes,
                contact_name=by_id[last.contact_id].name if last.contact_id in by_id else None,
            ) if last else None,
            insight=insight,
        )


def _priority_key(item: AccountListItem) -> tuple:
    return (LEVEL_RANK[item.insight.priority_level], -item.insight.priority_score, item.customer.name)


def _matches(item: AccountListItem, q: str) -> bool:
    haystack = [item.customer.name, item.insight.reason, item.insight.suggested_action.title]
    if item.primary_contact:
        haystack += [item.primary_contact.name, item.primary_contact.email]
    return any(q in h.lower() for h in haystack)


def _timeline_entry(interaction: Interaction, contacts: dict[str, Contact]) -> TimelineEntry:
    contact = contacts.get(interaction.contact_id or "")
    return TimelineEntry(**interaction.model_dump(), seq=interaction.seq,
                         contact_name=contact.name if contact else None,
                         contact_role=contact.role if contact else None)
