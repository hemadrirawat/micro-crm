"""The single structured view of an account that both brief providers work from."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..intelligence.analyzer import AccountInsight
from ..models import Contact, Customer, Interaction

MAX_INTERACTIONS_FOR_LLM = 25


@dataclass(frozen=True)
class AccountContext:
    customer: Customer
    contacts: list[Contact]
    interactions: list[Interaction]  # chronological
    insight: AccountInsight
    today: date

    def interaction(self, interaction_id: str) -> Interaction | None:
        return next((i for i in self.interactions if i.id == interaction_id), None)

    def contact(self, contact_id: str | None) -> Contact | None:
        return next((c for c in self.contacts if c.id == contact_id), None)

    def llm_payload(self) -> dict:
        """Only what the model needs. No email addresses or internal ids beyond references."""
        recent = self.interactions[-MAX_INTERACTIONS_FOR_LLM:]
        names = {c.id: c.name for c in self.contacts}
        ins = self.insight
        return {
            "today": self.today.isoformat(),
            "account": {
                "name": self.customer.name,
                "status": self.customer.status.value,
                "created_at": self.customer.created_at.isoformat(),
            },
            "contacts": [{"contact_id": c.id, "name": c.name, "role": c.role} for c in self.contacts],
            "deterministic_assessment": {
                "priority_level": ins.priority_level.value,
                "priority_score": ins.priority_score,
                "on_hold": ins.on_hold,
                "buying_intent": ins.buying_intent,
                "relationship_health": ins.relationship_health,
                "rules_suggested_action": ins.suggested_action.title,
                "signals": [{"label": s.label, "points": s.points, "detail": s.detail,
                             "evidence_ids": s.evidence_ids} for s in ins.signals],
            },
            "interactions": [
                {
                    "id": i.id,
                    "date": i.occurred_at.isoformat(),
                    "type": i.type.value,
                    "contact": names.get(i.contact_id or "", "unknown"),
                    "notes": i.notes,
                }
                for i in recent
            ],
        }
