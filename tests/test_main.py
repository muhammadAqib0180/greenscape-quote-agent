"""
Tests for app/main.py — FastAPI routes via TestClient with fake db and mocked LLM/Slack.
Runs fully offline: APP_ENV=test activates in-memory db, LLM and Slack are mocked.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Must set before importing app modules so APP_ENV routing fires
os.environ["APP_ENV"] = "test"
os.environ.setdefault("GEMINI_API_KEY", "fake-key")
os.environ.setdefault("RENDER_THRESHOLD", "30000")

from fastapi.testclient import TestClient  # noqa: E402

import app.db_fake as fake_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_fake_db():
    """Reset in-memory store before every test so tests are independent."""
    fake_db.reset()
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PROPOSAL_RESPONSE = {
    "client_name": "Alice Homeowner",
    "line_items": [
        {
            "pricing_item_id": 1,
            "name": "Lawn Mowing",
            "quantity": 500.0,
            "unit_price": 0.05,
            "line_total": 25.0,
        }
    ],
    "subtotal": 25.0,
    "notes_summary": "Mow front lawn.",
    "special_conditions": [],
}

FORM_DATA = {
    "client_name": "Alice Homeowner",
    "raw_notes": "Mow the entire front lawn, about 500 sqft.",
}


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestHome:
    def test_home_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200
        assert b"<html" in response.content or b"<!DOCTYPE" in response.content.lower() or b"form" in response.content.lower()


# ---------------------------------------------------------------------------
# POST /submit
# ---------------------------------------------------------------------------

class TestSubmit:
    def _mock_llm_success(self):
        from app.models import ParsedProposal
        parsed = ParsedProposal(**VALID_PROPOSAL_RESPONSE)
        return (parsed, None)

    def _mock_llm_error(self):
        return (None, "LLM call failed: timeout")

    def test_submit_valid_notes_redirects_to_proposals(self):
        with patch("app.main.llm.parse_notes_to_proposal", return_value=self._mock_llm_success()):
            response = client.post("/submit", data=FORM_DATA, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/proposals"

    def test_submit_valid_notes_stores_proposal(self):
        with patch("app.main.llm.parse_notes_to_proposal", return_value=self._mock_llm_success()):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)
        proposals = fake_db.list_proposals()
        assert len(proposals) == 1
        assert proposals[0]["client_name"] == "Alice Homeowner"
        assert proposals[0]["status"] == "draft"
        assert proposals[0]["subtotal"] == 25.0

    def test_submit_llm_error_stores_draft_with_error(self):
        with patch("app.main.llm.parse_notes_to_proposal", return_value=self._mock_llm_error()):
            response = client.post("/submit", data=FORM_DATA, follow_redirects=False)
        assert response.status_code == 303
        proposals = fake_db.list_proposals()
        assert len(proposals) == 1
        assert proposals[0]["parse_error"] == "LLM call failed: timeout"
        assert proposals[0]["subtotal"] is None

    def test_submit_high_value_sets_needs_render(self):
        """Proposals above RENDER_THRESHOLD (30000) should set needs_render=True."""
        big_proposal = {
            **VALID_PROPOSAL_RESPONSE,
            "subtotal": 50000.0,
            "line_items": [
                {"pricing_item_id": 5, "name": "Irrigation System Install", "quantity": 55, "unit_price": 900.0, "line_total": 49500.0}
            ],
        }
        from app.models import ParsedProposal
        parsed = ParsedProposal(**big_proposal)

        with patch("app.main.llm.parse_notes_to_proposal", return_value=(parsed, None)):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)

        proposals = fake_db.list_proposals()
        assert proposals[0]["needs_render"] is True

    def test_submit_low_value_does_not_set_needs_render(self):
        with patch("app.main.llm.parse_notes_to_proposal", return_value=self._mock_llm_success()):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)

        proposals = fake_db.list_proposals()
        assert proposals[0]["needs_render"] is False


# ---------------------------------------------------------------------------
# GET /proposals
# ---------------------------------------------------------------------------

class TestProposalsList:
    def test_proposals_page_returns_200(self):
        response = client.get("/proposals")
        assert response.status_code == 200

    def test_proposals_page_shows_stored_proposals(self):
        fake_db.insert_proposal({
            "client_name": "Test Client",
            "raw_notes": "some notes",
            "extracted_items": {
                "notes_summary": "Mow front lawn.",
                "line_items": [
                    {"pricing_item_id": 1, "name": "Lawn Mowing", "quantity": 100, "unit_price": 0.05, "line_total": 5.0}
                ],
            },
            "subtotal": 5.0,
            "needs_render": False,
            "status": "draft",
            "parse_error": None,
        })
        response = client.get("/proposals")
        assert response.status_code == 200
        assert b"Test Client" in response.content


# ---------------------------------------------------------------------------
# POST /proposals/{id}/approve
# ---------------------------------------------------------------------------

class TestApproveProposal:
    def _seed_proposal(self) -> int:
        row = fake_db.insert_proposal({
            "client_name": "Alice Homeowner",
            "raw_notes": "mow lawn",
            "extracted_items": {"notes_summary": "Mow front lawn."},
            "subtotal": 25.0,
            "needs_render": False,
            "status": "draft",
            "parse_error": None,
        })
        return row["id"]

    def test_approve_redirects_to_proposals(self):
        proposal_id = self._seed_proposal()
        with patch("app.main.slack.notify_proposal_approved") as mock_slack:
            response = client.post(f"/proposals/{proposal_id}/approve", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/proposals"

    def test_approve_updates_status(self):
        proposal_id = self._seed_proposal()
        with patch("app.main.slack.notify_proposal_approved"):
            client.post(f"/proposals/{proposal_id}/approve", follow_redirects=False)
        proposal = fake_db.get_proposal(proposal_id)
        assert proposal["status"] == "approved"

    def test_approve_calls_slack_notify(self):
        proposal_id = self._seed_proposal()
        with patch("app.main.slack.notify_proposal_approved") as mock_slack:
            client.post(f"/proposals/{proposal_id}/approve", follow_redirects=False)
        mock_slack.assert_called_once()
        called_proposal = mock_slack.call_args[0][0]
        assert called_proposal["client_name"] == "Alice Homeowner"


# ---------------------------------------------------------------------------
# POST /proposals/{id}/reject
# ---------------------------------------------------------------------------

class TestRejectProposal:
    def _seed_proposal(self) -> int:
        row = fake_db.insert_proposal({
            "client_name": "Bob Builder",
            "raw_notes": "trim hedges",
            "extracted_items": None,
            "subtotal": 45.0,
            "needs_render": False,
            "status": "draft",
            "parse_error": None,
        })
        return row["id"]

    def test_reject_redirects_to_proposals(self):
        proposal_id = self._seed_proposal()
        response = client.post(f"/proposals/{proposal_id}/reject", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/proposals"

    def test_reject_updates_status(self):
        proposal_id = self._seed_proposal()
        client.post(f"/proposals/{proposal_id}/reject", follow_redirects=False)
        proposal = fake_db.get_proposal(proposal_id)
        assert proposal["status"] == "rejected"
