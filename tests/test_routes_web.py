"""
tests/test_routes_web.py — Tests for app/routes/web.py (HTML-serving UI routes).

Exercises every route moved from app/main.py into the dedicated web router,
asserting correct HTTP status codes, redirect targets, template rendering,
and side-effects on the in-memory fake database.

Runs fully offline: APP_ENV=test activates db_fake, LLM and Slack are mocked.
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

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_fake_db():
    """Isolate every test with a fresh in-memory database."""
    fake_db.reset()
    yield


VALID_LLM_RESPONSE = {
    "client_name": "Carol Contractor",
    "line_items": [
        {
            "pricing_item_id": 2,
            "name": "Hedge Trimming",
            "quantity": 40.0,
            "unit_price": 4.50,
            "line_total": 180.0,
        }
    ],
    "subtotal": 180.0,
    "notes_summary": "Trim 40 linear feet of hedges.",
    "special_conditions": [],
}

FORM_DATA = {
    "client_name": "Carol Contractor",
    "raw_notes": "Please trim the hedges around the perimeter, about 40 linear feet.",
}


def _seed_proposal(**kwargs) -> int:
    defaults = {
        "client_name": "Test Client",
        "raw_notes": "some notes",
        "extracted_items": {
            "notes_summary": "Mow lawn.",
            "line_items": [
                {
                    "pricing_item_id": 1,
                    "name": "Lawn Mowing",
                    "quantity": 100,
                    "unit_price": 0.05,
                    "line_total": 5.0,
                }
            ],
        },
        "subtotal": 5.0,
        "needs_render": False,
        "status": "draft",
        "parse_error": None,
    }
    defaults.update(kwargs)
    return fake_db.insert_proposal(defaults)["id"]


# ---------------------------------------------------------------------------
# GET / — Home / Submit form
# ---------------------------------------------------------------------------


class TestHomeRoute:
    def test_home_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_home_renders_html(self):
        response = client.get("/")
        ct = response.headers.get("content-type", "")
        assert "text/html" in ct

    def test_home_contains_form(self):
        response = client.get("/")
        assert b"form" in response.content.lower()


# ---------------------------------------------------------------------------
# POST /submit
# ---------------------------------------------------------------------------


class TestSubmitRoute:
    def _parsed(self):
        from app.models import ParsedProposal

        return (ParsedProposal(**VALID_LLM_RESPONSE), None)

    def test_submit_redirects_on_success(self):
        with patch("app.routes.web.llm.parse_notes_to_proposal", return_value=self._parsed()):
            response = client.post("/submit", data=FORM_DATA, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/proposals"

    def test_submit_stores_proposal_in_db(self):
        with patch("app.routes.web.llm.parse_notes_to_proposal", return_value=self._parsed()):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)
        proposals = fake_db.list_proposals()
        assert len(proposals) == 1
        assert proposals[0]["client_name"] == "Carol Contractor"

    def test_submit_llm_error_still_redirects(self):
        with patch(
            "app.routes.web.llm.parse_notes_to_proposal",
            return_value=(None, "API timeout"),
        ):
            response = client.post("/submit", data=FORM_DATA, follow_redirects=False)
        assert response.status_code == 303

    def test_submit_llm_error_stores_parse_error(self):
        with patch(
            "app.routes.web.llm.parse_notes_to_proposal",
            return_value=(None, "API timeout"),
        ):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)
        proposals = fake_db.list_proposals()
        assert proposals[0]["parse_error"] == "API timeout"

    def test_submit_high_value_sets_needs_render(self):
        from app.models import ParsedProposal

        big = {
            **VALID_LLM_RESPONSE,
            "subtotal": 50000.0,
            "line_items": [
                {
                    "pricing_item_id": 5,
                    "name": "Irrigation System Install",
                    "quantity": 55,
                    "unit_price": 900.0,
                    "line_total": 49500.0,
                }
            ],
        }
        with patch(
            "app.routes.web.llm.parse_notes_to_proposal",
            return_value=(ParsedProposal(**big), None),
        ):
            client.post("/submit", data=FORM_DATA, follow_redirects=False)
        assert fake_db.list_proposals()[0]["needs_render"] is True


# ---------------------------------------------------------------------------
# GET /proposals
# ---------------------------------------------------------------------------


class TestProposalsListRoute:
    def test_proposals_returns_200(self):
        assert client.get("/proposals").status_code == 200

    def test_proposals_shows_stored_client_name(self):
        _seed_proposal(client_name="Unique Client XYZ")
        response = client.get("/proposals")
        assert b"Unique Client XYZ" in response.content


# ---------------------------------------------------------------------------
# POST /proposals/{id}/approve
# ---------------------------------------------------------------------------


class TestApproveRoute:
    def test_approve_redirects(self):
        pid = _seed_proposal()
        with patch("app.routes.web.slack.notify_proposal_approved"):
            response = client.post(f"/proposals/{pid}/approve", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/proposals"

    def test_approve_changes_status(self):
        pid = _seed_proposal()
        with patch("app.routes.web.slack.notify_proposal_approved"):
            client.post(f"/proposals/{pid}/approve", follow_redirects=False)
        assert fake_db.get_proposal(pid)["status"] == "approved"

    def test_approve_calls_slack(self):
        pid = _seed_proposal()
        with patch("app.routes.web.slack.notify_proposal_approved") as mock_slack:
            client.post(f"/proposals/{pid}/approve", follow_redirects=False)
        mock_slack.assert_called_once()


# ---------------------------------------------------------------------------
# POST /proposals/{id}/reject
# ---------------------------------------------------------------------------


class TestRejectRoute:
    def test_reject_redirects(self):
        pid = _seed_proposal()
        response = client.post(f"/proposals/{pid}/reject", follow_redirects=False)
        assert response.status_code == 303

    def test_reject_changes_status(self):
        pid = _seed_proposal()
        client.post(f"/proposals/{pid}/reject", follow_redirects=False)
        assert fake_db.get_proposal(pid)["status"] == "rejected"


# ---------------------------------------------------------------------------
# POST /proposals/{id}/delete
# ---------------------------------------------------------------------------


class TestDeleteRoute:
    def test_delete_redirects(self):
        pid = _seed_proposal()
        response = client.post(f"/proposals/{pid}/delete", follow_redirects=False)
        assert response.status_code == 303

    def test_delete_removes_from_db(self):
        pid = _seed_proposal()
        client.post(f"/proposals/{pid}/delete", follow_redirects=False)
        assert fake_db.list_proposals() == []


# ---------------------------------------------------------------------------
# POST /proposals/{id}/edit
# ---------------------------------------------------------------------------


class TestEditRoute:
    def _items_json(self):
        import json

        return json.dumps(
            [
                {
                    "pricing_item_id": 3,
                    "name": "Mulch Installation",
                    "quantity": 5,
                    "unit_price": 75.0,
                    "line_total": 375.0,
                    "confidence": "high",
                    "confidence_reason": "Manual edit",
                }
            ]
        )

    def test_edit_redirects(self):
        pid = _seed_proposal()
        response = client.post(
            f"/proposals/{pid}/edit",
            data={
                "client_name": "Updated Client",
                "notes_summary": "Updated summary",
                "items_json": self._items_json(),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edit_updates_subtotal(self):
        pid = _seed_proposal()
        client.post(
            f"/proposals/{pid}/edit",
            data={
                "client_name": "Updated Client",
                "notes_summary": "Updated notes",
                "items_json": self._items_json(),
            },
            follow_redirects=False,
        )
        assert abs(fake_db.get_proposal(pid)["subtotal"] - 375.0) < 0.01

    def test_edit_invalid_json_returns_400(self):
        pid = _seed_proposal()
        response = client.post(
            f"/proposals/{pid}/edit",
            data={
                "client_name": "X",
                "notes_summary": "",
                "items_json": "NOT_VALID_JSON",
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /catalog
# ---------------------------------------------------------------------------


class TestCatalogRoute:
    def test_catalog_returns_200(self):
        assert client.get("/catalog").status_code == 200

    def test_catalog_contains_lawn_mowing(self):
        response = client.get("/catalog")
        assert b"Lawn Mowing" in response.content


# ---------------------------------------------------------------------------
# GET /analytics
# ---------------------------------------------------------------------------


class TestAnalyticsRoute:
    def test_analytics_returns_200(self):
        assert client.get("/analytics").status_code == 200


# ---------------------------------------------------------------------------
# GET /proposals/{id}/download-pdf
# ---------------------------------------------------------------------------


class TestDownloadPdfRoute:
    def test_pdf_download_returns_200_and_pdf_content_type(self):
        pid = _seed_proposal()
        response = client.get(f"/proposals/{pid}/download-pdf")
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("content-type", "")

    def test_pdf_download_unknown_proposal_returns_404(self):
        response = client.get("/proposals/9999/download-pdf")
        assert response.status_code == 404
