"""
app/main.py — Application entry-point and wiring.

Responsibilities (only):
  1. Configure structured JSON logging (via app.logging_config).
  2. Create the FastAPI application instance.
  3. Attach middleware (CorrelationIdMiddleware).
  4. Register all routers (API + Web UI).
  5. Expose /healthz (liveness) and /readyz (readiness) endpoints.

All route logic lives in app/routes/api.py (JSON REST) and
app/routes/web.py (HTML UI).  Logging primitives live in
app/logging_config.py.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import db
from app.logging_config import CorrelationIdMiddleware, configure_root_logger
from app.routes.api import router as api_router
from app.routes.web import router as web_router

load_dotenv()

configure_root_logger()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QuoteFlow Pro — AI Proposal Accelerator",
    description=(
        "Turns raw site-walk field notes into structured, catalog-priced proposal "
        "drafts in seconds. Includes AI rewrite engine, PDF export, Slack webhooks, "
        "and a full audit trail of LLM revisions."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CorrelationIdMiddleware)
app.include_router(api_router)
app.include_router(web_router)


# ---------------------------------------------------------------------------
# Liveness probe — no external dependencies
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["Observability"])
def healthz():
    """Liveness probe.

    Returns 200 {"status": "ok"} unconditionally.  Used by load balancers
    and the CI docker-build job to confirm the process started successfully.
    No database or external service calls are made.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Readiness probe — checks DB connectivity
# ---------------------------------------------------------------------------


@app.get("/readyz", tags=["Observability"])
def readyz():
    """Readiness probe.

    Returns 200 {"status": "ok"} when the database is reachable.
    Returns 503 {"status": "error", "detail": "..."} when it is not.

    In APP_ENV=test mode the DB is the in-memory fake so this always
    returns 200.  In production it performs a lightweight Supabase ping.
    """
    if os.environ.get("APP_ENV") == "test":
        return {"status": "ok"}
    try:
        db.get_pricing_catalog()
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "database unreachable"},
        )


# ---------------------------------------------------------------------------
# Legacy /health alias (preserved for backwards compatibility)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Observability"])
def health():
    """Liveness + Supabase connectivity check (legacy alias for /healthz).

    Returns 200 {status: ok} when healthy, 503 when Supabase is unreachable.
    In test mode (APP_ENV=test) always returns ok without a real DB call.
    """
    if os.environ.get("APP_ENV") == "test":
        return {"status": "ok"}
    try:
        db.get_client().table("proposals").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error("Health check: Supabase unreachable: %s", e)
        return JSONResponse(
            status_code=503, content={"status": "error", "detail": "database unreachable"}
        )


# ---------------------------------------------------------------------------
# Server entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    raw_port = os.environ.get("PORT", "8000")
    try:
        port_num = int("".join(filter(str.isdigit, str(raw_port))) or "8000")
    except ValueError:
        port_num = 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port_num)
