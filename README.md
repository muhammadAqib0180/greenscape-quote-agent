# QuoteFlow Pro — Autonomous AI Proposal Accelerator

![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688.svg)
![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)
![Tests](https://img.shields.io/badge/tests-62%20passed-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

Turns raw site-walk field notes into structured, catalog-priced proposal drafts in seconds — cutting the quote turnaround cycle from **6–9 days to under 2 minutes** and recovering over **$1M in lost annual revenue** for high-ticket trade contractors.

## Why this system
In high-ticket contracting ($28K avg job size), **speed to quote wins the deal**. Founders and estimators are stuck spending 20+ hours a week in Excel spreadsheets manually pricing field notes. QuoteFlow Pro automates the interpretation step (matching messy notes to catalog SKUs) while keeping the human as the final approver before anything sends.

## Key Features & Enterprise Capabilities

- ⚡ **AI Scope Parsing & Catalog Mapping**: Gemini Flash parses raw, unstructured text or voice field notes into catalog-mapped line items.
- 🎯 **Line-Item AI Confidence Ratings**: Evaluates mapping accuracy per line item (`High`, `Medium`, `Low`) to highlight items needing human spot-checks.
- ✏️ **Interactive Proposal Editor**: Inline drawer to adjust quantities, unit prices, add missing catalog items, or update notes before approval.
- 📊 **Live Analytics & Telemetry Dashboard**: Real-time insights at `/analytics` tracking pipeline value, latency reduction, and confidence distribution.
- 📄 **Client-Ready PDF Proposal Export**: Instant PDF quote generator (`fpdf2`) with company branding, terms, subtotal tables, and special conditions.
- 📥 **1-Click Data Export**: CSV export endpoint (`/api/v1/proposals/export/csv`) for spreadsheet reporting.
- 🔌 **RESTful OpenAPI Endpoint Architecture**: Clean `/api/v1/` routes with interactive Swagger documentation (`/docs`).
- 🔍 **Interactive Catalog Explorer**: Search and filter pricing items at `/catalog`.
- ⚡ **Slack & CRM Webhooks**: Automatic Slack notification and GoHighLevel (GHL) CRM integration hook on proposal approval.
- 🎨 **Smart Render Routing**: Proposals over $30K auto-flag `needs_render` for 3D architectural render workflows.
- 🛡️ **SAST & Security Audit**: Built-in `bandit` security scanning and `pip-audit` dependency analysis.

## Architecture & Documentation

- [`docs/API.md`](docs/API.md): Dedicated REST API Endpoint Specifications & cURL Examples.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): Developer Setup, Code Styling (Black/Ruff), Testing & Git Workflow.
- [`SECURITY.md`](SECURITY.md): Security Policy & Vulnerability Disclosure Process.
- [`CHANGELOG.md`](CHANGELOG.md): Release Notes & Semantic Versioning History.

## Setup & Quickstart

### Option A: Quickstart with Docker (No credentials required)
Boot the application immediately in offline test mode using Docker Compose:
```bash
docker compose up
```
Visit `http://localhost:8000` to submit notes, `/proposals` to review/edit, `/analytics` for metrics, and `/catalog` to view prices.

### Option B: Local Python Environment
1. **Supabase**: create a project at supabase.com, then run `supabase_schema.sql` in the SQL Editor to create tables and seed the pricing catalog.
2. **Gemini key**: get one at aistudio.google.com/apikey
3. **Slack webhook**: create one at api.slack.com/apps → Incoming Webhooks → Add to Slack
4. Copy `.env.example` to `.env` and fill in credentials.
5. Install and run locally:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
6. Visit `http://localhost:8000` for main interface, `/proposals` for drafts, `/analytics` for telemetry, `/catalog` for prices, and `/docs` for API documentation.

## Testing & Quality Assurance

The full 62-test suite runs **without any API keys or live services** — all external calls are replaced by an in-memory fake backend and mocked LLM/Slack.

Run tests:
```bash
$env:APP_ENV="test"; pytest
```

To see coverage:
```bash
$env:APP_ENV="test"; pytest --cov=app --cov-report=term-missing
```

`APP_ENV=test` activates `app/db_fake.py` — an in-memory drop-in for Supabase. No external credentials required.
