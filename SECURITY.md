# Security Policy

QuoteFlow Pro is committed to protecting project data and maintaining high security standards.
A complete threat analysis is documented in [`THREAT_MODEL.md`](THREAT_MODEL.md).

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within QuoteFlow Pro, please report it privately:

1. **GitHub**: Open a private security advisory via *Security → Advisories* in the repository.
2. **Email**: `security@quoteflowpro.internal` — include steps to reproduce, affected components, and potential impact.
3. **Response Time**: We acknowledge receipt within 24 hours and aim to provide a patch within 5 business days.

## Automated Security Scans

This repository enforces static application security testing (SAST) and dependency auditing on every commit:

- **SAST**: `bandit -r app/` scans Python source code for security flaws.
- **Dependency Audit**: `pip-audit` checks installed packages against known CVE databases.
- **Reproducible Builds**: `requirements.lock` pins all transitive dependencies to prevent silent version drift.
- **Container Hardening**: Multi-stage Docker builds running under non-root users (`appuser`).
- **Data Validation**: Strict Pydantic schemas prevent SQL injection, malformed JSON injection, or unauthorized parameter mutation.

## Secret Management

Secrets are **never hardcoded** in source code (verified by `bandit` on every CI push).
All credentials are runtime environment variables sourced from `.env` (local development)
or a secrets manager (production).

For production deployments, refer to the **Secret Manager Integration Guide** in
[`THREAT_MODEL.md §7`](THREAT_MODEL.md#7-secret-manager-integration-guide) for
step-by-step instructions for Google Cloud Secret Manager, Doppler, or AWS Secrets Manager.

## Threat Model

A comprehensive STRIDE threat model covering all trust boundaries, asset inventory,
known controls, and recommended security enhancements is maintained in
[`THREAT_MODEL.md`](THREAT_MODEL.md).

Key security controls in place:

| Control | Implementation |
|---|---|
| Input validation | Pydantic models on all API boundaries |
| Zero hardcoded secrets | Confirmed by `bandit` SAST on every push |
| LLM output guardrails | All Gemini responses validated against schema before DB write |
| Revision audit trail | Full AI rewrite history stored in `revision_history` JSONB |
| Human approval gate | No automated client delivery; every proposal requires estimator review |
