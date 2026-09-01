import os
import httpx


def notify_proposal_approved(proposal: dict) -> None:
    """Fires when Marcus approves a draft. Replaces the manual Slack pings
    Jenna currently sends 5-10x/day to check on proposal status."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return  # no-op if not configured, don't crash the approval flow

    render_note = " (render required before send)" if proposal.get("needs_render") else ""
    text = (
        f"✅ Proposal approved for *{proposal['client_name']}*\n"
        f"Subtotal: ${proposal['subtotal']:,.2f}{render_note}\n"
        f"Summary: {proposal.get('extracted_items', {}).get('notes_summary', '')}"
    )

    try:
        httpx.post(webhook_url, json={"text": text}, timeout=5)
    except httpx.HTTPError:
        pass  # notification failure shouldn't block the approval itself
