"""
Tests for app/db.py — Supabase client integration branch.
Tests real Supabase client wrappers by monkeypatching create_client.
"""

import importlib
import os
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def real_db_module(monkeypatch):
    """Import or reload app.db with APP_ENV unset to activate real Supabase code branch."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "mock-supabase-key")

    import app.db as db_mod
    # Reset cached client singleton if present
    if hasattr(db_mod, "_client"):
        db_mod._client = None
    importlib.reload(db_mod)

    yield db_mod

    # Restore APP_ENV=test and reload to prevent side-effects on other tests
    monkeypatch.setenv("APP_ENV", "test")
    importlib.reload(db_mod)


def test_get_client(real_db_module):
    with patch("app.db.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        c1 = real_db_module.get_client()
        assert c1 == mock_client
        assert mock_create.call_args[0] == ("https://mock.supabase.co", "mock-supabase-key")

        # Second call should return cached client without calling create_client again
        c2 = real_db_module.get_client()
        assert c2 == mock_client
        assert mock_create.call_count == 1


def test_get_pricing_catalog(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [{"id": 1, "name": "Mowing", "unit_price": 50.0}]
    mock_client.table.return_value.select.return_value.execute.return_value = mock_res

    real_db_module._client = mock_client
    catalog = real_db_module.get_pricing_catalog()

    assert catalog == mock_res.data
    mock_client.table.assert_called_once_with("pricing_items")
    mock_client.table().select.assert_called_once_with("*")


def test_insert_proposal(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    proposal_data = {"client_name": "Test Client", "subtotal": 100.0}
    mock_res.data = [proposal_data]
    mock_client.table.return_value.insert.return_value.execute.return_value = mock_res

    real_db_module._client = mock_client
    result = real_db_module.insert_proposal(proposal_data)

    assert result == proposal_data
    mock_client.table.assert_called_once_with("proposals")
    mock_client.table().insert.assert_called_once_with(proposal_data)


def test_list_proposals(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [{"id": 1, "client_name": "Client A"}]
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = mock_res

    real_db_module._client = mock_client
    proposals = real_db_module.list_proposals()

    assert proposals == mock_res.data
    mock_client.table.assert_called_once_with("proposals")
    mock_client.table().select.return_value.order.assert_called_once_with("created_at", desc=True)


def test_get_proposal(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.data = {"id": 42, "client_name": "Client B"}
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_res

    real_db_module._client = mock_client
    proposal = real_db_module.get_proposal(42)

    assert proposal == mock_res.data
    mock_client.table.assert_called_once_with("proposals")
    mock_client.table().select.return_value.eq.assert_called_once_with("id", 42)


def test_update_proposal_status(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    updated_proposal = {"id": 10, "status": "approved"}
    mock_res.data = [updated_proposal]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_res

    real_db_module._client = mock_client
    result = real_db_module.update_proposal_status(10, "approved")

    assert result == updated_proposal
    mock_client.table.assert_called_once_with("proposals")
    mock_client.table().update.assert_called_once_with({"status": "approved"})
    mock_client.table().update.return_value.eq.assert_called_once_with("id", 10)


def test_retry_db_call_transient_retry(real_db_module):
    mock_client = MagicMock()
    mock_res = MagicMock()
    proposal_data = {"client_name": "Retry Client", "subtotal": 200.0}
    mock_res.data = [proposal_data]

    # Fail twice with Gateway Timeout, then succeed on 3rd attempt
    mock_client.table.return_value.insert.return_value.execute.side_effect = [
        Exception("504 Gateway Timeout"),
        Exception("ValidationError: 3 validation errors for APIErrorFromJSON"),
        mock_res,
    ]

    real_db_module._client = mock_client
    with patch("time.sleep"):  # skip sleep in tests
        result = real_db_module.insert_proposal(proposal_data)

    assert result == proposal_data
    assert mock_client.table.return_value.insert.return_value.execute.call_count == 3


def test_retry_db_call_exhausted_raises_timeout_error(real_db_module):
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("504 Gateway Timeout")

    real_db_module._client = mock_client
    with patch("time.sleep"):
        with pytest.raises(real_db_module.DatabaseTimeoutError) as exc_info:
            real_db_module.insert_proposal({"client_name": "Fail Client"})

    assert "timed out (504 Gateway Timeout)" in str(exc_info.value)

