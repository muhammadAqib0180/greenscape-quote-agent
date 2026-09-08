import os
import sys
from fpdf import FPDF
from fpdf.enums import XPos, YPos

def clean_txt(s: str) -> str:
    """Sanitizes text for standard latin-1 PDF core fonts."""
    replacements = {
        "\u2014": " -- ",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2192": "-->",
        "\u2190": "<--",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class InterviewPDF(FPDF):
    def header(self):
        self.set_fill_color(24, 43, 33)
        self.rect(0, 0, 210, 18, "F")
        self.set_y(4)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, clean_txt("QUOTEFLOW PRO  |  ALESSANDRO INTERVIEW MASTER GUIDE & SCRIPT"), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(10)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(180, 220, 200)
        self.cell(0, 4, clean_txt("Screen-Share Talking Script, Code Breakdown, 5-Agent Roadmap & Scalability"), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(8)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, clean_txt(f"Muhammad Aqib  |  isthispossible.ai Technical Interview  |  Page {self.page_no()}/{{nb}}"), align="C")

    def section_title(self, num, title):
        self.ln(3)
        self.set_fill_color(235, 245, 238)
        self.set_draw_color(45, 106, 79)
        self.set_line_width(0.4)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(25, 75, 50)
        self.cell(0, 6, clean_txt(f"  {num}. {title.upper()}"), border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 8.8)
        self.set_text_color(30, 41, 59)
        self.cell(0, 4.8, clean_txt(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_p(self, text):
        self.set_font("Helvetica", "", 8.2)
        self.set_text_color(45, 55, 72)
        self.multi_cell(0, 4, clean_txt(text))
        self.ln(1.5)

    def speech_box(self, label, text):
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.set_font("Helvetica", "B", 7.8)
        self.set_text_color(15, 118, 110)
        self.cell(0, 4.2, clean_txt(f"  [WHAT TO SAY: {label}]"), border="LTR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "I", 7.8)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 3.8, clean_txt(f'"{text}"'), border="LBR", fill=True)
        self.ln(2)

    def code_expl(self, code_line, explanation):
        self.set_fill_color(241, 245, 249)
        self.set_draw_color(226, 232, 240)
        self.set_font("Courier", "B", 7.5)
        self.set_text_color(15, 23, 42)
        self.cell(0, 4, clean_txt(f"  {code_line}"), border="LTR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 7.8)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 3.6, clean_txt(f"  --> In Plain Words: {explanation}"), border="LBR", fill=True)
        self.ln(1.2)


def build_pdf():
    pdf = InterviewPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # --- TITLE ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(24, 43, 33)
    pdf.cell(0, 6, clean_txt("Master Interview Walkthrough, Code Guide & Future Roadmap"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 8.2)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, clean_txt("Candidate: Muhammad Aqib | Position: AI Agent Engineer | Interviewer: Alessandro Colford (isthispossible.ai)"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # --- SECTION 1 ---
    pdf.section_title("1", "The 20-Minute Game Plan & Time Management")
    pdf.body_p(
        "20 minutes passes very quickly on a screen share. Keep strictly to this structure so you show the product, code, future roadmap, and tests comfortably."
    )

    pdf.set_font("Helvetica", "B", 7.8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(26, 5, "Time Window", 1, 0, "C", True)
    pdf.cell(38, 5, "Stage", 1, 0, "L", True)
    pdf.cell(126, 5, "Key Objective & What You Are Doing", 1, 1, "L", True)

    timetable = [
        ("0:00 - 2:30", "Strategic Intro", "Hook Alessandro with the $1.4M revenue leak. Explain why QuoteFlow was prioritized over marketing."),
        ("2:30 - 8:30", "Live Deployed App", "Show field notes input, Gemini AI extraction, confidence scores, edit drawer, PDF download, and Slack alert."),
        ("8:30 - 13:00", "Code & Architecture", "Switch to VS Code. Walk through models.py, llm.py, main.py, and db_fake.py test isolation."),
        ("13:00 - 16:30", "Future Roadmap", "Explain the 5-Agent Strategy, Dollar-Leverage rankings, Vector RAG scaling, and why marketing was rejected."),
        ("16:30 - 20:00", "Tests & Q&A", "Run pytest (62 tests in 10s). Answer questions calmly and ask Alessandro about client deployment challenges.")
    ]
    pdf.set_font("Helvetica", "", 7.5)
    for t_col, s_col, g_col in timetable:
        pdf.cell(26, 4.8, t_col, 1, 0, "C")
        pdf.cell(38, 4.8, s_col, 1, 0, "L")
        pdf.cell(126, 4.8, g_col, 1, 1, "L")
    pdf.ln(3)

    # --- SECTION 2 ---
    pdf.section_title("2", "Verbatim Step-by-Step Talking Script (Plain English)")

    pdf.sub_title("Step 1: The Intro (Under 2 minutes)")
    pdf.speech_box(
        "Opening Hook",
        "Hi Alessandro, great to meet you! Before jumping into the live app, let me give you the quick business rationale behind QuoteFlow Pro. When analyzing Marcus's landscaping business, he averages $28,000 per project across roughly 150 jobs a year. His constraint is NOT marketing -- his ROAS is 4.5x and he cannot keep up with current leads. His real bottleneck is that after site walks, notes sit in notebooks for 6 to 9 days because Marcus is the only person pricing them manually in Excel. During that delay, 35 to 40% of clients go with faster competitors, costing over $1.4M a year. QuoteFlow Pro solves this exact interpretation bottleneck: it turns raw notes into catalog-priced proposals in seconds, while keeping Marcus in control as the final approver."
    )

    pdf.sub_title("Step 2: Live App Demo")
    pdf.speech_box(
        "Intake Page (http://localhost:8000)",
        "Here is the intake screen. An estimator simply types or pastes raw site-walk notes. Notice how messy these notes can be: shorthand abbreviations, mixed units like square feet and linear feet, and special notes like HOA permits. Let's hit 'Generate Proposal Draft'."
    )
    pdf.speech_box(
        "Proposals Dashboard (/proposals)",
        "In about two seconds, Gemini Flash extracted the scope and mapped every item to our 200+ item pricing catalog. Look at four key things here: First, accurate SKU matching with real unit prices. Second, AI Confidence Ratings: each line is tagged High, Medium, or Low with a plain-English reason so Marcus only needs to double-check uncertain items. Third, because the total exceeds $30,000, it automatically flagged '3D Render Required'. Fourth, it captured the HOA requirement under Special Conditions."
    )
    pdf.speech_box(
        "Interactive Editor & PDF Export",
        "AI should never be an uncontrollable black box. If Marcus wants to adjust a quantity or add another item, he clicks Edit. He can change quantities or prices and hit Save -- the subtotal instantly recalculates. Next, if we click 'Download PDF', our built-in PDF engine generates a clean, branded proposal draft complete with scope summary, itemized tables, and legal terms ready for the homeowner."
    )
    pdf.speech_box(
        "Approval & Slack Automation",
        "When Marcus clicks 'Approve', it updates the status and triggers a Slack webhook. Because this quote exceeded $30,000, the Slack message automatically alerts Carlos: 'Attention @Carlos - 3D Render Required!' so Carlos can begin 3D modeling immediately without Marcus having to write an email."
    )

    # --- SECTION 3 ---
    pdf.section_title("3", "Line-by-Line Code Breakdown in Plain English")
    pdf.body_p(
        "Why app/models.py exists: LLMs output unpredictable text. Pydantic is our bouncer. It guarantees that whatever Gemini outputs strictly conforms to clean numbers, text, and structures before touching the database."
    )

    code_items = [
        ("class LineItem(BaseModel):", "Blueprint for a single billable line item in a proposal (like Pavers or Sod)."),
        ("pricing_item_id: int", "The exact database ID matching our Supabase pricing table SKU."),
        ("name: str", "The human-readable name of the catalog item."),
        ("quantity: float = Field(gt=0)", "'float' allows decimals (2.5 tons). 'gt=0' means Greater Than 0. Prevents zero or negative quantities."),
        ("unit_price: float = Field(gt=0)", "Catalog unit price. Guarded with gt=0 to prevent accidental $0 pricing."),
        ("line_total: float = Field(gt=0)", "Quantity times unit price. Guaranteed positive dollar value."),
        ('confidence: Literal["high", "medium", "low"] = "high"', "Forces the AI to pick only one of these three exact words."),
        ("confidence_reason: Optional[str] = None", "Short 1-sentence reason why that confidence was assigned."),
        ("class ParsedProposal(BaseModel):", "The master contract for the entire quote that Gemini must satisfy."),
        ("client_name: str", "The client or homeowner's name."),
        ("line_items: list[LineItem] = Field(min_length=1)", "Must have at least 1 item. AI cannot generate a useless empty proposal."),
        ("subtotal: float = Field(ge=0)", "Total dollar sum. Must be Greater than or Equal to 0."),
        ("notes_summary: str", "1-to-2 sentence plain summary so Marcus understands the job at a glance."),
        ("special_conditions: list[str] = []", "Non-billable flags like HOA approval, permits, or gate codes."),
        ("raw_notes: str = Field(min_length=10)", "In SubmitNotesRequest: Blocks accidental empty submissions like 'hi' or 'ok'."),
        ("UpdateProposalRequest (all Optional)", "Allows Marcus to update just 1 field in the edit drawer without resending everything.")
    ]
    for c_line, c_expl in code_items:
        pdf.code_expl(c_line, c_expl)

    pdf.sub_title("What is 'Native JSON Mode' and Why Are We Doing It?")
    pdf.body_p(
        "Normal LLMs talk like humans: 'Sure! Here is your quote: ```json ... ``` Hope this helps!'. If an LLM outputs markdown fences or chatting text, json.loads() crashes. Native JSON Mode (response_mime_type='application/json') constrains Gemini at the model level so every single token from the first bracket { to the last } is 100% pure JSON syntax -- zero markdown, zero chatting, zero crashes."
    )

    pdf.sub_title("What is the Purpose of the 62 Tests? Why are we testing?")
    pdf.body_p(
        "Tests are automated checks that act like a picky quality-assurance robot. They prove the software does not break under pressure:\n"
        "- Model Tests: Prove that negative prices or zero quantities are blocked by Pydantic.\n"
        "- LLM Guardrail Tests: Prove that if Gemini fails or returns garbage, the app saves it as a draft with parse_error instead of crashing.\n"
        "- DB & API Tests: Prove that saving, approving, rejecting, and CSV export work without a live database via conftest.py.\n"
        "- Slack & PDF Tests: Prove that quotes >$30k tag @Carlos and PDF quote bytes are valid."
    )

    # --- SECTION 4 ---
    pdf.section_title("4", "The Future Roadmap & The 5-Agent Strategy")
    pdf.body_p(
        "In STRATEGY.md, I ranked 5 AI agents by Dollar Leverage (recoverable revenue), not just what Marcus said out loud:"
    )

    pdf.speech_box(
        "Explaining the 5-Agent Roadmap",
        "Alessandro, beyond this proposal tool, I mapped out a 5-agent ecosystem ranked strictly by ROI:\n"
        "1. Quote & Proposal Accelerator (P0 - Built): Solves the 7-day quote lag, recovering $1.4M/year.\n"
        "2. Post-Sign Milestone Tracker (P1): 8 to 12 projects sit stalled in HOA permits and deposit payments, delaying $300K+ in cash flow. This agent auto-tracks permit portals and sends friendly nudges to homeowners and Jenna.\n"
        "3. Build-Progress Update Agent (P2): When work starts, silence for 4 days makes clients anxious. This agent listens to CompanyCam photo uploads and drafts personal Marcus-voiced progress updates in 1 click.\n"
        "4. Closed-Lost Reactivation Agent (P3): 1,400 past leads sit dormant in GoHighLevel CRM. Re-engaging them with personalized check-ins at a 2% close rate unlocks $784K in latent revenue with zero ad spend.\n"
        "5. Lead Pre-Qualification Voice/SMS Agent (P4): Filters tire-kickers before they take slots on Marcus's calendar."
    )

    pdf.sub_title("Why I Explicitly Rejected the Marketing Agent")
    pdf.body_p(
        "Marcus mentioned marketing as his #4 priority. But he stated twice that ROAS is already 4.5x and he cannot keep up with current leads. Building a marketing agent generates leads he can't fulfill and makes the quote bottleneck worse. It is a clean, data-backed 'No'."
    )

    pdf.sub_title("Technical Scaling Roadmap (Catalog > 500 items)")
    pdf.speech_box(
        "Scaling from In-Context to Vector RAG",
        "Right now, feeding all 200 catalog SKUs into Gemini takes ~3,500 tokens. It costs $0.0003 and takes 1.5s. But if Marcus expands to 2,000 SKUs, putting the whole catalog into the prompt causes latency spikes and LLM attention drift. The production solution is a Two-Stage Vector RAG: store SKUs in Supabase using pgvector and embeddings. When field notes come in, we query the top 20 relevant items via semantic search, and feed only those into Gemini."
    )

    # --- SECTION 5 ---
    pdf.section_title("5", "Anticipated Questions & Bulletproof Simple Answers")

    qa_list = [
        ("Why Gemini Flash instead of GPT-4o or Claude Sonnet?",
         "Three reasons: Speed, Cost, and Accuracy. Flash responds in 1.5 to 2 seconds, giving estimators a snappy real-time experience. For structured catalog mapping, heavy models like GPT-4o are 10 to 15 times more expensive with zero noticeable quality difference. Flash gives 99%+ schema adherence when backed by Pydantic."),
        ("What happens if an estimator mentions an item not in the catalog (e.g. exotic pizza oven)?",
         "The prompt explicitly commands the AI never to invent prices or fake SKUs. If there is no reasonable match, it omits the item. In the UI, Marcus sees the raw notes side-by-side with the quote and can click Edit to manually add a custom item before approving."),
        ("Why keep Marcus in the loop? Why not email the quote to the homeowner automatically?",
         "Because this is high-ticket construction ($28K average job). An unverified AI quote with a missing retaining wall or wrong square footage could cost Marcus $10,000 out of pocket. Keeping Marcus as a 30-second reviewer gives him 10x speed while keeping 100% human quality control."),
        ("How does the $30,000 render threshold work?",
         "In main.py, RENDER_THRESHOLD defaults to 30000. If the subtotal exceeds that, needs_render is set to True. This adds an alert badge in the UI and PDF, and instructs slack.py to mention @Carlos so he immediately starts 3D modeling without waiting for an email."),
        ("How did you ensure reliable cloud deployment?",
         "Cloud platforms like Render or Railway often pass the PORT environment variable with quotes or whitespace, which crashes standard Uvicorn. I built uvicorn_patch.py and start.sh with regex sanitization and fallback to port 8000, plus a multi-stage non-root Dockerfile.")
    ]

    for q, a in qa_list:
        pdf.set_font("Helvetica", "B", 8.2)
        pdf.set_text_color(15, 118, 110)
        pdf.cell(0, 4.2, clean_txt(f"Q: {q}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 7.8)
        pdf.set_text_color(45, 55, 72)
        pdf.multi_cell(0, 3.6, clean_txt(f"Answer: {a}"))
        pdf.ln(1.5)

    # --- SECTION 6 ---
    pdf.section_title("6", "Pre-Call Setup Checklist")
    checklist = [
        "1. Open Browser: Tab 1 (http://localhost:8000), Tab 2 (/proposals), Tab 3 (Downloaded PDF sample).",
        "2. Open VS Code: Have models.py or main.py open. Make sure terminal is zoomed in (Ctrl + +).",
        "3. Test Run pytest: Run $env:APP_ENV='test'; pytest once before the call to make sure it prints '62 passed'.",
        "4. Turn Off Notifications: Close WhatsApp, Discord, Slack, and mute phone notifications.",
        "5. Keep this PDF Open on your second screen or phone for quick reference while talking!"
    ]
    for item in checklist:
        pdf.body_p(f"- {item}")

    output_path = os.path.join(os.path.dirname(__file__), "QuoteFlow_Interview_Complete_Guide.pdf")
    pdf.output(output_path)
    print(f"Successfully generated PDF at: {output_path}")

if __name__ == "__main__":
    build_pdf()
