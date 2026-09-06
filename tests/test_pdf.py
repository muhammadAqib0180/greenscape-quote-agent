import pytest
from app.pdf import generate_proposal_pdf


def test_generate_proposal_pdf_success():
    proposal = {
        "id": 42,
        "client_name": "PDF Test Client",
        "subtotal": 1250.00,
        "status": "approved",
        "needs_render": True,
        "created_at": "2026-09-06T12:00:00Z",
        "extracted_items": {
            "notes_summary": "Full lawn maintenance and mulch installation",
            "line_items": [
                {
                    "pricing_item_id": 1,
                    "name": "Lawn Mowing",
                    "quantity": 10.0,
                    "unit_price": 50.0,
                    "line_total": 500.0,
                    "confidence": "high",
                },
                {
                    "pricing_item_id": 3,
                    "name": "Mulch Installation",
                    "quantity": 10.0,
                    "unit_price": 75.0,
                    "line_total": 750.0,
                    "confidence": "medium",
                },
            ],
            "special_conditions": ["Permit required", "HOA clearance pending"],
        },
    }

    pdf_bytes = generate_proposal_pdf(proposal)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
