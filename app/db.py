import functools
import logging
import os
import time
from supabase import create_client, Client
try:
    from supabase.lib.client_options import ClientOptions
except ImportError:
    ClientOptions = None  # type: ignore

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operations time out (e.g. 504 Gateway Timeout)."""
    pass


def retry_db_call(max_retries: int = 3, backoff: float = 0.5):
    """Decorator to retry DB operations on transient network/Supabase errors (504, 502, 503, timeouts)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except KeyError:
                    # Do not retry KeyError (e.g., entity not found)
                    raise
                except Exception as exc:
                    last_exc = exc
                    exc_str = str(exc)
                    is_transient = any(
                        keyword in exc_str.lower()
                        for keyword in [
                            "gateway timeout",
                            "504",
                            "502",
                            "503",
                            "service unavailable",
                            "bad gateway",
                            "timeout",
                            "connection",
                            "apierrorfromjson",
                            "validationerror",
                        ]
                    )
                    if attempt < max_retries and is_transient:
                        sleep_time = backoff * (2 ** (attempt - 1))
                        logger.warning(
                            "Database call %s failed (attempt %d/%d): %s. Retrying in %.2fs...",
                            func.__name__,
                            attempt,
                            max_retries,
                            exc,
                            sleep_time,
                        )
                        time.sleep(sleep_time)
                    else:
                        break

            exc_str = str(last_exc)
            if "504" in exc_str or "gateway timeout" in exc_str.lower() or "timeout" in exc_str.lower():
                raise DatabaseTimeoutError(
                    f"Database operation '{func.__name__}' timed out (504 Gateway Timeout). Please try again."
                ) from last_exc
            elif isinstance(last_exc, DatabaseError):
                raise last_exc
            else:
                raise DatabaseError(f"Database operation '{func.__name__}' failed: {last_exc}") from last_exc

        return wrapper

    return decorator


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
            if ClientOptions is not None:
                options = ClientOptions(postgrest_client_timeout=30)
                _client = create_client(url, key, options=options)
            else:
                _client = create_client(url, key)
        return _client

    @retry_db_call()
    def get_pricing_catalog() -> list[dict]:  # type: ignore[misc]
        res = get_client().table("pricing_items").select("*").execute()
        return res.data

    @retry_db_call()
    def insert_proposal(row: dict) -> dict:  # type: ignore[misc]
        res = get_client().table("proposals").insert(row).execute()
        return res.data[0]

    @retry_db_call()
    def list_proposals() -> list[dict]:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    @retry_db_call()
    def get_proposal(proposal_id: int) -> dict:  # type: ignore[misc]
        try:
            res = (
                get_client()
                .table("proposals")
                .select("*")
                .eq("id", proposal_id)
                .single()
                .execute()
            )
            if not res.data:
                raise KeyError(f"Proposal {proposal_id} not found")
            return res.data
        except KeyError:
            raise
        except Exception as exc:
            if "PGRST116" in str(exc):
                raise KeyError(f"Proposal {proposal_id} not found") from exc
            raise

    @retry_db_call()
    def update_proposal_status(proposal_id: int, status: str) -> dict:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .update({"status": status})
            .eq("id", proposal_id)
            .execute()
        )
        if not res.data:
            raise KeyError(f"Proposal {proposal_id} not found")
        return res.data[0]

    @retry_db_call()
    def update_proposal(proposal_id: int, updates: dict) -> dict:  # type: ignore[misc]
        res = (
            get_client()
            .table("proposals")
            .update(updates)
            .eq("id", proposal_id)
            .execute()
        )
        if not res.data:
            raise KeyError(f"Proposal {proposal_id} not found")
        return res.data[0]

    @retry_db_call()
    def delete_proposal(proposal_id: int) -> bool:  # type: ignore[misc]
        res = get_client().table("proposals").delete().eq("id", proposal_id).execute()
        return len(res.data) > 0

    @retry_db_call()
    def get_revision_history(proposal_id: int) -> list[dict]:  # type: ignore[misc]
        """Return the JSONB revision_history array for a proposal."""
        try:
            res = (
                get_client()
                .table("proposals")
                .select("revision_history")
                .eq("id", proposal_id)
                .single()
                .execute()
            )
            if not res.data:
                raise KeyError(f"Proposal {proposal_id} not found")
            return res.data.get("revision_history") or []
        except KeyError:
            raise
        except Exception as exc:
            if "PGRST116" in str(exc):
                raise KeyError(f"Proposal {proposal_id} not found") from exc
            raise

    @retry_db_call()
    def add_revision_history(proposal_id: int, revision_entry: dict) -> dict:  # type: ignore[misc]
        """Append revision_entry to the JSONB revision_history column using Supabase RPC.

        Falls back to a read-modify-write if the RPC function is not deployed.
        """
        try:
            get_client().rpc(
                "append_revision",
                {"pid": proposal_id, "entry": revision_entry},
            ).execute()
        except Exception:
            current = get_revision_history(proposal_id)
            current.append(revision_entry)
            get_client().table("proposals").update(
                {"revision_history": current}
            ).eq("id", proposal_id).execute()

        return get_proposal(proposal_id)

