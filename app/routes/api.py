import os
from fastapi import APIRouter, HTTPException, Response, status
from app import db, llm, slack
from app.models import (
    SubmitNotesRequest,
    UpdateProposalRequest,
    ParsedProposal,
    RewriteProposalRequest,
    RevisionEntry,
)

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
    writer.writerow(
        [
            "Proposal ID",
            "Client Name",
            "Status",
            "Subtotal ($)",
            "Needs Render",
            "Items Count",
            "Revisions",
            "Created At",
        ]
    )

    for p in proposals:
        extracted = p.get("extracted_items") or {}
        items_count = len(extracted.get("line_items", [])) if isinstance(extracted, dict) else 0
        revision_count = len(p.get("revision_history") or [])
        writer.writerow(
            [
                p.get("id"),
                p.get("client_name"),
                p.get("status"),
                f"{p.get('subtotal', 0.0) or 0.0:.2f}",
                "Yes" if p.get("needs_render") else "No",
                items_count,
                revision_count,
                (p.get("created_at") or "")[:10],
            ]
        )

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
        record = db.insert_proposal(
            {
                "client_name": req.client_name,
                "raw_notes": req.raw_notes,
                "extracted_items": None,
                "subtotal": None,
                "needs_render": False,
                "status": "draft",
                "parse_error": error,
            }
        )
        return Response(
            content=db.get_proposal(record["id"]),
            status_code=status.HTTP_202_ACCEPTED,
        )

    needs_render = parsed.subtotal > RENDER_THRESHOLD
    record = db.insert_proposal(
        {
            "client_name": parsed.client_name,
            "raw_notes": req.raw_notes,
            "extracted_items": parsed.model_dump(),
            "subtotal": parsed.subtotal,
            "needs_render": needs_render,
            "status": "draft",
            "parse_error": None,
        }
    )
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


# ---------------------------------------------------------------------------
# AI Rewrite Engine
# ---------------------------------------------------------------------------


@router.post("/proposals/{proposal_id}/rewrite")
def rewrite_proposal(proposal_id: int, req: RewriteProposalRequest):
    """Apply AI-driven revision instructions to an existing proposal.

    Sends the current proposal scope + the estimator's free-text instructions
    to Gemini Flash, which returns a revised ParsedProposal. The revision is
    stored as a new version of the proposal and a diff-annotated entry is
    appended to the proposal's revision_history audit trail.

    **Example instructions**:
    - *"Remove tree removal, add 3 more irrigation zones, flag that a site
      permit is required and HOA approval is pending."*
    - *"Customer wants only front yard mowing, reduce sqft to 800, add
      hedge trimming for 40 linear feet."*

    Returns the updated proposal with the new revision_history appended.
    """
    try:
        proposal = db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    if not proposal.get("extracted_items"):
        raise HTTPException(
            status_code=422,
            detail=(
                "Cannot rewrite a proposal that has no parsed scope. "
                "The original parse must succeed before revisions can be applied."
            ),
        )

    catalog = db.get_pricing_catalog()
    new_parsed, error = llm.rewrite_proposal(proposal, req.revision_instructions, catalog)

    if error:
        raise HTTPException(
            status_code=502,
            detail=f"AI rewrite failed: {error}",
        )

    # Determine revision number
    existing_history = db.get_revision_history(proposal_id)
    revision_number = len(existing_history) + 1

    # Build structured diff entry
    revision_entry = RevisionEntry.build(
        revision_number=revision_number,
        instructions=req.revision_instructions,
        previous_proposal=proposal,
        new_parsed=new_parsed,
    )

    # Persist the rewritten proposal
    needs_render = new_parsed.subtotal > RENDER_THRESHOLD
    updated = db.update_proposal(
        proposal_id,
        {
            "client_name": new_parsed.client_name,
            "extracted_items": new_parsed.model_dump(),
            "subtotal": new_parsed.subtotal,
            "needs_render": needs_render,
            "parse_error": None,
        },
    )

    # Append the audit trail entry
    final = db.add_revision_history(proposal_id, revision_entry.model_dump())
    return final


@router.get("/proposals/{proposal_id}/rewrite/history")
def get_rewrite_history(proposal_id: int):
    """Retrieve the full AI revision history for a proposal.

    Returns a list of RevisionEntry objects in chronological order,
    each containing the revision instructions, subtotal delta, and
    item-level diff (added, removed, modified line items).
    """
    try:
        db.get_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    return db.get_revision_history(proposal_id)


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------


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
