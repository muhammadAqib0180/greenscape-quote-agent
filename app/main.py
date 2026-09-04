import logging
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app import db, llm, slack

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Greenscape Pro - Quote Accelerator")
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
