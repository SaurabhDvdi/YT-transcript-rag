# Production Release Readiness Checklist

## 1. Automated Quality Gates

| Check                    | Tool / Command                     | Required Status          | Actual Status |
| :----------------------- | :--------------------------------- | :----------------------- | :------------ |
| **Backend Test Suite**   | `uv run pytest tests/ -v`          | 100% Passing (137 tests) | ✅ Passed     |
| **Security Test Suite**  | `uv run pytest tests/security/ -v` | 100% Passing (14 tests)  | ✅ Passed     |
| **Backend Static Types** | `uv run mypy src`                  | 0 Errors (100 files)     | ✅ Passed     |
| **Backend Linting**      | `uv run ruff check src/ tests/`    | 0 Warnings / Errors      | ✅ Passed     |
| **Frontend Test Suite**  | `npm run test:extension`           | 100% Passing (67 tests)  | ✅ Passed     |
| **Monorepo Typecheck**   | `npm run typecheck`                | 0 Errors                 | ✅ Passed     |
| **Frontend Linting**     | `npm run lint`                     | 0 Errors                 | ✅ Passed     |
| **Prettier Formatting**  | `npm run format`                   | 100% Formatted           | ✅ Passed     |
| **Chrome MV3 Build**     | `npm run build`                    | 0 Build Errors (265 kB)  | ✅ Passed     |
| **Firefox MV2 Build**    | `npm run build:firefox`            | 0 Build Errors (265 kB)  | ✅ Passed     |

---

## 2. Secrets & Environment Configuration Checklist

- [ ] **`ENVIRONMENT`**: Set to `"production"`.
- [ ] **`AUTH_TOKEN_SECRET`**: Set to a cryptographically-random 64-character hex string generated via `openssl rand -hex 32` (cannot use dev default).
- [ ] **`ADMIN_API_KEY`**: Set to a high-entropy secret string at least 32 characters long.
- [ ] **`ALLOWED_ORIGINS`**: Set to specific extension IDs only (e.g. `chrome-extension://<id>,moz-extension://<id>`). Wildcard `*` and `localhost` are strictly rejected.
- [ ] **`GEMINI_API_KEY`** or **`CF_ACCOUNT_ID` + `CF_API_TOKEN`**: Production AI provider credentials configured via `wrangler secret put`.

---

## 3. Database & Storage Migrations Checklist

- [ ] Run all D1 migrations in chronological order:
  - `0001_initial.sql`
  - `0002_jobs_and_usage.sql`
  - `0003_persistent_vector_store.sql`
  - `0004_d1_conversations.sql`
  - `0005_auth_tables.sql`
  - `0006_conversation_sessions.sql`
- [ ] Verify foreign keys and indices (`idx_conversations_user`, `idx_conversations_session`, `idx_auth_sessions_hash`).
- [ ] Verify Cloudflare KV namespace binding (`CACHE_KV`).

---

## 4. Web Store Deployment Checklist

- [ ] **Chrome Web Store:**
  - Zip directory: `apps/extension/.output/chrome-mv3`
  - Manifest version: `0.1.0`
  - Verify icon sizes: 16x16, 32x32, 48x48, 128x128 present.
  - Permissions justified in store listing (`storage`, `sidepanel`).
- [ ] **Firefox Add-ons (AMO):**
  - Zip directory: `apps/extension/.output/firefox-mv2`
  - Verify sidebar action functionality.
