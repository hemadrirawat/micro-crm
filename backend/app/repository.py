"""SQLite-backed data access. The supplied CSV dataset is seeded on first start."""

from __future__ import annotations

import csv
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from .models import Contact, Customer, Interaction, InteractionType

SEED_DIR = Path(__file__).resolve().parent / "seed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prospect', 'customer')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interactions (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    contact_id TEXT REFERENCES contacts(id),
    type TEXT NOT NULL CHECK (type IN ('email', 'call', 'meeting', 'note')),
    occurred_at TEXT NOT NULL,
    notes TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'seed'
);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interactions(customer_id);
"""


class NotFoundError(LookupError):
    pass


class CrmRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        if self._is_empty():
            self.reset_to_seed()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _is_empty(self) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0

    # --- seeding -----------------------------------------------------------------

    def reset_to_seed(self) -> None:
        """Replace all data with the supplied sample dataset."""
        with self._connect() as conn:
            conn.execute("DELETE FROM interactions")
            conn.execute("DELETE FROM contacts")
            conn.execute("DELETE FROM customers")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'interactions'")
            for row in _read_csv("customers.csv"):
                conn.execute(
                    "INSERT INTO customers (id, name, status, created_at) VALUES (?, ?, ?, ?)",
                    (row["id"], row["name"], row["status"], row["created_at"]),
                )
            for row in _read_csv("contacts.csv"):
                conn.execute(
                    "INSERT INTO contacts (id, customer_id, name, email, role) VALUES (?, ?, ?, ?, ?)",
                    (row["id"], row["customer_id"], row["name"], row["email"], row["role"]),
                )
            for row in _read_csv("interactions.csv"):
                conn.execute(
                    "INSERT INTO interactions (id, customer_id, contact_id, type, occurred_at, notes, source)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'seed')",
                    (row["id"], row["customer_id"], row["contact_id"] or None, row["type"],
                     row["occurred_at"], row["notes"]),
                )

    # --- reads -------------------------------------------------------------------

    def list_customers(self) -> list[Customer]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
        return [Customer(**dict(r)) for r in rows]

    def get_customer(self, customer_id: str) -> Customer:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Account {customer_id} not found")
        return Customer(**dict(row))

    def list_contacts(self, customer_id: str | None = None) -> list[Contact]:
        query, params = "SELECT * FROM contacts", ()
        if customer_id:
            query, params = query + " WHERE customer_id = ?", (customer_id,)
        with self._connect() as conn:
            rows = conn.execute(query + " ORDER BY id", params).fetchall()
        return [Contact(**dict(r)) for r in rows]

    def list_interactions(self, customer_id: str | None = None) -> list[Interaction]:
        """Interactions in chronological order (oldest first)."""
        query, params = "SELECT * FROM interactions", ()
        if customer_id:
            query, params = query + " WHERE customer_id = ?", (customer_id,)
        with self._connect() as conn:
            rows = conn.execute(query + " ORDER BY occurred_at, seq", params).fetchall()
        return [Interaction(**dict(r)) for r in rows]

    # --- writes ------------------------------------------------------------------

    def add_interaction(
        self,
        customer_id: str,
        type_: InteractionType,
        notes: str,
        occurred_at: date,
        contact_id: str | None = None,
    ) -> Interaction:
        self.get_customer(customer_id)
        if contact_id is not None:
            valid = {c.id for c in self.list_contacts(customer_id)}
            if contact_id not in valid:
                raise ValueError(f"Contact {contact_id} does not belong to {customer_id}")
        interaction_id = f"int_user_{uuid.uuid4().hex[:10]}"
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO interactions (id, customer_id, contact_id, type, occurred_at, notes, source)"
                " VALUES (?, ?, ?, ?, ?, ?, 'user')",
                (interaction_id, customer_id, contact_id, type_.value, occurred_at.isoformat(), notes),
            )
            row = conn.execute("SELECT * FROM interactions WHERE seq = ?", (cur.lastrowid,)).fetchone()
        return Interaction(**dict(row))

    def delete_user_interaction(self, interaction_id: str) -> Interaction:
        """Only interactions logged in the app can be removed; seed history is immutable."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM interactions WHERE id = ?", (interaction_id,)).fetchone()
            if row is None:
                raise NotFoundError(f"Interaction {interaction_id} not found")
            if row["source"] != "user":
                raise PermissionError("Imported interaction history cannot be deleted")
            conn.execute("DELETE FROM interactions WHERE id = ?", (interaction_id,))
        return Interaction(**dict(row))


def _read_csv(name: str) -> list[dict[str, str]]:
    with open(SEED_DIR / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
