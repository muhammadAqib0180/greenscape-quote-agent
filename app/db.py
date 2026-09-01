import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def get_pricing_catalog() -> list[dict]:
    res = get_client().table("pricing_items").select("*").execute()
    return res.data


def insert_proposal(row: dict) -> dict:
    res = get_client().table("proposals").insert(row).execute()
    return res.data[0]


def list_proposals() -> list[dict]:
    res = (
        get_client()
        .table("proposals")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def get_proposal(proposal_id: int) -> dict:
    res = (
        get_client().table("proposals").select("*").eq("id", proposal_id).single().execute()
    )
    return res.data


def update_proposal_status(proposal_id: int, status: str) -> dict:
    res = (
        get_client()
        .table("proposals")
        .update({"status": status})
        .eq("id", proposal_id)
        .execute()
    )
    return res.data[0]
