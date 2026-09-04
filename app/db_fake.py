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
    record = {"id": proposal_id, "created_at": "2026-09-01T00:00:00Z", **row}
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
