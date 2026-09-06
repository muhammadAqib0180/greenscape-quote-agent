import os
from fastapi import APIRouter, HTTPException, Response, status
from app import db, llm, slack
from app.models import SubmitNotesRequest, UpdateProposalRequest, ParsedProposal

router = APIRouter(prefix="/api/v1", tags=["Proposals & Catalog API"])

RENDER_THRESHOLD = float(os.environ.get("RENDER_THRESHOLD", 30000))


@router.get("/proposals")
def list_proposals():
    """List all proposals in descending order of creation date."""
    return db.list_proposals()


@router.get("/proposals/export/csv")
def export_proposals_csv():
    """Export all proposals as a downloadable CSV file."""
    import csv
    import io

    proposals = db.list_proposals()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Proposal ID", "Client Name", "Status", "Subtotal ($)",
        "Needs Render", "Items Count", "Created At"
    ])

    for p in proposals:
        extracted = p.get("extracted_items") or {}
        items_count = len(extracted.get("line_items", [])) if isinstance(extracted, dict) else 0
        writer.writerow([
            p.get("id"),
            p.get("client_name"),
            p.get("status"),
            f"{p.get('subtotal', 0.0) or 0.0:.2f}",
            "Yes" if p.get("needs_render") else "No",
            items_count,
            (p.get("created_at") or "")[:10],
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Quoteflow_Proposals_Export.csv"},
    )



@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: int):
    """Retrieve a single proposal by ID."""
    try:
        return db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")


@router.post("/proposals/parse")
def parse_and_create_proposal(req: SubmitNotesRequest):
    """Parse raw site-walk notes using Gemini AI and create a draft proposal."""
    catalog = db.get_pricing_catalog()
    parsed, error = llm.parse_notes_to_proposal(req.client_name, req.raw_notes, catalog)

    if error:
        record = db.insert_proposal({
            "client_name": req.client_name,
            "raw_notes": req.raw_notes,
            "extracted_items": None,
            "subtotal": None,
            "needs_render": False,
            "status": "draft",
            "parse_error": error,
        })
        return Response(
            content=db.get_proposal(record["id"]),
            status_code=status.HTTP_202_ACCEPTED
        )

    needs_render = parsed.subtotal > RENDER_THRESHOLD
    record = db.insert_proposal({
        "client_name": parsed.client_name,
        "raw_notes": req.raw_notes,
        "extracted_items": parsed.model_dump(),
        "subtotal": parsed.subtotal,
        "needs_render": needs_render,
        "status": "draft",
        "parse_error": None,
    })
    return record


@router.put("/proposals/{proposal_id}")
def update_proposal(proposal_id: int, req: UpdateProposalRequest):
    """Update proposal details (line items, client name, notes summary, special conditions)."""
    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    updates = {}
    if req.client_name is not None:
        updates["client_name"] = req.client_name

    extracted = proposal.get("extracted_items") or {}
    if not isinstance(extracted, dict):
        extracted = {}

    if req.notes_summary is not None:
        extracted["notes_summary"] = req.notes_summary

    if req.special_conditions is not None:
        extracted["special_conditions"] = req.special_conditions

    if req.line_items is not None:
        raw_items = [item.model_dump() for item in req.line_items]
        new_subtotal = sum(item.line_total for item in req.line_items)
        extracted["line_items"] = raw_items
        updates["subtotal"] = new_subtotal
        updates["needs_render"] = new_subtotal > RENDER_THRESHOLD

    if extracted:
        updates["extracted_items"] = extracted

    updated = db.update_proposal(proposal_id, updates)
    return updated


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int):
    """Approve proposal and trigger Slack webhook notification."""
    try:
        proposal = db.update_proposal_status(proposal_id, "approved")
        slack.notify_proposal_approved(proposal)
        return proposal
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    """Reject proposal draft."""
    try:
        proposal = db.update_proposal_status(proposal_id, "rejected")
        return proposal
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")


@router.delete("/proposals/{proposal_id}")
def delete_proposal(proposal_id: int):
    """Delete a proposal by ID."""
    deleted = db.delete_proposal(proposal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    return {"status": "success", "message": f"Proposal {proposal_id} deleted"}


@router.get("/catalog")
def get_catalog():
    """Retrieve available pricing catalog line items."""
    return db.get_pricing_catalog()


@router.post("/integrations/ghl/webhook")
def ghl_sync_webhook(payload: dict):
    """GoHighLevel CRM sync webhook stub for downstream automation."""
    return {
        "status": "synced",
        "crm": "GoHighLevel",
        "processed_event": payload.get("event", "proposal_update"),
    }
