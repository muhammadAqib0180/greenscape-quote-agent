# Contributing to QuoteFlow Pro

Thank you for contributing to QuoteFlow Pro — Autonomous AI Proposal Accelerator! We welcome community contributions, bug reports, and feature requests.

---

## 🚀 Quick Setup

1. **Fork & Clone** the repository:
   ```bash
   git clone https://github.com/your-username/quoteflow-pro.git
   cd quoteflow-pro
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt pytest pytest-cov ruff black bandit pyright fpdf2
   ```

---

## 🧪 Testing Guidelines

All contributions must pass the automated test suite. The test suite runs **without requiring external API credentials** by setting `APP_ENV=test`:

```bash
# Windows PowerShell:
$env:APP_ENV="test"; pytest

# Linux / macOS / Bash:
APP_ENV=test pytest
```

---

## 🧹 Code Quality, Formatting & Security Standards

Verify code quality before submitting a Pull Request:

### 1. Code Formatter (Black / Ruff)
```bash
ruff format --check app/
# or
black --check app/
```

### 2. Linter (Ruff)
```bash
ruff check app/
```

### 3. Static Application Security Testing (SAST - Bandit)
```bash
bandit -r app/
```

---

## 📦 Versioning & Release Process

This repository uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
Releases are triggered when a version tag (`v*.*.*`) is pushed to `main`.
See [`CHANGELOG.md`](CHANGELOG.md) for version release history.
