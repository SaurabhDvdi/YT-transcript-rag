# Local Run & Setup Guide

This guide walks you through setting up, developing, and testing the **YouTube AI Assistant Browser Extension** and its **Cloudflare Workers Python Backend** locally across Chromium browsers (Google Chrome, Brave, Microsoft Edge, Opera, Vivaldi) and Mozilla Firefox.

---

## 1. Prerequisites

- **Node.js**: `v20.0.0` or later (tested on Node `v22.x`)
- **npm**: `v9.0.0` or later (tested on npm `v11.x`)
- **Python**: `3.13` or later
- **uv**: Fast Python package installer and runner ([installation instructions](https://docs.astral.sh/uv/))
- A supported browser:
  - Google Chrome, Brave, Microsoft Edge, Opera, or Vivaldi (Chromium)
  - Mozilla Firefox (Gecko)

Verify your environment:

```bash
node -v
npm -v
python --version
uv --version
```

---

## 2. Installation

Clone the repository and install dependencies:

```bash
# 1. Clone repository
git clone https://github.com/<owner>/youtube-ai.git
cd youtube-ai

# 2. Install Node.js dependencies across all workspaces
npm install

# 3. Synchronize Python virtual environment and dependencies for backend
cd apps/backend
uv sync
cd ../..

# 4. Copy environment configuration template
cp .env.example .env
```

---

## 3. Local Development (Dual-Terminal Workflow)

For active local development with the live backend and hot-reloading browser extension, use two terminal windows:

### Terminal 1: Python Backend (Cloudflare Worker)

```bash
npm run dev:backend
# Or run directly in apps/backend:
# cd apps/backend && uv run pywrangler dev
```

The backend starts on `http://localhost:8787` with:

- Pyodide WebAssembly Python Worker runtime
- In-memory D1 SQLite database & Vector Store
- Mock AI provider enabled for development and testing

Verify the backend is running:

```bash
curl http://localhost:8787/api/v1/health
# Response: {"status":"ok","service":"youtube-ai-api","version":"0.1.0"}
```

### Terminal 2: Browser Extension (WXT Hot-Reloading)

For **Chromium browsers** (Chrome, Brave, Edge, Opera, Vivaldi):

```bash
npm run dev
```

> WXT starts Vite in extension development mode, launches a clean Chromium profile with the extension pre-installed, and hot-reloads on source changes.

For **Mozilla Firefox**:

```bash
npm run dev:firefox
```

---

## 4. Manual Installation of Production Builds

If you want to test built production bundles directly in your browser:

1. Build the production bundles:

```bash
# Build Chromium bundle (Manifest V3)
npm run build

# Build Firefox bundle
npm run build:firefox
```

2. Load into **Google Chrome / Brave / Edge / Opera / Vivaldi**:
   - Open `chrome://extensions` (or `brave://extensions`, `edge://extensions`).
   - Enable **Developer mode** (toggle in upper right).
   - Click **Load unpacked**.
   - Select the directory: `apps/extension/.output/chrome-mv3`.

3. Load into **Mozilla Firefox**:
   - Open `about:debugging#/runtime/this-firefox`.
   - Click **Load Temporary Add-on...**.
   - Select the file: `apps/extension/.output/firefox-mv2/manifest.json`.

4. Use the Extension on YouTube:
   - Navigate to any YouTube video (e.g., `https://www.youtube.com/watch?v=...`).
   - Click the **YouTube AI Assistant** icon in the browser toolbar to open the side panel.
   - The extension detects the active video, acquires the transcript, and enables grounded Q&A with clickable timestamp citations.

---

## 5. Running Test Suites & Quality Checks

All quality gates can be executed from the root directory:

```bash
# 1. Run all tests across monorepo (159 backend + 85 extension)
npm test

# 2. Run backend test suite directly
cd apps/backend
uv run pytest tests/ -v
cd ../..

# 3. Run extension Vitest suite directly
npm run test:extension

# 4. Strict Type Checking (Mypy for Python + tsc for TypeScript)
npm run typecheck
cd apps/backend && uv run mypy src evaluation && cd ../..

# 5. Linting (Ruff for Python + ESLint for TypeScript/React)
npm run lint
cd apps/backend && uv run ruff check . && cd ../..

# 6. Code Formatting (Prettier + Ruff format check)
npm run format
cd apps/backend && uv run ruff format --check . && cd ../..
```

---

## 6. Running the Machine Learning Benchmark Suite

Execute the reproducible evaluation harness measuring retrieval recall, MRR, groundedness, hallucination rate, and citation validity:

```bash
cd apps/backend
uv run python -m evaluation.run
```

Results are generated in:

- `evaluation/results/latest.json`
- `evaluation/results/latest.md`
