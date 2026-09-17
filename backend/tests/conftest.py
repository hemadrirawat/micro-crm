from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.config import load_settings
from app.intelligence.analyzer import AccountInsight, analyze_account
from app.models import AccountStatus, Contact, Customer, Interaction, InteractionType
from app.repository import CrmRepository

DEMO_TODAY = date(2026, 9, 1)


@pytest.fixture
def repo(tmp_path: Path) -> CrmRepository:
    return CrmRepository(tmp_path / "crm.db")


@pytest.fixture
def seeded_insights(repo: CrmRepository) -> dict[str, AccountInsight]:
    """Insights for the supplied dataset, keyed by account *name* (for readable assertions)."""
    return {
        c.name: analyze_account(c, repo.list_contacts(c.id), repo.list_interactions(c.id), DEMO_TODAY)
        for c in repo.list_customers()
    }


@pytest.fixture
def settings(tmp_path: Path):
    return replace(load_settings(), database_path=tmp_path / "api.db", today_override="2026-09-01",
                   llm_api_key=None)


def make_account(status: str, notes: list[tuple[str, str, str]], today: date = DEMO_TODAY) -> AccountInsight:
    """Analyze a synthetic account. notes = [(type, iso_date, text), ...]."""
    customer = Customer(id="cust_x", name="Test Practice", status=AccountStatus(status), created_at=date(2026, 1, 1))
    contact = Contact(id="contact_x", customer_id="cust_x", name="Pat Doe", email="pat@x.example", role="Owner")
    interactions = [
        Interaction(id=f"int_x{n}", customer_id="cust_x", contact_id="contact_x",
                    type=InteractionType(kind), occurred_at=date.fromisoformat(day), notes=text, seq=n)
        for n, (kind, day, text) in enumerate(notes)
    ]
    return analyze_account(customer, [contact], interactions, today)
