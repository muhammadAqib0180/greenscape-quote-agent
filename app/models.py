from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError  # noqa: F401


class LineItem(BaseModel):
    pricing_item_id: int
    name: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    line_total: float = Field(gt=0)
    confidence: Literal["high", "medium", "low"] = "high"
    confidence_reason: Optional[str] = None


class ParsedProposal(BaseModel):
    """Strict schema the LLM output must match. If it doesn't validate,
    the proposal is flagged for manual review instead of auto-processed."""

    client_name: str
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: float = Field(ge=0)
    notes_summary: str
    special_conditions: list[str] = []
    estimated_duration_days: Optional[float] = None
    recommended_crew_size: Optional[int] = None


class SubmitNotesRequest(BaseModel):
    client_name: str
    raw_notes: str = Field(min_length=10)


class UpdateProposalRequest(BaseModel):
    client_name: Optional[str] = None
    notes_summary: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    special_conditions: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# AI Rewrite Engine models
# ---------------------------------------------------------------------------


class RewriteProposalRequest(BaseModel):
    """Request body for the AI proposal rewrite endpoint.

    The estimator supplies free-text revision instructions describing what
    to change (e.g. "remove tree removal, add 3 irrigation zones, note that
    HOA approval is required"). Gemini rewrites the proposal scope against
    the same pricing catalog and returns a new structured ParsedProposal.
    """

    revision_instructions: str = Field(
        min_length=5,
        description=(
            "Free-text instructions describing what to change in this proposal. "
            "Example: 'Remove tree removal item, add 2 more irrigation zones, "
            "flag that a site permit is required.'"
        ),
    )


class RevisionEntry(BaseModel):
    """A single entry in a proposal's AI revision history.

    Stored as a JSONB array in the database so the full rewrite trail is
    queryable and auditable without a separate table.
    """

    revision_number: int = Field(ge=1, description="Monotonically increasing revision counter.")
    instructions: str = Field(description="The free-text instructions the estimator provided.")
    previous_subtotal: float = Field(ge=0, description="Subtotal before this rewrite.")
    new_subtotal: float = Field(ge=0, description="Subtotal after this rewrite.")
    subtotal_delta: float = Field(
        description="Change in subtotal (positive = increase, negative = decrease)."
    )
    added_items: list[str] = Field(
        default_factory=list,
        description="Names of line items added by this rewrite.",
    )
    removed_items: list[str] = Field(
        default_factory=list,
        description="Names of line items removed by this rewrite.",
    )
    modified_items: list[str] = Field(
        default_factory=list,
        description="Names of line items whose quantity or price changed.",
    )
    revised_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of when this rewrite was applied.",
    )

    @classmethod
    def build(
        cls,
        revision_number: int,
        instructions: str,
        previous_proposal: dict,
        new_parsed: "ParsedProposal",
    ) -> "RevisionEntry":
        """Compute item-level diff and construct the revision entry."""
        prev_extracted = previous_proposal.get("extracted_items") or {}
        prev_items = {
            item["name"]: item
            for item in (prev_extracted.get("line_items") or [])
            if isinstance(item, dict)
        }
        new_items = {item.name: item for item in new_parsed.line_items}

        prev_names = set(prev_items.keys())
        new_names = set(new_items.keys())

        added = sorted(new_names - prev_names)
        removed = sorted(prev_names - new_names)
        modified = sorted(
            name
            for name in prev_names & new_names
            if (
                abs(prev_items[name].get("quantity", 0) - new_items[name].quantity) > 0.001
                or abs(prev_items[name].get("unit_price", 0) - new_items[name].unit_price) > 0.001
            )
        )

        previous_subtotal = float(previous_proposal.get("subtotal") or 0.0)
        new_subtotal = new_parsed.subtotal

        return cls(
            revision_number=revision_number,
            instructions=instructions,
            previous_subtotal=previous_subtotal,
            new_subtotal=new_subtotal,
            subtotal_delta=round(new_subtotal - previous_subtotal, 2),
            added_items=added,
            removed_items=removed,
            modified_items=modified,
        )
