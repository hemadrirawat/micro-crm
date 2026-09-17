"""Constrained output schema for account briefs, shared by the LLM and rules providers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["high", "medium", "low", "unknown", "existing_customer"]
Urgency = Literal["high", "medium", "low"]


class Evidence(BaseModel):
    interaction_id: str
    occurred_at: date
    type: str
    quote: str = Field(max_length=400)


class Recipient(BaseModel):
    contact_id: str
    name: str
    email: str
    role: str


class LlmBriefOutput(BaseModel):
    """Exactly what the model must return. Anything else is rejected before display."""

    summary: str = Field(min_length=20, max_length=800)
    key_facts: list[str] = Field(default_factory=list, max_length=6)
    intent: Intent
    urgency: Urgency
    blockers: list[str] = Field(default_factory=list, max_length=5)
    next_action: str = Field(min_length=5, max_length=220)
    reason: str = Field(min_length=10, max_length=600)
    evidence_ids: list[str] = Field(default_factory=list, max_length=6)
    recipient_contact_id: str | None = None
    message_subject: str = Field(default="", max_length=140)
    suggested_message: str = Field(default="", max_length=1800)
    talking_points: list[str] = Field(default_factory=list, max_length=5)
    insufficient_information: bool = False


class AccountBrief(BaseModel):
    customer_id: str
    summary: str
    key_facts: list[str]
    intent: Intent
    urgency: Urgency
    blockers: list[str]
    next_action: str
    reason: str
    evidence: list[Evidence]
    recipient: Recipient | None
    message_subject: str
    suggested_message: str
    talking_points: list[str]
    insufficient_information: bool
    source: Literal["llm", "rules"]
    model: str | None = None
    fallback_reason: str | None = None
    generated_at: datetime
