"""API and data behaviour through the HTTP layer."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings))


def test_system_reports_rules_mode_without_api_key(client):
    body = client.get("/api/system").json()
    assert body == {"status": "ok", "ai_mode": "rules", "model": None, "today": "2026-09-01"}


def test_seed_data_loaded_and_dashboard_prioritises(client):
    body = client.get("/api/dashboard").json()
    assert body["prospects"] + body["customers"] == 12
    names = [a["customer"]["name"] for a in body["needs_attention"]]
    assert set(names[:3]) == {"Parkview Dental Studio", "Central Avenue Dentistry", "Northstar Dental Group"}
    assert "Evergreen Dental Partners" not in names
    assert len(body["recent_activity"]) == 8
    assert body["recent_activity"][0]["interaction"]["id"] == "int_056"


@pytest.mark.parametrize("view,expected", [("all", 12), ("prospects", 7), ("customers", 5), ("needs_attention", 6)])
def test_account_filters(client, view, expected):
    assert len(client.get("/api/accounts", params={"view": view}).json()) == expected


def test_search_matches_account_and_contact_names(client):
    assert [a["customer"]["name"] for a in client.get("/api/accounts", params={"q": "parkview"}).json()] == [
        "Parkview Dental Studio"]
    assert [a["customer"]["id"] for a in client.get("/api/accounts", params={"q": "sarah"}).json()] == ["cust_001"]
    assert client.get("/api/accounts", params={"q": "zzz"}).json() == []


def test_sort_by_last_interaction(client):
    items = client.get("/api/accounts", params={"sort": "last_interaction"}).json()
    dates = [a["insight"]["last_interaction_at"] for a in items]
    assert dates == sorted(dates, reverse=True)


def test_invalid_query_params_rejected(client):
    assert client.get("/api/accounts", params={"view": "bogus"}).status_code == 422


def test_account_detail_has_timeline_newest_first(client):
    body = client.get("/api/accounts/cust_001").json()
    assert [c["name"] for c in body["contacts"]] == ["Sarah Mitchell", "Daniel Kim"]
    assert body["timeline"][0]["id"] == "int_005"
    assert body["timeline"][0]["contact_name"] == "Sarah Mitchell"


def test_unknown_account_is_404(client):
    assert client.get("/api/accounts/cust_999").status_code == 404
    assert client.post("/api/accounts/cust_999/brief").status_code == 404


def test_mark_follow_up_done_updates_state_and_can_be_undone(client):
    result = client.post("/api/accounts/cust_012/follow-ups/complete", json={"note": "Booked a call."})
    assert result.status_code == 200
    body = result.json()
    assert body["interaction"]["source"] == "user"
    assert body["account"]["insight"]["priority_level"] == "monitor"

    names = [a["customer"]["name"] for a in client.get("/api/accounts", params={"view": "needs_attention"}).json()]
    assert "Central Avenue Dentistry" not in names

    undone = client.delete(f"/api/interactions/{body['interaction']['id']}")
    assert undone.json()["insight"]["priority_level"] == "act_now"


def test_seed_history_cannot_be_deleted(client):
    assert client.delete("/api/interactions/int_001").status_code == 403


def test_log_interaction_validates_input(client):
    assert client.post("/api/accounts/cust_001/interactions", json={"type": "email", "notes": "  "}).status_code == 422
    wrong_contact = {"type": "call", "notes": "Talked to someone", "contact_id": "contact_010"}
    assert client.post("/api/accounts/cust_001/interactions", json=wrong_contact).status_code == 422
    future = {"type": "call", "notes": "Future call", "occurred_at": "2027-01-01"}
    assert client.post("/api/accounts/cust_001/interactions", json=future).status_code == 422


def test_logging_a_reply_rescores_the_account(client):
    body = client.post("/api/accounts/cust_001/interactions", json={
        "type": "email", "contact_id": "contact_001",
        "notes": "Sarah replied that partners approved and asked if we can schedule a kickoff call.",
    }).json()
    assert body["account"]["insight"]["suggested_action"]["signal_key"] == "follow_up_requested"


def test_reset_restores_seed(client):
    client.post("/api/accounts/cust_012/follow-ups/complete", json={})
    assert client.post("/api/demo/reset").status_code == 204
    assert len(client.get("/api/accounts/cust_012").json()["timeline"]) == 6
