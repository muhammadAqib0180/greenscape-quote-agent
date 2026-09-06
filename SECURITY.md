# Security Policy

QuoteFlow Pro is committed to protecting project data and maintaining high security standards.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within QuoteFlow Pro, please report it privately:

1. **Email**: Open a security inquiry via repository maintainers or email `security@quoteflowpro.internal`.
2. **Details**: Include steps to reproduce, affected components, and potential impact.
3. **Response Time**: We acknowledge receipt of vulnerability reports within 24 hours and aim to provide a patch within 5 business days.

## Automated Security Scans

This repository enforces static application security testing (SAST) and dependency auditing on every commit:

- **SAST**: `bandit -r app/` scans Python source code for security flaws.
- **Dependency Audit**: `pip-audit` checks installed packages against known CVE databases.
- **Container Hardening**: Multi-stage Docker builds running under non-root users (`appuser`).
- **Data Validation**: Strict Pydantic schemas prevent SQL injection, malformed JSON injection, or unauthorized parameter mutation.
