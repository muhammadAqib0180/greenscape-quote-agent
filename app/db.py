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
        update_proposal,
        delete_proposal,
        get_revision_history,
        add_revision_history,
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
            get_client()
            .table("proposals")
            .select("*")
            .eq("id", proposal_id)
            .single()
            .execute()
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

    def update_proposal(proposal_id: int, updates: dict) -> dict:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .update(updates)
            .eq("id", proposal_id)
            .execute()
        )
        return res.data[0]

    def delete_proposal(proposal_id: int) -> bool:  # type: ignore[misc]
        res = get_client().table("proposals").delete().eq("id", proposal_id).execute()
        return len(res.data) > 0

    # -------------------------------------------------------------------------
    # Revision history (AI Rewrite Engine)
    # -------------------------------------------------------------------------

    def get_revision_history(proposal_id: int) -> list[dict]:  # type: ignore[misc]
        """Return the JSONB revision_history array for a proposal."""
        res = (
            get_client()
            .table("proposals")
            .select("revision_history")
            .eq("id", proposal_id)
            .single()
            .execute()
        )
        return res.data.get("revision_history") or []

    def add_revision_history(proposal_id: int, revision_entry: dict) -> dict:  # type: ignore[misc]
        """Append revision_entry to the JSONB revision_history column using Supabase RPC.

        Falls back to a read-modify-write if the RPC function is not deployed.
        """
        try:
            # Preferred: atomic append via Postgres function
            # CREATE OR REPLACE FUNCTION append_revision(pid int, entry jsonb)
            # RETURNS void AS $$
            #   UPDATE proposals
            #   SET revision_history = revision_history || entry::jsonb
            #   WHERE id = pid;
            # $$ LANGUAGE SQL;
            get_client().rpc(
                "append_revision",
                {"pid": proposal_id, "entry": revision_entry},
            ).execute()
        except Exception:
            # Fallback: read-modify-write (non-atomic but always works)
            current = get_revision_history(proposal_id)
            current.append(revision_entry)
            get_client().table("proposals").update(
                {"revision_history": current}
            ).eq("id", proposal_id).execute()

        return get_proposal(proposal_id)
