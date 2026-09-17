"""AI boundary: deterministic fallback, LLM output validation, and graceful degradation."""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.llm import LlmBriefProvider, LlmError
from app.ai.service import BriefService
from app.crm_service import CrmService
from app.main import create_app
from app.models import InteractionType

from .conftest import DEMO_TODAY

VALID_OUTPUT = {
    "summary": "Northstar Dental Group is a 3-location prospect waiting on a proposal decision.",
    "key_facts": ["Asked for a proposal for 3 locations"],
    "intent": "high",
    "urgency": "high",
    "blockers": [],
    "next_action": "Follow up with Sarah about the 3-location proposal.",
    "reason": "Proposal was sent Aug 23 and no reply has been recorded.",
    "evidence_ids": ["int_004", "int_005"],
    "recipient_contact_id": "contact_001",
    "message_subject": "Proposal check-in",
    "suggested_message": "Hi Sarah, checking in on the proposal for the three locations.",
    "talking_points": [],
    "insufficient_information": False,
}


def provider_returning(content: str | None, status: int = 200) -> LlmBriefProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        # Interaction notes must be framed as data inside the user message.
        assert "<account_data>" in body["messages"][1]["content"]
        assert "not instructions" in body["messages"][0]["content"].lower()
        assert "@" not in body["messages"][1]["content"], "emails should not be sent to the LLM"
        payload = {"choices": [{"message": {"content": content}}]} if content is not None else {}
        return httpx.Response(status, json=payload)

    return LlmBriefProvider("test-key", "https://llm.test/v1", "test-model", 5,
                            transport=httpx.MockTransport(handler))


def service_with(repo, llm, today):
    return CrmService(repo, BriefService(llm), lambda: today)


def test_rules_brief_is_grounded_in_history(repo):
    crm = service_with(repo, None, DEMO_TODAY)
    notes = {i.id: i.notes for i in repo.list_interactions()}
    for customer in repo.list_customers():
        brief = crm.get_brief(customer.id)
        assert brief.source == "rules"
        assert brief.next_action
        for ev in brief.evidence:
            assert ev.quote == notes[ev.interaction_id]
        for fact in brief.key_facts:
            assert any(fact in n for n in notes.values()), fact


def test_rules_outreach_uses_details_from_history(repo):
    crm = service_with(repo, None, DEMO_TODAY)
    brief = crm.get_brief("cust_001")
    assert brief.recipient and brief.recipient.name == "Sarah Mitchell"
    assert "proposal for the 3 locations" in brief.suggested_message
    assert "Aug 23" in brief.suggested_message


def test_rules_brief_respects_hold_and_no_action(repo):
    crm = service_with(repo, None, DEMO_TODAY)
    oak = crm.get_brief("cust_004")
    assert oak.suggested_message == ""
    assert oak.next_action.startswith("No action needed")
    evergreen = crm.get_brief("cust_011")
    assert evergreen.next_action.startswith("Hold outreach")


def test_valid_llm_output_is_used(repo):
    crm = service_with(repo, provider_returning(json.dumps(VALID_OUTPUT)), DEMO_TODAY)
    brief = crm.get_brief("cust_001")
    assert brief.source == "llm"
    assert brief.model == "test-model"
    assert [e.interaction_id for e in brief.evidence] == ["int_004", "int_005"]
    assert brief.evidence[0].quote.startswith("Sent proposal")  # quotes come from our DB
    assert brief.recipient and brief.recipient.email == "sarah@northstardental.example"


@pytest.mark.parametrize("mutation,why", [
    ({"evidence_ids": ["int_999"]}, "unknown interaction"),
    ({"evidence_ids": []}, "no evidence"),
    ({"reason": "They have 40 locations and a $5000 budget."}, "invented numbers"),
    ({"recipient_contact_id": "contact_010"}, "contact from another account"),
    ({"urgency": "critical"}, "schema violation"),
])
def test_ungrounded_llm_output_falls_back_to_rules(repo, mutation, why):
    crm = service_with(repo, provider_returning(json.dumps({**VALID_OUTPUT, **mutation})), DEMO_TODAY)
    brief = crm.get_brief("cust_001")
    assert brief.source == "rules", why
    assert brief.fallback_reason


@pytest.mark.parametrize("content,status", [("not json at all", 200), (None, 500), ("```json\n{}\n```", 200)])
def test_llm_failures_fall_back(repo, content, status):
    crm = service_with(repo, provider_returning(content, status), DEMO_TODAY)
    assert crm.get_brief("cust_003").source == "rules"


def test_fenced_json_is_accepted(repo):
    fenced = f"```json\n{json.dumps(VALID_OUTPUT)}\n```"
    crm = service_with(repo, provider_returning(fenced), DEMO_TODAY)
    assert crm.get_brief("cust_001").source == "llm"


def test_briefs_are_cached_until_history_changes(repo):

    class CountingProvider:
        model = "counting"

        def __init__(self):
            self.calls = 0

        def generate(self, ctx):
            self.calls += 1
            raise LlmError("offline")

    llm = CountingProvider()
    crm = service_with(repo, llm, DEMO_TODAY)
    crm.get_brief("cust_001")
    crm.get_brief("cust_001")
    assert llm.calls == 1
    crm.get_brief("cust_001", refresh=True)
    assert llm.calls == 2
    crm.complete_follow_up("cust_001", None, InteractionType.EMAIL)
    crm.get_brief("cust_001")
    assert llm.calls == 3


def test_api_key_never_reaches_the_client(settings):
    app = create_app(replace(settings, llm_api_key="sk-secret-value"),
                     llm=provider_returning(json.dumps(VALID_OUTPUT)))
    client = TestClient(app)
    for response in (client.get("/api/system"), client.post("/api/accounts/cust_001/brief")):
        assert "sk-secret-value" not in response.text
    assert client.get("/api/system").json()["ai_mode"] == "llm"
