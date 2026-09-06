# YouTube AI Assistant

A production-grade, cross-browser browser extension and Cloudflare Python Worker backend with durable video transcript processing, D1 persistent vector storage, multi-tier caching with stampede protection, pseudonymous session quotas, multi-dimensional rate limiting, circuit breaker resilience, readiness probes, authenticated user accounts, verified interactive timestamp citations `[MM:SS]`, and an empirical machine learning evaluation framework.

---

## 1. System Architecture

```text
YouTube Video Detection / Browser Extension (WXT + React + TypeScript)
        │
        ├── Attach X-Request-ID & Bearer Token / Persistent X-Session-ID
        ▼
FastAPI Cloudflare Worker (Python 3.13 / Pyodide WASM Runtime)
        │
        ├── [Rate Limit & Stream Concurrency Control] (Max 1 active stream/session)
        ├── [Authentication & User Quota Check] (30 questions/day, 20 transcripts/day)
        ▼
Durable Video Registry (D1 `videos` table)
        │
        ├── Status: accepted -> processing -> ready / error
        ├── Stored metadata: versions, hash, language, durations
        ▼
Durable Processing Jobs (D1 `processing_jobs` table)
        │
        ├── Single-flight in-flight deduplication
        ├── Bounded retries (max_attempts = 3)
        ├── Stale job recovery for dropped isolate tasks
        ▼
Durable Transcripts Store (D1 `transcripts` table)
        │
        ├── Normalized segments with full start, duration, text
        ├── Multi-language support and cascade deletion
        ▼
Vector Retrieval Engine
        │
        ├── Semantic chunking with token-bounded sliding windows
        ├── Dense 384-dimensional vector embeddings
        ├── Durable Vector Store (D1 `vector_chunks` or Vectorize)
        └── Strict video ID & embedding version isolation
        ▼
Resilient Grounded Generation (SSE)
        │
        ├── Query rewriter resolving conversational pronouns
        ├── Context builder with untrusted evidence framing
        ├── Health-aware LLMRouter with CircuitBreaker failover
        ├── Real-time SSE token streaming
        └── Atomic citation validation & persistence in D1
```

---

## 2. Project Structure

```text
youtube-ai/
├── apps/
│   ├── backend/               # Python 3.13 + FastAPI on Cloudflare Workers
│   │   ├── evaluation/        # ML evaluation engine, metrics, runner
│   │   ├── migrations/        # Sequential D1 SQL migrations (0001-0006)
│   │   ├── src/               # Application source (API, core, services)
│   │   ├── tests/             # Pytest test suite (unit, security, evaluation)
│   │   ├── pyproject.toml     # Python dependencies and tool configs
│   │   └── wrangler.toml      # Cloudflare Worker bindings (D1, KV, Vectorize)
│   │
│   └── extension/             # WXT + React 18 + TypeScript + Tailwind
│       ├── assets/            # CSS tokens and styling
│       ├── components/        # UI components (Chat, Drawer, Citations, etc.)
│       ├── entrypoints/       # Background, content script, sidepanel
│       ├── services/          # API client, SSE parser, storage
│       ├── tests/             # Vitest unit and integration tests
│       └── wxt.config.ts      # Extension manifest and build configuration
│
├── packages/
│   └── shared-types/          # Typed API and SSE contract shared with extension
│
├── evaluation/
│   ├── datasets/              # Gold benchmark datasets (retrieval, QA, security)
│   └── results/               # Versioned evaluation benchmark outputs
│
├── docs/                      # Technical and operational documentation
├── .github/                   # GitHub Actions CI, CodeQL, and templates
├── .env.example               # Environment variables template
├── package.json               # Monorepo workspaces and root scripts
└── README.md
```

---

## 3. Technology Stack

- **Backend**: Python 3.13 + FastAPI on Cloudflare Workers (`workers-py`, Pyodide WebAssembly runtime)
- **Frontend Extension**: WXT + React 18 + TypeScript + Tailwind CSS
- **Shared Contracts**: `@youtube-ai/shared-types`
- **Database**: Cloudflare D1 (Serverless SQLite at the edge) with versioned SQL schema migrations
- **Cache**: In-Memory with single-flight stampede protection + Cloudflare KV adapter
- **Vector Store**: D1 Persistent Vector Store + Cloudflare Vectorize adapter
- **Evaluation**: Custom evaluation engine with pure-Python stdlib metrics and 22 CI regression tests
- **Browser Targets**:
  - Chrome, Brave, Microsoft Edge, Opera, Vivaldi (Chromium Manifest V3)
  - Mozilla Firefox (Gecko target)

---

## 4. Quick Start & Local Setup

### Prerequisites

- **Python**: `>= 3.13` with [uv](https://docs.astral.sh/uv/)
- **Node.js**: `>= 20.0.0` (tested on Node `22.x`) and `npm`

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/<owner>/youtube-ai.git
   cd youtube-ai
   ```

2. **Install Python backend dependencies**:

   ```bash
   cd apps/backend
   uv sync
   cd ../..
   ```

3. **Install frontend monorepo dependencies**:

   ```bash
   npm install
   ```

4. **Set up local environment variables**:
   ```bash
   cp .env.example .env
   ```

### Running Locally

- **Start backend local server** (FastAPI on Cloudflare Worker runtime):

  ```bash
  npm run dev:backend
  # Runs: uv run pywrangler dev on http://localhost:8787
  ```

- **Start extension in Chromium**:

  ```bash
  npm run dev
  ```

- **Start extension in Firefox**:
  ```bash
  npm run dev:firefox
  ```

For comprehensive step-by-step local testing, see [RUN_LOCALLY.md](RUN_LOCALLY.md).

---

## 5. Automated Verification & Quality Gates

The repository enforces strict quality gates across backend and extension workspaces:

```bash
# 1. Backend tests & type checking (159 passed)
cd apps/backend
uv run pytest tests/ -v
uv run mypy src evaluation
uv run ruff check .
uv run ruff format --check .
cd ../..

# 2. Extension tests & code quality (85 passed)
npm run test:extension
npm run typecheck
npm run lint
npm run format

# 3. Production extension builds
npm run build
npm run build:firefox
```

---

## 6. API Endpoints

### Core Service & Health

| Method | Path             | Description                                          |
| :----- | :--------------- | :--------------------------------------------------- |
| `GET`  | `/api/v1/health` | Lightweight liveness probe                           |
| `GET`  | `/api/v1/ready`  | Readiness check for D1, Cache, Vector Store, and LLM |

### Authentication & Accounts

| Method   | Path                    | Description                                      |
| :------- | :---------------------- | :----------------------------------------------- |
| `POST`   | `/api/v1/auth/register` | Register user account with PBKDF2 password hash  |
| `POST`   | `/api/v1/auth/login`    | Authenticate and receive access & refresh tokens |
| `POST`   | `/api/v1/auth/refresh`  | Rotate refresh token and issue new access token  |
| `GET`    | `/api/v1/auth/me`       | Retrieve authenticated user profile              |
| `POST`   | `/api/v1/auth/logout`   | Invalidate active session and refresh token      |
| `DELETE` | `/api/v1/auth/account`  | Delete account with cascading user data deletion |

### Video & Transcript Lifecycle

| Method | Path                                 | Description                                              |
| :----- | :----------------------------------- | :------------------------------------------------------- |
| `POST` | `/api/v1/videos`                     | Register video and enqueue transcript acquisition        |
| `GET`  | `/api/v1/videos/:videoId`            | Get transcript processing and retrieval readiness status |
| `GET`  | `/api/v1/videos/:videoId/transcript` | Retrieve durable normalized transcript                   |
| `POST` | `/api/v1/videos/:videoId/retrieval`  | Direct semantic search over video chunks                 |

### Conversations & Grounded Q&A

| Method   | Path                                      | Description                                   |
| :------- | :---------------------------------------- | :-------------------------------------------- |
| `POST`   | `/api/v1/videos/:videoId/conversations`   | Create a new conversation thread              |
| `GET`    | `/api/v1/videos/:videoId/conversations`   | List conversation threads for a video         |
| `GET`    | `/api/v1/conversations/:id`               | Get conversation details with message history |
| `PATCH`  | `/api/v1/conversations/:id`               | Rename conversation title                     |
| `DELETE` | `/api/v1/conversations/:id`               | Delete conversation and its messages          |
| `POST`   | `/api/v1/videos/:videoId/ask`             | Grounded question answering (JSON)            |
| `POST`   | `/api/v1/videos/:videoId/ask?stream=true` | Server-Sent Events (SSE) token streaming      |

### Admin Maintenance

| Method | Path                    | Description                                             |
| :----- | :---------------------- | :------------------------------------------------------ |
| `POST` | `/api/v1/admin/cleanup` | Execute data retention cleanup (Requires `X-Admin-Key`) |

---

## 7. Documentation

- [docs/product.md](docs/product.md): Product specification and feature guidelines.
- [docs/ui.md](docs/ui.md): Design system tokens, typography scale, and WCAG accessibility.
- [docs/evaluation.md](docs/evaluation.md): ML evaluation methodology, metrics, and error taxonomy.
- [docs/benchmarks.md](docs/benchmarks.md): Gold benchmark datasets and baseline scores.
- [docs/deployment.md](docs/deployment.md) & [docs/deployment-checklist.md](docs/deployment-checklist.md): Production deployment runbooks.
- [docs/security.md](docs/security.md) & [SECURITY.md](SECURITY.md): Security architecture and disclosure policy.
- [docs/privacy.md](docs/privacy.md): Privacy guarantees and data handling.
- [docs/api.md](docs/api.md): Detailed API contract specification.

---

## 8. Security Notice

- Never commit `.env` or configuration files containing credentials to version control.
- All production secrets must be stored securely using Cloudflare Secrets (`npx wrangler secret put <KEY>`).
- The browser extension contains zero client-side credentials or administrative access keys.

---

## 9. License

No project license selected. All rights reserved.
