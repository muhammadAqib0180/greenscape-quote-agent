"""
Tests for app/llm.py — LLM parse validation and error paths.
google.genai.Client is fully mocked; no API key or network required.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure APP_ENV=test is active before any app imports
os.environ.setdefault("APP_ENV", "test")

from app.models import ParsedProposal  # noqa: E402
import app.llm as llm_module  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CATALOG = [
    {"id": 1, "name": "Lawn Mowing", "unit": "sqft", "unit_price": 0.05},
    {"id": 2, "name": "Hedge Trimming", "unit": "linear_ft", "unit_price": 4.50},
]

VALID_LLM_JSON = json.dumps({
    "client_name": "Bob Builder",
    "line_items": [
        {
            "pricing_item_id": 1,
            "name": "Lawn Mowing",
            "quantity": 1000.0,
            "unit_price": 0.05,
            "line_total": 50.0,
        }
    ],
    "subtotal": 50.0,
    "notes_summary": "Mow the large front lawn.",
    "special_conditions": [],
})

MALFORMED_JSON = "{ this is not valid JSON !!!"

OFF_SCHEMA_JSON = json.dumps({
    "client_name": "Bob Builder",
    "line_items": [
        {
            "pricing_item_id": 1,
            "name": "Lawn Mowing",
            "quantity": -999,  # violates gt=0
            "unit_price": 0.05,
            "line_total": 50.0,
        }
    ],
    "subtotal": 50.0,
    "notes_summary": "Something.",
    "special_conditions": [],
})


def _make_mock_response(text: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp


def _call(raw_notes: str = "mow the front lawn", json_text: str = VALID_LLM_JSON):
    """Helper: patch genai.Client, call parse_notes_to_proposal, return (result, error)."""
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = _make_mock_response(json_text)

    with patch.object(llm_module.genai, "Client", return_value=mock_client_instance):
        return llm_module.parse_notes_to_proposal("Bob Builder", raw_notes, SAMPLE_CATALOG)


def _call_with_exception(exc: Exception):
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = exc

    with patch.object(llm_module.genai, "Client", return_value=mock_client_instance):
        return llm_module.parse_notes_to_proposal("Bob Builder", "mow", SAMPLE_CATALOG)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseNotesToProposal:

    def test_valid_json_returns_parsed_proposal(self):
        """Happy path: LLM returns valid JSON → (ParsedProposal, None)."""
        result, error = _call()

        assert error is None
        assert result is not None
        assert isinstance(result, ParsedProposal)
        assert result.client_name == "Bob Builder"
        assert result.subtotal == 50.0

    def test_malformed_json_returns_none_and_error(self):
        """LLM returns unparseable JSON → (None, error_string containing 'Validation failed')."""
        result, error = _call(json_text=MALFORMED_JSON)

        assert result is None
        assert error is not None
        assert "Validation failed" in error

    def test_off_schema_json_returns_none_and_error(self):
        """LLM returns valid JSON that fails Pydantic validation → (None, error_string)."""
        result, error = _call(json_text=OFF_SCHEMA_JSON)

        assert result is None
        assert error is not None
        assert "Validation failed" in error

    def test_llm_network_exception_returns_none_and_error(self):
        """Network / API error during LLM call → (None, error_string containing 'LLM call failed')."""
        result, error = _call_with_exception(Exception("Connection refused"))

        assert result is None
        assert error is not None
        assert "LLM call failed" in error

    def test_empty_line_items_returns_none_and_error(self):
        """LLM returns valid JSON but empty line_items → fails min_length=1 → (None, error_string)."""
        bad_json = json.dumps({
            "client_name": "Bob Builder",
            "line_items": [],  # violates min_length=1
            "subtotal": 0.0,
            "notes_summary": "Nothing found.",
            "special_conditions": [],
        })
        result, error = _call(json_text=bad_json)

        assert result is None
        assert error is not None

    def test_missing_notes_summary_returns_none_and_error(self):
        """LLM omits required notes_summary field → (None, error_string)."""
        incomplete_json = json.dumps({
            "client_name": "Bob Builder",
            "line_items": [
                {"pricing_item_id": 1, "name": "Lawn Mowing", "quantity": 100, "unit_price": 0.05, "line_total": 5.0}
            ],
            "subtotal": 5.0,
            # notes_summary is intentionally missing
            "special_conditions": [],
        })
        result, error = _call(json_text=incomplete_json)

        assert result is None
        assert error is not None
        assert "Validation failed" in error

    def test_special_conditions_preserved_in_result(self):
        """Special conditions list from LLM response is preserved."""
        json_with_conditions = json.dumps({
            "client_name": "Bob Builder",
            "line_items": [
                {"pricing_item_id": 1, "name": "Lawn Mowing", "quantity": 100, "unit_price": 0.05, "line_total": 5.0}
            ],
            "subtotal": 5.0,
            "notes_summary": "Needs HOA approval.",
            "special_conditions": ["HOA approval required", "Permit needed"],
        })
        result, error = _call(json_text=json_with_conditions)

        assert error is None
        assert result is not None
        assert "HOA approval required" in result.special_conditions
