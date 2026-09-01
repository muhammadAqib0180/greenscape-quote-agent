import os
import httpx


def notify_proposal_approved(proposal: dict) -> None:
    """Fires when Marcus approves a draft."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    if proposal.get("needs_render"):
        text = (
            f"🎨 *ATTN @Carlos — 3D Render Required!*\n"
            f"✅ Proposal approved for *{proposal['client_name']}*\n"
            f"Subtotal: *${proposal['subtotal']:,.2f}* (Exceeds $30k threshold)\n"
            f"Summary: {proposal.get('extracted_items', {}).get('notes_summary', '')}"
        )
    else:
        text = (
            f"✅ Proposal approved for *{proposal['client_name']}*\n"
            f"Subtotal: *${proposal['subtotal']:,.2f}*\n"
            f"Summary: {proposal.get('extracted_items', {}).get('notes_summary', '')}"
        )

    try:
        httpx.post(webhook_url, json={"text": text}, timeout=5)
    except httpx.HTTPError:
        pass
