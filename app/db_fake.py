"""
In-memory fake database backend for offline testing.

Activated when APP_ENV=test is set in the environment. Mirrors every
function signature in app/db.py so tests run with zero network calls
and no Supabase credentials required.
"""

from __future__ import annotations

import itertools
from typing import Any

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_id_counter = itertools.count(start=1)
_proposals: dict[int, dict[str, Any]] = {}

# A small, realistic pricing catalog used by tests
_CATALOG: list[dict[str, Any]] = [
    {"id": 1, "name": "Lawn Mowing", "unit": "sqft", "unit_price": 0.05},
    {"id": 2, "name": "Hedge Trimming", "unit": "linear_ft", "unit_price": 4.50},
    {"id": 3, "name": "Mulch Installation", "unit": "cubic_yd", "unit_price": 75.00},
    {"id": 4, "name": "Tree Removal (small)", "unit": "each", "unit_price": 350.00},
    {"id": 5, "name": "Irrigation System Install", "unit": "zone", "unit_price": 900.00},
]


def reset() -> None:
    """Reset all in-memory state — call in test setUp / autouse fixture."""
    global _id_counter
    _id_counter = itertools.count(start=1)
    _proposals.clear()


# ---------------------------------------------------------------------------
# Public API — mirrors app/db.py exactly
# ---------------------------------------------------------------------------


def get_client():  # type: ignore[return]
    """Fake client — returns None; tests should not call this directly."""
    return None


def get_pricing_catalog() -> list[dict]:
    return list(_CATALOG)


def insert_proposal(row: dict) -> dict:
    proposal_id = next(_id_counter)
    record: dict[str, Any] = {
        "id": proposal_id,
        "created_at": "2026-09-01T00:00:00Z",
        "revision_history": [],
        **row,
    }
    _proposals[proposal_id] = record
    return record


def list_proposals() -> list[dict]:
    return list(reversed(list(_proposals.values())))


def get_proposal(proposal_id: int) -> dict:
    if proposal_id not in _proposals:
        raise KeyError(f"Proposal {proposal_id} not found")
    return _proposals[proposal_id]


def update_proposal_status(proposal_id: int, status: str) -> dict:
    if proposal_id not in _proposals:
        raise KeyError(f"Proposal {proposal_id} not found")
    _proposals[proposal_id]["status"] = status
    return _proposals[proposal_id]


def update_proposal(proposal_id: int, updates: dict) -> dict:
    if proposal_id not in _proposals:
        raise KeyError(f"Proposal {proposal_id} not found")
    _proposals[proposal_id].update(updates)
    return _proposals[proposal_id]


def delete_proposal(proposal_id: int) -> bool:
    if proposal_id not in _proposals:
        return False
    del _proposals[proposal_id]
    return True


# ---------------------------------------------------------------------------
# Revision history API (AI Rewrite Engine)
# ---------------------------------------------------------------------------


def get_revision_history(proposal_id: int) -> list[dict]:
    """Return the full revision history list for a proposal.

    Returns an empty list if the proposal has no revisions yet.
    Raises KeyError if the proposal does not exist.
    """
    proposal = get_proposal(proposal_id)
    return list(proposal.get("revision_history") or [])


def add_revision_history(proposal_id: int, revision_entry: dict) -> dict:
    """Append a revision entry to a proposal's history and return the proposal.

    The revision_entry dict should match the RevisionEntry schema.
    Raises KeyError if the proposal does not exist.
    """
    proposal = get_proposal(proposal_id)
    history: list[dict] = list(proposal.get("revision_history") or [])
    history.append(revision_entry)
    _proposals[proposal_id]["revision_history"] = history
    return _proposals[proposal_id]
