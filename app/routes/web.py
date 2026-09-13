"""
app/routes/web.py — HTML-serving routes for the QuoteFlow Pro UI.

All browser-facing routes live here, keeping app/main.py thin (wiring only).
These routes render Jinja2 templates and redirect after mutations. The JSON
REST API lives in app/routes/api.py.
"""

import json
import logging
import os
import pathlib

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db, llm, slack
from app.pdf import generate_proposal_pdf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Web UI"])

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

RENDER_THRESHOLD = float(os.environ.get("RENDER_THRESHOLD", 30000))


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


@router.get("/")
def home(request: Request):
    """Serve the proposal submission form."""
    return templates.TemplateResponse(request, "submit.html")


# ---------------------------------------------------------------------------
# Submit raw site-walk notes → parse + store draft
# ---------------------------------------------------------------------------


@router.post("/submit")
def submit_notes(
    request: Request,
    client_name: str = Form(...),
    raw_notes: str = Form(...),
):
    """Parse raw field notes via Gemini and store as a draft proposal."""
    catalog = db.get_pricing_catalog()
    parsed, error = llm.parse_notes_to_proposal(client_name, raw_notes, catalog)

    if error:
        db.insert_proposal(
            {
                "client_name": client_name,
                "raw_notes": raw_notes,
                "extracted_items": None,
                "subtotal": None,
                "needs_render": False,
                "status": "draft",
                "parse_error": error,
            }
        )
        return RedirectResponse(url="/proposals", status_code=303)

    needs_render = parsed.subtotal > RENDER_THRESHOLD
    db.insert_proposal(
        {
            "client_name": parsed.client_name,
            "raw_notes": raw_notes,
            "extracted_items": parsed.model_dump(),
            "subtotal": parsed.subtotal,
            "needs_render": needs_render,
            "status": "draft",
            "parse_error": None,
        }
    )
    return RedirectResponse(url="/proposals", status_code=303)


# ---------------------------------------------------------------------------
# Proposals dashboard
# ---------------------------------------------------------------------------


@router.get("/proposals")
def view_proposals(request: Request):
    """Render the proposals review and management dashboard."""
    proposals = db.list_proposals()
    catalog = db.get_pricing_catalog()
    return templates.TemplateResponse(
        request, "proposals.html", {"proposals": proposals, "catalog": catalog}
    )


# ---------------------------------------------------------------------------
# Proposal lifecycle actions
# ---------------------------------------------------------------------------


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int):
    """Approve a draft proposal and fire Slack notification."""
    proposal = db.update_proposal_status(proposal_id, "approved")
    slack.notify_proposal_approved(proposal)
    return RedirectResponse(url="/proposals", status_code=303)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    """Reject a draft proposal."""
    db.update_proposal_status(proposal_id, "rejected")
    return RedirectResponse(url="/proposals", status_code=303)


@router.post("/proposals/{proposal_id}/delete")
def delete_proposal_route(proposal_id: int):
    """Delete a proposal from the database."""
    db.delete_proposal(proposal_id)
    return RedirectResponse(url="/proposals", status_code=303)


# ---------------------------------------------------------------------------
# Inline editor
# ---------------------------------------------------------------------------


@router.post("/proposals/{proposal_id}/edit")
def edit_proposal_items(
    proposal_id: int,
    request: Request,
    client_name: str = Form(...),
    notes_summary: str = Form(""),
    items_json: str = Form(...),
):
    """Process edited line items submitted from the proposals dashboard UI."""
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
        processed_items.append(
            {
                "pricing_item_id": pricing_id,
                "name": name,
                "quantity": qty,
                "unit_price": price,
                "line_total": line_total,
                "confidence": item.get("confidence", "high"),
                "confidence_reason": item.get(
                    "confidence_reason", "Manually verified by estimator"
                ),
            }
        )

    subtotal = round(subtotal, 2)
    extracted["line_items"] = processed_items
    extracted["notes_summary"] = notes_summary
    extracted["client_name"] = client_name

    db.update_proposal(
        proposal_id,
        {
            "client_name": client_name,
            "subtotal": subtotal,
            "needs_render": subtotal > RENDER_THRESHOLD,
            "extracted_items": extracted,
        },
    )

    return RedirectResponse(url="/proposals", status_code=303)


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------


@router.get("/proposals/{proposal_id}/download-pdf")
def download_proposal_pdf(proposal_id: int):
    """Generate and stream a client-ready PDF for the specified proposal."""
    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    pdf_bytes = generate_proposal_pdf(proposal)
    filename = (
        f"Proposal_{proposal.get('client_name', 'Client').replace(' ', '_')}"
        f"_{proposal_id}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Revision history UI
# ---------------------------------------------------------------------------


@router.get("/proposals/{proposal_id}/history")
def view_revision_history(proposal_id: int, request: Request):
    """Render the AI revision timeline for a proposal.

    Shows every rewrite that has been applied — instructions, item-level
    diffs, and subtotal changes — so estimators can audit the AI's
    decision-making history.
    """
    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    revision_history = db.get_revision_history(proposal_id)
    return templates.TemplateResponse(
        request,
        "revision_history.html",
        {
            "proposal": proposal,
            "revision_history": revision_history,
            "proposal_id": proposal_id,
        },
    )


# ---------------------------------------------------------------------------
# Catalog & Analytics
# ---------------------------------------------------------------------------


@router.get("/catalog")
def view_catalog(request: Request):
    """Render the interactive pricing catalog explorer."""
    catalog = db.get_pricing_catalog()
    return templates.TemplateResponse(request, "catalog.html", {"catalog": catalog})


@router.get("/analytics")
def view_analytics(request: Request):
    """Render the live analytics and telemetry dashboard."""
    proposals = db.list_proposals()
    return templates.TemplateResponse(
        request, "analytics.html", {"proposals": proposals}
    )
