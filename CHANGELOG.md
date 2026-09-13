# Changelog

All notable changes to Greenscape Pro — Quote & Proposal Accelerator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-13

### Added
- **AI Proposal Rewrite Engine** (`POST /api/v1/proposals/{id}/rewrite`): Accepts free-text revision instructions and re-runs the proposal scope through Gemini Flash, updating the stored proposal with the revised line items, subtotal, and special conditions.
- **Revision History Audit Trail**: Every AI rewrite is stored as a `RevisionEntry` in a `revision_history` JSONB column with full item-level diffs (added/removed/modified line items) and subtotal deltas.
- **Revision History API** (`GET /api/v1/proposals/{id}/rewrite/history`): Returns the full chronological rewrite audit trail for any proposal.
- **Revision History UI** (`GET /proposals/{id}/history`): Beautiful timeline page showing each rewrite with color-coded diff pills and subtotal delta visualization.
- **`/healthz` liveness endpoint**: Returns `{"status": "ok"}` with no external dependencies — used by load balancers and the CI docker-build verification job.
- **`/readyz` readiness endpoint**: Returns 200 when the database is reachable, 503 otherwise.
- **`app/logging_config.py`**: Extracted `JsonFormatter` and `CorrelationIdMiddleware` into a dedicated module for reusability and cleaner separation of concerns.
- **`app/routes/web.py`**: All HTML-serving routes extracted from `app/main.py` into a dedicated web router, making `main.py` a thin wiring layer (~50 LOC).
- **`THREAT_MODEL.md`**: Comprehensive STRIDE threat model covering all four trust boundaries, asset inventory, controls matrix, recommended enhancements, secret manager integration guide (GCP / Doppler / AWS), and incident response runbook.
- **`RewriteProposalRequest` and `RevisionEntry` Pydantic models** in `app/models.py`.
- **`get_revision_history()` and `add_revision_history()`** in `app/db.py` and `app/db_fake.py`.
- **`rewrite_proposal()` function** in `app/llm.py` with a dedicated `REWRITE_SYSTEM_PROMPT`.
- **`append_revision` Postgres function** in `supabase_schema.sql` for atomic JSONB array appends.
- **Revision count column** in `GET /api/v1/proposals/export/csv`.
- **`tests/test_rewrite.py`**: 26 tests covering the rewrite API, error paths, diff logic, and revision history UI.
- **`tests/test_routes_web.py`**: 30+ tests covering all web router routes.

### Changed
- **`requirements.lock`**: Now pins all transitive dependencies (not just direct deps) for reproducible builds.
- **CI pipeline**: All test and audit jobs now install from `requirements.lock` instead of `requirements.txt`. Docker build job now performs a `curl -f /healthz` liveness verification after container start.
- **`.env.example`**: Added missing `APP_ENV` and `PORT` variables with explanatory comments.
- **`SECURITY.md`**: Updated to reference `THREAT_MODEL.md` and document secret manager guidance.
- **`app/main.py`**: Refactored to thin wiring layer; all route logic moved to dedicated routers.

### Removed
- Inline route logic from `app/main.py` (moved to `app/routes/web.py`).
- Inline `JsonFormatter` and `CorrelationIdMiddleware` from `app/main.py` (moved to `app/logging_config.py`).

---

## [1.0.0] - 2026-09-06

### Added
- **AI Scope Parsing & Catalog Mapping**: Automated raw field notes parsing against a 200+ SKU landscaping pricing catalog using Gemini 3.6 Flash.
- **Line-Item AI Confidence Ratings**: Per-item confidence scoring (`High`, `Medium`, `Low`) to streamline human spot-checks.
- **Interactive Proposal Editor**: Modal interface for adjusting quantities, line item prices, or adding catalog items before approval.
- **Client-Ready PDF Proposal Export**: Instant PDF quote generation engine powered by `fpdf2`.
- **RESTful OpenAPI Endpoints**: Comprehensive `/api/v1/` routes with interactive Swagger UI documentation (`/docs`).
- **Interactive Catalog Explorer**: `/catalog` page with real-time client-side search.
- **GoHighLevel & Slack Webhooks**: Automated notification and CRM synchronization on proposal approval.
- **Hardened Dockerfile**: Multi-stage production container setup with non-root security context (`USER appuser`) and health checks.
- **Static Application Security Testing (SAST)**: Configured `bandit` SAST scanner and code formatting checks (`black` / `ruff format`).
- **Comprehensive API & Contributing Guides**: Added [`docs/API.md`](docs/API.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).
