import json
import logging
import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app import db, llm, slack

load_dotenv()


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production and cloud environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "path"):
            log_record["path"] = record.path
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


# Configure root logger with JSON Formatter
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
root_logger.handlers = [handler]

logger = logging.getLogger(__name__)

app = FastAPI(title="Greenscape Pro - Quote Accelerator")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching request_id to headers and contextually logging HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response


app.add_middleware(CorrelationIdMiddleware)

templates = Jinja2Templates(directory="app/templates")

RENDER_THRESHOLD = float(os.environ.get("RENDER_THRESHOLD", 30000))


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "submit.html")


@app.post("/submit")
def submit_notes(request: Request, client_name: str = Form(...), raw_notes: str = Form(...)):
    catalog = db.get_pricing_catalog()
    parsed, error = llm.parse_notes_to_proposal(client_name, raw_notes, catalog)

    if error:
        db.insert_proposal({
            "client_name": client_name,
            "raw_notes": raw_notes,
            "extracted_items": None,
            "subtotal": None,
            "needs_render": False,
            "status": "draft",
            "parse_error": error,
        })
        return RedirectResponse(url="/proposals", status_code=303)

    needs_render = parsed.subtotal > RENDER_THRESHOLD
    db.insert_proposal({
        "client_name": parsed.client_name,
        "raw_notes": raw_notes,
        "extracted_items": parsed.model_dump(),
        "subtotal": parsed.subtotal,
        "needs_render": needs_render,
        "status": "draft",
        "parse_error": None,
    })
    return RedirectResponse(url="/proposals", status_code=303)


@app.get("/proposals")
def view_proposals(request: Request):
    proposals = db.list_proposals()
    return templates.TemplateResponse(
        request, "proposals.html", {"proposals": proposals}
    )


@app.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int):
    proposal = db.update_proposal_status(proposal_id, "approved")
    slack.notify_proposal_approved(proposal)
    return RedirectResponse(url="/proposals", status_code=303)


@app.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    db.update_proposal_status(proposal_id, "rejected")
    return RedirectResponse(url="/proposals", status_code=303)


@app.get("/health")
def health():
    """Liveness + Supabase connectivity check.
    Returns 200 {status: ok} when healthy, 503 when Supabase is unreachable.
    In test mode (APP_ENV=test) always returns ok without a real DB call.
    """
    if os.environ.get("APP_ENV") == "test":
        return {"status": "ok"}
    try:
        # Lightweight connectivity check — fetches 0 rows
        db.get_client().table("proposals").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error("Health check: Supabase unreachable: %s", e)
        return JSONResponse(status_code=503, content={"status": "error", "detail": "database unreachable"})

