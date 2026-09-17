"""API request/response models."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .intelligence.analyzer import AccountInsight
from .models import Contact, Customer, Interaction, InteractionType


class LastInteraction(BaseModel):
    id: str
    type: InteractionType
    occurred_at: date
    notes: str
    contact_name: str | None


class AccountListItem(BaseModel):
    customer: Customer
    primary_contact: Contact | None
    last_interaction: LastInteraction | None
    insight: AccountInsight


class TimelineEntry(Interaction):
    contact_name: str | None = None
    contact_role: str | None = None


class AccountDetail(BaseModel):
    customer: Customer
    contacts: list[Contact]
    insight: AccountInsight
    timeline: list[TimelineEntry]  # newest first


class HealthSummary(BaseModel):
    healthy: int
    watch: int
    at_risk: int


class LevelCounts(BaseModel):
    act_now: int
    this_week: int
    check_in: int
    monitor: int


class ActivityItem(BaseModel):
    interaction: TimelineEntry
    customer_id: str
    customer_name: str


class Dashboard(BaseModel):
    today: date
    level_counts: LevelCounts
    health: HealthSummary
    prospects: int
    customers: int
    needs_attention: list[AccountListItem]
    opportunities: list[AccountListItem]
    on_hold: list[AccountListItem]
    recent_activity: list[ActivityItem]


class SystemInfo(BaseModel):
    status: Literal["ok"]
    ai_mode: Literal["llm", "rules"]
    model: str | None
    today: date


class CompleteFollowUpRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)
    channel: InteractionType = InteractionType.EMAIL

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class LogInteractionRequest(BaseModel):
    type: InteractionType
    notes: str = Field(min_length=3, max_length=2000)
    contact_id: str | None = None
    occurred_at: date | None = None

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Notes must be at least 3 characters")
        return value


class InteractionResult(BaseModel):
    interaction: Interaction
    account: AccountListItem
