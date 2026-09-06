import io
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class ProposalPDF(FPDF):
    def header(self):
        # Header banner
        self.set_fill_color(30, 77, 53)  # Dark green
        self.rect(0, 0, 210, 28, "F")
        self.set_y(8)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "  QUOTEFLOW PRO -- FORMAL PROPOSAL DRAFT", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(200, 235, 215)
        self.cell(0, 4, "  Autonomous AI Proposal Engine for High-Ticket Trade Contractors", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f"QuoteFlow Pro | Confidential Proposal | Page {self.page_no()}/{{nb}}", align="C")



def generate_proposal_pdf(proposal: dict) -> bytes:
    """Generates a clean PDF binary for a given proposal record."""
    pdf = ProposalPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    client_name = proposal.get("client_name", "Valued Client")
    subtotal = proposal.get("subtotal", 0.0) or 0.0
    status = (proposal.get("status") or "draft").upper()
    extracted = proposal.get("extracted_items") or {}
    summary = extracted.get("notes_summary", "") if isinstance(extracted, dict) else ""
    line_items = extracted.get("line_items", []) if isinstance(extracted, dict) else []
    special_conditions = extracted.get("special_conditions", []) if isinstance(extracted, dict) else []
    needs_render = proposal.get("needs_render", False)

    # Client & Metadata Box
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, f"Proposal for: {client_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(100, 100, 100)
    created_at = (proposal.get("created_at") or "")[:10]
    pdf.cell(0, 5, f"Date: {created_at if created_at else 'Current'} | Status: {status} | Proposal ID: #{proposal.get('id', 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Summary
    if summary:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(45, 106, 79)
        pdf.cell(0, 6, "PROJECT SCOPE SUMMARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, summary)
        pdf.ln(4)

    # Special Flags / Conditions
    if special_conditions or needs_render:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(180, 100, 20)
        pdf.cell(0, 6, "SPECIAL CONDITIONS & REQUIREMENTS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        if needs_render:
            pdf.cell(0, 5, "- ATTN: 3D Architectural Render Required (Subtotal > $30,000 threshold)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for cond in special_conditions:
            pdf.cell(0, 5, f"- {cond}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    # Line Items Table
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(45, 106, 79)
    pdf.cell(0, 6, "ESTIMATED LINE ITEMS & PRICING", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Table Header
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(210, 220, 230)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(90, 7, " Item Description", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="L", fill=True)
    pdf.cell(30, 7, "Quantity", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C", fill=True)
    pdf.cell(35, 7, "Unit Price", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="R", fill=True)
    pdf.cell(35, 7, "Total", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R", fill=True)

    # Table Rows
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    for item in line_items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0.0)
        line_total = item.get("line_total", 0.0)

        pdf.cell(90, 6, f" {name[:45]}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
        pdf.cell(30, 6, f"{qty:g}", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
        pdf.cell(35, 6, f"${unit_price:,.2f} ", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="R")
        pdf.cell(35, 6, f"${line_total:,.2f} ", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")

    # Subtotal Row
    pdf.set_fill_color(230, 245, 235)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 77, 53)
    pdf.cell(155, 8, "TOTAL ESTIMATED PROPOSAL ", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="R", fill=True)
    pdf.cell(35, 8, f"${subtotal:,.2f} ", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R", fill=True)

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, "Terms & Approvals: All quotes remain valid for 30 days from issue date. Proposals are subject to final site inspection verification prior to mobilization. Approved proposals trigger project milestone setup.")

    output_bytes = pdf.output()
    if isinstance(output_bytes, (str, bytearray)):
        return bytes(output_bytes) if isinstance(output_bytes, bytearray) else output_bytes.encode('latin1')
    return output_bytes
