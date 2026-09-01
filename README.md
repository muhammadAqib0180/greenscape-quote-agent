# Greenscape Pro — Quote & Proposal Accelerator

Turns Marcus's raw site-walk notes into a structured, priced proposal draft — cutting
the quote cycle from 6–9 days to minutes of review, instead of days of manual
line-by-line pricing.

## Why this system
Marcus is the bottleneck: he's the only one who can turn a site walk into a priced
scope. This agent removes the interpretation step (matching messy notes to the
pricing catalog) while keeping Marcus as the final approver before anything sends —
his judgment isn't automated, his data entry is.

## Architecture
- **FastAPI** backend, server-rendered Jinja templates (no separate frontend build)
- **Supabase (Postgres)** for persistent storage — `proposals` + `pricing_items`
- **Gemini 2.0 Flash** parses raw notes against the pricing catalog into strict
  JSON, validated against a Pydantic schema before it's ever shown or sent
- **Slack webhook** fires on approval — replaces the manual "is this ready yet?"
  pings the team currently does 5-10x/day
- Proposals over $30K auto-flag `needs_render` to mirror the existing rule about
  routing to Carlos for a render before send

## Guardrails
If the LLM output doesn't validate against the schema (malformed JSON, missing
fields, item IDs that don't exist in the catalog), the proposal is stored with a
`parse_error` and surfaced for manual review — it never auto-sends bad data.

## Setup

1. **Supabase**: create a project at supabase.com, then run `supabase_schema.sql`
   in the SQL Editor to create tables and seed the pricing catalog.
2. **Gemini key**: get one at aistudio.google.com/apikey
3. **Slack webhook**: create one at api.slack.com/apps → Incoming Webhooks →
   Add to Slack (any workspace/channel works for testing)
4. Copy `.env.example` to `.env` and fill in the three values above.
5. Install and run locally:
   ```
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
6. Visit `http://localhost:8000` to submit notes, `/proposals` to review/approve.

## Deploy
Push to GitHub, connect the repo on Railway or Render, add the same env vars in
their dashboard, deploy. Both auto-detect the FastAPI app via `uvicorn app.main:app`.

## Cost note
Gemini 2.0 Flash is priced per-token and cheap enough that even a high-volume
week (dozens of proposals) costs well under $1 in API spend — not a meaningful
line item against the value it unlocks.

## What I'd build next with more time
- Real similarity/embedding match for catalog items instead of giving the LLM
  the full catalog in-context (won't scale past ~200 items cleanly)
- Actual GHL API integration for sending the approved proposal, instead of the
  Slack notification standing in for "ready to send"
- A confidence score per line item so Marcus can spot-check only the shaky ones
