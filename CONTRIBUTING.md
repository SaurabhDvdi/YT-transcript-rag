# Contributing to YouTube AI Assistant

Thank you for your interest in contributing! This document outlines local setup, coding standards, testing, and our pull request process.

---

## 1. Prerequisites

- **Python**: `>= 3.13` with [uv](https://docs.astral.sh/uv/) installed.
- **Node.js**: `>= 20.0.0` (tested on Node `22.x`) with `npm`.
- **Wrangler**: `uv run pywrangler` or `npx wrangler`.

---

## 2. Local Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/<owner>/youtube-ai.git
   cd youtube-ai
   ```

2. **Install dependencies**:

   ```bash
   # Python backend dependencies
   cd apps/backend
   uv sync
   cd ../..

   # Monorepo and extension dependencies
   npm install
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

---

## 3. Development Workflow

- **Run backend locally**:
  ```bash
  npm run dev:backend
  # Or: cd apps/backend && uv run pywrangler dev
  ```
- **Run extension in Chromium**:
  ```bash
  npm run dev
  ```
- **Run extension in Firefox**:
  ```bash
  npm run dev:firefox
  ```

---

## 4. Quality & Testing

Before opening a pull request, all automated checks must pass:

```bash
# 1. Backend tests & type checking
cd apps/backend
uv run pytest tests/ -v
uv run mypy src evaluation
uv run ruff check .
uv run ruff format --check .
cd ../..

# 2. Extension tests & code quality
npm run test:extension
npm run typecheck
npm run lint
npm run format

# 3. Production extension builds
npm run build
npm run build:firefox
```

---

## 5. Branching & Pull Requests

1. Branch from `master` using descriptive names: `fix/issue-description` or `feat/feature-name`.
2. Follow commit message conventions (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
3. Ensure no local `.env` files, credentials, or generated files (`.output/`, `node_modules/`, `.venv/`) are included in commits.
4. Open a Pull Request referencing any relevant issues.

---

## 6. Security Reporting

Please do NOT submit security vulnerabilities via public pull requests or issues. See [SECURITY.md](SECURITY.md) for private disclosure instructions.
