"""
Tests for app/slack.py — Slack webhook notification utility.
"""

import os
from unittest.mock import patch
import httpx
import pytest

from app.slack import notify_proposal_approved


def test_notify_proposal_approved_no_webhook(monkeypatch):
    """Should return early and not post if SLACK_WEBHOOK_URL is not set."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    with patch("httpx.post") as mock_post:
        notify_proposal_approved({"client_name": "Test Client", "subtotal": 1000})
        mock_post.assert_not_called()


def test_notify_proposal_approved_standard(monkeypatch):
    """Should build standard Slack notification for proposals with needs_render=False."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/mock")
    proposal = {
        "client_name": "Acme Corp",
        "subtotal": 15000.0,
        "needs_render": False,
        "extracted_items": {"notes_summary": "Lawn mowing and hedge trimming."},
    }

    with patch("httpx.post") as mock_post:
        notify_proposal_approved(proposal)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload_text = kwargs["json"]["text"]
        assert "Acme Corp" in payload_text
        assert "$15,000.00" in payload_text
        assert "3D Render Required" not in payload_text
        assert "Lawn mowing and hedge trimming." in payload_text


def test_notify_proposal_approved_needs_render(monkeypatch):
    """Should include 3D Render notification for proposals with needs_render=True."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/mock")
    proposal = {
        "client_name": "Mega Estate",
        "subtotal": 45000.0,
        "needs_render": True,
        "extracted_items": {"notes_summary": "Complete outdoor patio build."},
    }

    with patch("httpx.post") as mock_post:
        notify_proposal_approved(proposal)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload_text = kwargs["json"]["text"]
        assert "Mega Estate" in payload_text
        assert "3D Render Required" in payload_text
        assert "$45,000.00" in payload_text
        assert "Exceeds $30k threshold" in payload_text


def test_notify_proposal_approved_handles_httpx_error(monkeypatch, caplog):
    """Should catch and log httpx.HTTPError without raising an exception."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/mock")
    proposal = {
        "client_name": "Fail Test",
        "subtotal": 5000.0,
        "needs_render": False,
    }

    with patch("httpx.post", side_effect=httpx.HTTPError("Network failure")):
        with caplog.at_level("WARNING"):
            # Should not raise exception
            notify_proposal_approved(proposal)
        assert any("Slack notify failed" in record.message for record in caplog.records)
