# Changelog

All notable changes to Greenscape Pro — Quote & Proposal Accelerator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
