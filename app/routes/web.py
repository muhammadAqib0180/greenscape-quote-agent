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
    try:
        catalog = db.get_pricing_catalog()
    except Exception as exc:
        logger.error("Failed to fetch catalog on submit: %s", exc)
        return templates.TemplateResponse(
            request,
            "submit.html",
            {
                "error": "Database service is temporarily unavailable. Please try again in a few moments.",
                "client_name": client_name,
                "raw_notes": raw_notes,
            },
            status_code=503,
        )

    parsed, error = llm.parse_notes_to_proposal(client_name, raw_notes, catalog)

    try:
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
    except Exception as exc:
        logger.error("Failed to save proposal on submit: %s", exc)
        return templates.TemplateResponse(
            request,
            "submit.html",
            {
                "error": f"Database service error while saving draft ({exc}). Please try again.",
                "client_name": client_name,
                "raw_notes": raw_notes,
            },
            status_code=503,
        )


# ---------------------------------------------------------------------------
# Proposals dashboard
# ---------------------------------------------------------------------------


@router.get("/proposals")
def view_proposals(request: Request):
    """Render the proposals review and management dashboard."""
    try:
        proposals = db.list_proposals()
        catalog = db.get_pricing_catalog()
    except Exception as exc:
        logger.error("Failed to fetch proposals list: %s", exc)
        proposals = []
        catalog = []
    return templates.TemplateResponse(
        request, "proposals.html", {"proposals": proposals, "catalog": catalog}
    )


# ---------------------------------------------------------------------------
# Proposal lifecycle actions
# ---------------------------------------------------------------------------


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int):
    """Approve a draft proposal and fire Slack notification."""
    try:
        proposal = db.update_proposal_status(proposal_id, "approved")
        slack.notify_proposal_approved(proposal)
        return RedirectResponse(url="/proposals", status_code=303)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    except Exception as exc:
        logger.error("Database error approving proposal %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    """Reject a draft proposal."""
    try:
        db.update_proposal_status(proposal_id, "rejected")
        return RedirectResponse(url="/proposals", status_code=303)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    except Exception as exc:
        logger.error("Database error rejecting proposal %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")


@router.post("/proposals/{proposal_id}/delete")
def delete_proposal_route(proposal_id: int):
    """Delete a proposal from the database."""
    try:
        db.delete_proposal(proposal_id)
        return RedirectResponse(url="/proposals", status_code=303)
    except Exception as exc:
        logger.error("Database error deleting proposal %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")


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

    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    except Exception as exc:
        logger.error("Database error getting proposal %d for edit: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")

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

    try:
        db.update_proposal(
            proposal_id,
            {
                "client_name": client_name,
                "subtotal": subtotal,
                "needs_render": subtotal > RENDER_THRESHOLD,
                "extracted_items": extracted,
            },
        )
    except Exception as exc:
        logger.error("Database error updating proposal %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")

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
    except Exception as exc:
        logger.error("Database error downloading PDF for %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")

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
    """Render the AI revision timeline for a proposal."""
    try:
        proposal = db.get_proposal(proposal_id)
        revision_history = db.get_revision_history(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    except Exception as exc:
        logger.error("Database error fetching history for %d: %s", proposal_id, exc)
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")

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
    try:
        catalog = db.get_pricing_catalog()
    except Exception as exc:
        logger.error("Failed to load catalog: %s", exc)
        catalog = []
    return templates.TemplateResponse(request, "catalog.html", {"catalog": catalog})


@router.get("/analytics")
def view_analytics(request: Request):
    """Render the live analytics and telemetry dashboard."""
    try:
        proposals = db.list_proposals()
    except Exception as exc:
        logger.error("Failed to load proposals for analytics: %s", exc)
        proposals = []
    return templates.TemplateResponse(
        request, "analytics.html", {"proposals": proposals}
    )

