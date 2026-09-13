"""
tests/test_rewrite.py — Tests for the AI Proposal Rewrite Engine.

Exercises:
  - POST /api/v1/proposals/{id}/rewrite (happy path, LLM error, invalid proposal,
    missing scope, multiple revisions, revision numbering)
  - GET /api/v1/proposals/{id}/rewrite/history (empty, populated)
  - RevisionEntry.build() diff logic (added, removed, modified items)
  - GET /proposals/{id}/history (web UI route)

All LLM calls are mocked. Runs fully offline.
"""

import os
from unittest.mock import patch

import pytest

os.environ["APP_ENV"] = "test"
os.environ.setdefault("GEMINI_API_KEY", "fake-key")
os.environ.setdefault("RENDER_THRESHOLD", "30000")

from fastapi.testclient import TestClient  # noqa: E402

import app.db_fake as fake_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ParsedProposal, RevisionEntry  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_db():
    """Isolate each test with a clean in-memory database."""
    fake_db.reset()
    yield


ORIGINAL_PROPOSAL = {
    "client_name": "Alice Homeowner",
    "line_items": [
        {
            "pricing_item_id": 1,
            "name": "Lawn Mowing",
            "quantity": 500.0,
            "unit_price": 0.05,
            "line_total": 25.0,
            "confidence": "high",
            "confidence_reason": "Clearly stated 500 sqft",
        },
        {
            "pricing_item_id": 4,
            "name": "Tree Removal (small)",
            "quantity": 2.0,
            "unit_price": 350.0,
            "line_total": 700.0,
            "confidence": "medium",
            "confidence_reason": "Two trees mentioned",
        },
    ],
    "subtotal": 725.0,
    "notes_summary": "Mow front lawn and remove two small trees.",
    "special_conditions": [],
}

REWRITTEN_PROPOSAL = {
    "client_name": "Alice Homeowner",
    "line_items": [
        {
            "pricing_item_id": 1,
            "name": "Lawn Mowing",
            "quantity": 500.0,
            "unit_price": 0.05,
            "line_total": 25.0,
            "confidence": "high",
            "confidence_reason": "Same as before",
        },
        {
            "pricing_item_id": 5,
            "name": "Irrigation System Install",
            "quantity": 3.0,
            "unit_price": 900.0,
            "line_total": 2700.0,
            "confidence": "high",
            "confidence_reason": "Explicitly requested 3 zones",
        },
    ],
    "subtotal": 2725.0,
    "notes_summary": "Mow front lawn and install 3-zone irrigation system. HOA approval pending.",
    "special_conditions": ["HOA approval required"],
}


def _seed_proposal(with_scope: bool = True) -> int:
    """Insert a proposal into the fake DB and return its ID."""
    row = {
        "client_name": "Alice Homeowner",
        "raw_notes": "Mow 500 sqft lawn, remove 2 small trees.",
        "extracted_items": ORIGINAL_PROPOSAL if with_scope else None,
        "subtotal": 725.0 if with_scope else None,
        "needs_render": False,
        "status": "draft",
        "parse_error": None if with_scope else "parse failed",
    }
    record = fake_db.insert_proposal(row)
    return record["id"]


def _make_parsed(data: dict) -> ParsedProposal:
    return ParsedProposal(**data)


# ---------------------------------------------------------------------------
# POST /api/v1/proposals/{id}/rewrite — happy path
# ---------------------------------------------------------------------------


class TestRewriteHappyPath:
    def test_rewrite_returns_200_with_updated_proposal(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            response = client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "Remove tree removal, add 3 irrigation zones, flag HOA approval needed."},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["client_name"] == "Alice Homeowner"

    def test_rewrite_updates_subtotal(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            response = client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "Remove tree removal, add 3 irrigation zones."},
            )
        assert response.json()["subtotal"] == 2725.0

    def test_rewrite_updates_extracted_items(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "Remove tree removal, add irrigation."},
            )
        proposal = fake_db.get_proposal(pid)
        items = proposal["extracted_items"]["line_items"]
        names = [i["name"] for i in items]
        assert "Irrigation System Install" in names
        assert "Tree Removal (small)" not in names

    def test_rewrite_appends_revision_history_entry(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "Remove tree removal, add irrigation."},
            )
        history = fake_db.get_revision_history(pid)
        assert len(history) == 1

    def test_rewrite_revision_number_is_one_for_first_rewrite(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "First revision."},
            )
        history = fake_db.get_revision_history(pid)
        assert history[0]["revision_number"] == 1

    def test_rewrite_second_call_increments_revision_number(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "Rev 1."})
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "Rev 2."})
        history = fake_db.get_revision_history(pid)
        assert len(history) == 2
        assert history[0]["revision_number"] == 1
        assert history[1]["revision_number"] == 2

    def test_rewrite_high_value_sets_needs_render(self):
        pid = _seed_proposal()
        big_rewrite = {
            **REWRITTEN_PROPOSAL,
            "subtotal": 45000.0,
            "line_items": [
                {
                    "pricing_item_id": 5,
                    "name": "Irrigation System Install",
                    "quantity": 50,
                    "unit_price": 900.0,
                    "line_total": 45000.0,
                    "confidence": "high",
                    "confidence_reason": "50 zones",
                }
            ],
        }
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(big_rewrite), None)):
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "50 zones."})
        proposal = fake_db.get_proposal(pid)
        assert proposal["needs_render"] is True


# ---------------------------------------------------------------------------
# POST /api/v1/proposals/{id}/rewrite — error paths
# ---------------------------------------------------------------------------


class TestRewriteErrors:
    def test_rewrite_unknown_proposal_returns_404(self):
        response = client.post(
            "/api/v1/proposals/9999/rewrite",
            json={"revision_instructions": "Remove trees."},
        )
        assert response.status_code == 404

    def test_rewrite_proposal_with_no_scope_returns_422(self):
        pid = _seed_proposal(with_scope=False)
        response = client.post(
            f"/api/v1/proposals/{pid}/rewrite",
            json={"revision_instructions": "Remove trees."},
        )
        assert response.status_code == 422
        assert "no parsed scope" in response.json()["detail"].lower()

    def test_rewrite_llm_failure_returns_502(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(None, "LLM timeout")):
            response = client.post(
                f"/api/v1/proposals/{pid}/rewrite",
                json={"revision_instructions": "Remove trees."},
            )
        assert response.status_code == 502
        assert "LLM timeout" in response.json()["detail"]

    def test_rewrite_empty_instructions_returns_422(self):
        pid = _seed_proposal()
        response = client.post(
            f"/api/v1/proposals/{pid}/rewrite",
            json={"revision_instructions": "Hi"},  # min_length=5
        )
        # "Hi" is 2 chars — below min_length=5
        assert response.status_code == 422

    def test_rewrite_missing_instructions_field_returns_422(self):
        pid = _seed_proposal()
        response = client.post(
            f"/api/v1/proposals/{pid}/rewrite",
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/proposals/{id}/rewrite/history
# ---------------------------------------------------------------------------


class TestRewriteHistoryAPI:
    def test_history_empty_for_new_proposal(self):
        pid = _seed_proposal()
        response = client.get(f"/api/v1/proposals/{pid}/rewrite/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_history_returns_accumulated_entries(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "First change."})
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "Second change."})
        response = client.get(f"/api/v1/proposals/{pid}/rewrite/history")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_history_unknown_proposal_returns_404(self):
        response = client.get("/api/v1/proposals/9999/rewrite/history")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# RevisionEntry.build() — diff logic unit tests
# ---------------------------------------------------------------------------


class TestRevisionEntryBuild:
    def test_detects_removed_items(self):
        entry = RevisionEntry.build(
            revision_number=1,
            instructions="Remove tree removal.",
            previous_proposal={"extracted_items": ORIGINAL_PROPOSAL, "subtotal": 725.0},
            new_parsed=_make_parsed(REWRITTEN_PROPOSAL),
        )
        assert "Tree Removal (small)" in entry.removed_items

    def test_detects_added_items(self):
        entry = RevisionEntry.build(
            revision_number=1,
            instructions="Add irrigation.",
            previous_proposal={"extracted_items": ORIGINAL_PROPOSAL, "subtotal": 725.0},
            new_parsed=_make_parsed(REWRITTEN_PROPOSAL),
        )
        assert "Irrigation System Install" in entry.added_items

    def test_computes_correct_subtotal_delta(self):
        entry = RevisionEntry.build(
            revision_number=1,
            instructions="Big change.",
            previous_proposal={"extracted_items": ORIGINAL_PROPOSAL, "subtotal": 725.0},
            new_parsed=_make_parsed(REWRITTEN_PROPOSAL),
        )
        assert abs(entry.subtotal_delta - 2000.0) < 0.01

    def test_revision_number_is_preserved(self):
        entry = RevisionEntry.build(
            revision_number=3,
            instructions="Third revision.",
            previous_proposal={"extracted_items": ORIGINAL_PROPOSAL, "subtotal": 725.0},
            new_parsed=_make_parsed(REWRITTEN_PROPOSAL),
        )
        assert entry.revision_number == 3

    def test_no_diff_when_items_unchanged(self):
        entry = RevisionEntry.build(
            revision_number=1,
            instructions="Same scope, different notes.",
            previous_proposal={"extracted_items": ORIGINAL_PROPOSAL, "subtotal": 725.0},
            new_parsed=_make_parsed(ORIGINAL_PROPOSAL),
        )
        assert entry.added_items == []
        assert entry.removed_items == []
        assert entry.modified_items == []


# ---------------------------------------------------------------------------
# GET /proposals/{id}/history — Web UI route
# ---------------------------------------------------------------------------


class TestRevisionHistoryWebUI:
    def test_history_page_returns_200(self):
        pid = _seed_proposal()
        response = client.get(f"/proposals/{pid}/history")
        assert response.status_code == 200

    def test_history_page_contains_client_name(self):
        pid = _seed_proposal()
        response = client.get(f"/proposals/{pid}/history")
        assert b"Alice Homeowner" in response.content

    def test_history_page_shows_revision_entries(self):
        pid = _seed_proposal()
        with patch("app.routes.api.llm.rewrite_proposal", return_value=(_make_parsed(REWRITTEN_PROPOSAL), None)):
            client.post(f"/api/v1/proposals/{pid}/rewrite", json={"revision_instructions": "Remove tree removal."})
        response = client.get(f"/proposals/{pid}/history")
        assert response.status_code == 200
        assert b"Remove tree removal" in response.content

    def test_history_page_404_for_unknown_proposal(self):
        response = client.get("/proposals/9999/history")
        assert response.status_code == 404
