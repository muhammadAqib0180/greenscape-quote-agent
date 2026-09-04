import os
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Offline test mode: swap in the in-memory fake so no Supabase credentials
# are needed during `pytest`. Set APP_ENV=test to activate.
# ---------------------------------------------------------------------------
if os.environ.get("APP_ENV") == "test":
    from app.db_fake import (  # noqa: F401  # re-exported as this module's API
        get_client,
        get_pricing_catalog,
        insert_proposal,
        list_proposals,
        get_proposal,
        update_proposal_status,
    )
else:
    _client: Client | None = None

    def get_client() -> Client:  # type: ignore[misc]
        global _client
        if _client is None:
            url = os.environ["SUPABASE_URL"]
            key = os.environ["SUPABASE_KEY"]
            _client = create_client(url, key)
        return _client

    def get_pricing_catalog() -> list[dict]:  # type: ignore[misc]
        res = get_client().table("pricing_items").select("*").execute()
        return res.data

    def insert_proposal(row: dict) -> dict:  # type: ignore[misc]
        res = get_client().table("proposals").insert(row).execute()
        return res.data[0]

    def list_proposals() -> list[dict]:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    def get_proposal(proposal_id: int) -> dict:  # type: ignore[misc]
        res = (
            get_client().table("proposals").select("*").eq("id", proposal_id).single().execute()
        )
        return res.data

    def update_proposal_status(proposal_id: int, status: str) -> dict:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .update({"status": status})
            .eq("id", proposal_id)
            .execute()
        )
        return res.data[0]
