"""
Tests for app/models.py — Pydantic validation rules for LineItem and ParsedProposal.
All tests run offline; no network calls or env vars required.
"""

import pytest
from pydantic import ValidationError

from app.models import LineItem, ParsedProposal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_line_item(**overrides) -> dict:
    base = {
        "pricing_item_id": 1,
        "name": "Lawn Mowing",
        "quantity": 500.0,
        "unit_price": 0.05,
        "line_total": 25.0,
    }
    base.update(overrides)
    return base


def _valid_proposal(**overrides) -> dict:
    base = {
        "client_name": "Alice Homeowner",
        "line_items": [_valid_line_item()],
        "subtotal": 25.0,
        "notes_summary": "Basic lawn mowing for front yard.",
        "special_conditions": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# LineItem tests
# ---------------------------------------------------------------------------

class TestLineItem:
    def test_valid_line_item_passes(self):
        item = LineItem(**_valid_line_item())
        assert item.quantity == 500.0
        assert item.unit_price == 0.05

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError) as exc_info:
            LineItem(**_valid_line_item(quantity=0))
        assert "quantity" in str(exc_info.value)

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError) as exc_info:
            LineItem(**_valid_line_item(quantity=-1.0))
        assert "quantity" in str(exc_info.value)

    def test_rejects_zero_unit_price(self):
        with pytest.raises(ValidationError) as exc_info:
            LineItem(**_valid_line_item(unit_price=0))
        assert "unit_price" in str(exc_info.value)

    def test_rejects_negative_unit_price(self):
        with pytest.raises(ValidationError):
            LineItem(**_valid_line_item(unit_price=-10.0))

    def test_rejects_zero_line_total(self):
        with pytest.raises(ValidationError):
            LineItem(**_valid_line_item(line_total=0))

    def test_rejects_missing_name(self):
        data = _valid_line_item()
        del data["name"]
        with pytest.raises(ValidationError) as exc_info:
            LineItem(**data)
        assert "name" in str(exc_info.value)

    def test_rejects_missing_pricing_item_id(self):
        data = _valid_line_item()
        del data["pricing_item_id"]
        with pytest.raises(ValidationError):
            LineItem(**data)


# ---------------------------------------------------------------------------
# ParsedProposal tests
# ---------------------------------------------------------------------------

class TestParsedProposal:
    def test_valid_proposal_passes(self):
        proposal = ParsedProposal(**_valid_proposal())
        assert proposal.client_name == "Alice Homeowner"
        assert len(proposal.line_items) == 1
        assert proposal.subtotal == 25.0

    def test_special_conditions_defaults_to_empty_list(self):
        data = _valid_proposal()
        del data["special_conditions"]
        proposal = ParsedProposal(**data)
        assert proposal.special_conditions == []

    def test_special_conditions_can_be_set(self):
        proposal = ParsedProposal(**_valid_proposal(special_conditions=["HOA approval required"]))
        assert "HOA approval required" in proposal.special_conditions

    def test_rejects_missing_client_name(self):
        data = _valid_proposal()
        del data["client_name"]
        with pytest.raises(ValidationError) as exc_info:
            ParsedProposal(**data)
        assert "client_name" in str(exc_info.value)

    def test_rejects_missing_line_items(self):
        data = _valid_proposal()
        del data["line_items"]
        with pytest.raises(ValidationError) as exc_info:
            ParsedProposal(**data)
        assert "line_items" in str(exc_info.value)

    def test_rejects_empty_line_items_list(self):
        """line_items must have at least one item — a proposal with zero items is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedProposal(**_valid_proposal(line_items=[]))
        assert "line_items" in str(exc_info.value)

    def test_rejects_negative_subtotal(self):
        with pytest.raises(ValidationError) as exc_info:
            ParsedProposal(**_valid_proposal(subtotal=-1.0))
        assert "subtotal" in str(exc_info.value)

    def test_zero_subtotal_is_allowed(self):
        """ge=0 means zero is valid (e.g., fully discounted proposal)."""
        proposal = ParsedProposal(**_valid_proposal(subtotal=0.0))
        assert proposal.subtotal == 0.0

    def test_rejects_line_item_with_negative_quantity(self):
        bad_item = _valid_line_item(quantity=-5.0)
        with pytest.raises(ValidationError):
            ParsedProposal(**_valid_proposal(line_items=[bad_item]))

    def test_multiple_line_items_passes(self):
        items = [
            _valid_line_item(pricing_item_id=1, name="Lawn Mowing", quantity=500, unit_price=0.05, line_total=25.0),
            _valid_line_item(pricing_item_id=2, name="Hedge Trimming", quantity=10, unit_price=4.50, line_total=45.0),
        ]
        proposal = ParsedProposal(**_valid_proposal(line_items=items, subtotal=70.0))
        assert len(proposal.line_items) == 2
