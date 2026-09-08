import json
import logging
import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app import db, llm, slack
from app.pdf import generate_proposal_pdf
from app.routes.api import router as api_router

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

app = FastAPI(title="QuoteFlow Pro — AI Proposal Accelerator")
app.include_router(api_router)


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
    catalog = db.get_pricing_catalog()
    return templates.TemplateResponse(
        request, "proposals.html", {"proposals": proposals, "catalog": catalog}
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


@app.post("/proposals/{proposal_id}/edit")
def edit_proposal_items(
    proposal_id: int,
    request: Request,
    client_name: str = Form(...),
    notes_summary: str = Form(""),
    items_json: str = Form(...),
):
    """Processes edited line items submitted from the proposals dashboard UI."""
    try:
        line_items_data = json.loads(items_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid items JSON formatting")

    proposal = db.get_proposal(proposal_id)
    extracted = proposal.get("extracted_items") or {}

    processed_items = []
    subtotal = 0.0

    for idx, item in enumerate(line_items_data):
        pricing_id = int(item.get("pricing_item_id", idx + 1))
        name = str(item.get("name", f"Item {idx + 1}")).strip()
        qty = max(0.01, float(item.get("quantity", 1)))
        price = max(0.01, float(item.get("unit_price", 0)))
        line_total = round(qty * price, 2)
        subtotal += line_total
        processed_items.append({
            "pricing_item_id": pricing_id,
            "name": name,
            "quantity": qty,
            "unit_price": price,
            "line_total": line_total,
            "confidence": item.get("confidence", "high"),
            "confidence_reason": item.get("confidence_reason", "Manually verified by estimator"),
        })

    subtotal = round(subtotal, 2)
    extracted["line_items"] = processed_items
    extracted["notes_summary"] = notes_summary
    extracted["client_name"] = client_name

    db.update_proposal(proposal_id, {
        "client_name": client_name,
        "subtotal": subtotal,
        "needs_render": subtotal > RENDER_THRESHOLD,
        "extracted_items": extracted,
    })

    return RedirectResponse(url="/proposals", status_code=303)


@app.post("/proposals/{proposal_id}/delete")
def delete_proposal_route(proposal_id: int):
    db.delete_proposal(proposal_id)
    return RedirectResponse(url="/proposals", status_code=303)


@app.get("/proposals/{proposal_id}/download-pdf")
def download_proposal_pdf(proposal_id: int):
    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    pdf_bytes = generate_proposal_pdf(proposal)
    filename = f"Proposal_{proposal.get('client_name', 'Client').replace(' ', '_')}_{proposal_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/catalog")
def view_catalog(request: Request):
    catalog = db.get_pricing_catalog()
    return templates.TemplateResponse(
        request, "catalog.html", {"catalog": catalog}
    )


@app.get("/analytics")
def view_analytics(request: Request):
    proposals = db.list_proposals()
    return templates.TemplateResponse(
        request, "analytics.html", {"proposals": proposals}
    )



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


if __name__ == "__main__":
    import uvicorn
    raw_port = os.environ.get("PORT", "8000")
    try:
        port_num = int("".join(filter(str.isdigit, str(raw_port))) or "8000")
    except ValueError:
        port_num = 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port_num)



