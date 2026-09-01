import json
import os
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.models import ParsedProposal

SYSTEM_PROMPT = """You are a landscaping estimator assistant for Greenscape Pro.

You will be given:
1. Raw, informal site-walk notes from the owner (may be messy, shorthand, incomplete)
2. A pricing catalog of available line items with their id, name, unit, and unit_price

Your job: extract the scope described in the notes and map it to catalog items with
realistic quantities based on what's described. Only use items that exist in the
catalog (match by pricing_item_id). If something in the notes has no reasonable
catalog match, omit it rather than inventing a price.

Respond with ONLY valid JSON matching this exact structure, no markdown fences,
no commentary:

{
  "client_name": "string",
  "line_items": [
    {
      "pricing_item_id": int,
      "name": "string (matches catalog item name)",
      "quantity": float,
      "unit_price": float (matches catalog unit_price),
      "line_total": float (quantity * unit_price)
    }
  ],
  "subtotal": float (sum of all line_totals),
  "notes_summary": "1-2 sentence plain summary of the request",
  "special_conditions": ["list", "of", "flags like HOA approval needed, permit required, etc"]
}
"""


def parse_notes_to_proposal(
    client_name: str, raw_notes: str, pricing_catalog: list[dict]
) -> tuple[ParsedProposal | None, str | None]:
    """Returns (parsed_proposal, error_message). One of the two is always None."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    catalog_str = json.dumps(pricing_catalog, indent=2)
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Client name: {client_name}\n\n"
        f"Site-walk notes:\n{raw_notes}\n\n"
        f"Pricing catalog:\n{catalog_str}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        raw_json = response.text
    except Exception as e:
        return None, f"LLM call failed: {e}"

    try:
        data = json.loads(raw_json)
        parsed = ParsedProposal(**data)
        return parsed, None
    except (json.JSONDecodeError, ValidationError) as e:
        # Guardrail: malformed or off-schema output never gets auto-processed.
        # It's stored with the error so a human can review and re-run.
        return None, f"Validation failed: {e}"
