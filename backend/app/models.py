"""Core CRM domain model: customers, contacts and interactions."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AccountStatus(StrEnum):
    PROSPECT = "prospect"
    CUSTOMER = "customer"


class InteractionType(StrEnum):
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"


class Customer(BaseModel):
    id: str
    name: str
    status: AccountStatus
    created_at: date


class Contact(BaseModel):
    id: str
    customer_id: str
    name: str
    email: str
    role: str

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0]


class Interaction(BaseModel):
    id: str
    customer_id: str
    contact_id: str | None = None
    type: InteractionType
    occurred_at: date
    notes: str
    # "seed" rows come from the supplied dataset; "user" rows were logged in the app
    # (e.g. "Mark follow-up done") and can be undone.
    source: Literal["seed", "user"] = "seed"
    # Insertion order. Interactions only carry a date, so seq breaks same-day ties.
    seq: int = Field(default=0, exclude=True)
