from pydantic import BaseModel, Field, ValidationError  # noqa: F401


class LineItem(BaseModel):
    pricing_item_id: int
    name: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    line_total: float = Field(gt=0)


class ParsedProposal(BaseModel):
    """Strict schema the LLM output must match. If it doesn't validate,
    the proposal is flagged for manual review instead of auto-processed."""
    client_name: str
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: float = Field(ge=0)
    notes_summary: str  # 1-2 sentence summary of what was requested
    special_conditions: list[str] = []  # e.g. "HOA approval required"


class SubmitNotesRequest(BaseModel):
    client_name: str
    raw_notes: str = Field(min_length=10)
