import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app import db_fake
from app.models import ParsedProposal, LineItem

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_fake_db():
    db_fake.reset()


def test_list_proposals_empty():
    res = client.get("/api/v1/proposals")
    assert res.status_code == 200
    assert res.json() == []


def test_get_catalog():
    res = client.get("/api/v1/catalog")
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) == 5
    assert catalog[0]["name"] == "Lawn Mowing"


def test_parse_and_create_proposal_success():
    fake_parsed = ParsedProposal(
        client_name="API Test Client",
        line_items=[
            LineItem(
                pricing_item_id=1,
                name="Lawn Mowing",
                quantity=100.0,
                unit_price=0.05,
                line_total=5.00,
                confidence="high",
                confidence_reason="Clear area note",
            )
        ],
        subtotal=5.00,
        notes_summary="100 sqft lawn mowing",
        special_conditions=["Standard access"],
    )

    with patch("app.llm.parse_notes_to_proposal", return_value=(fake_parsed, None)):
        res = client.post(
            "/api/v1/proposals/parse",
            json={"client_name": "API Test Client", "raw_notes": "100 sqft lawn mowing needed"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["client_name"] == "API Test Client"
        assert data["subtotal"] == 5.00
        assert data["status"] == "draft"


def test_get_proposal_by_id():
    db_fake.insert_proposal({
        "client_name": "Single Client",
        "raw_notes": "test notes",
        "extracted_items": {},
        "subtotal": 100.0,
        "needs_render": False,
        "status": "draft",
        "parse_error": None,
    })
    res = client.get("/api/v1/proposals/1")
    assert res.status_code == 200
    assert res.json()["client_name"] == "Single Client"


def test_get_proposal_not_found():
    res = client.get("/api/v1/proposals/999")
    assert res.status_code == 404


def test_update_proposal_api():
    p = db_fake.insert_proposal({
        "client_name": "Old Client",
        "raw_notes": "notes",
        "extracted_items": {"notes_summary": "old summary", "line_items": []},
        "subtotal": 10.0,
        "needs_render": False,
        "status": "draft",
        "parse_error": None,
    })
    update_payload = {
        "client_name": "Updated Client",
        "notes_summary": "new summary",
        "line_items": [
            {
                "pricing_item_id": 3,
                "name": "Mulch Installation",
                "quantity": 2.0,
                "unit_price": 75.0,
                "line_total": 150.0,
                "confidence": "high",
            }
        ],
    }
    res = client.put(f"/api/v1/proposals/{p['id']}", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["client_name"] == "Updated Client"
    assert data["subtotal"] == 150.0


def test_approve_and_reject_proposal_api():
    p = db_fake.insert_proposal({
        "client_name": "Action Client",
        "raw_notes": "notes",
        "extracted_items": {},
        "subtotal": 100.0,
        "needs_render": False,
        "status": "draft",
        "parse_error": None,
    })

    res = client.post(f"/api/v1/proposals/{p['id']}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    res_rej = client.post(f"/api/v1/proposals/{p['id']}/reject")
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"


def test_delete_proposal_api():
    p = db_fake.insert_proposal({
        "client_name": "Delete Client",
        "raw_notes": "notes",
        "extracted_items": {},
        "subtotal": 50.0,
        "needs_render": False,
        "status": "draft",
        "parse_error": None,
    })
    res = client.delete(f"/api/v1/proposals/{p['id']}")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    res_missing = client.delete("/api/v1/proposals/999")
    assert res_missing.status_code == 404


def test_ghl_webhook_stub():
    res = client.post("/api/v1/integrations/ghl/webhook", json={"event": "proposal_approved"})
    assert res.status_code == 200
    assert res.json()["crm"] == "GoHighLevel"
