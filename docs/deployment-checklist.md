# Production Deployment Checklist & Runbook

This document details the step-by-step production deployment procedure, secret provisioning, D1 database migration execution, smoke testing, and rollback strategy for the YouTube AI Assistant backend.

---

## 1. Pre-Deployment Verification

Before initiating deployment to Cloudflare Workers, all automated quality gates must pass locally:

```bash
# 1. Backend tests, types, and formatting
cd apps/backend
uv run pytest tests/ -v
uv run mypy src evaluation
uv run ruff check .
uv run ruff format --check .

# 2. Extension builds and tests
cd ../..
npm run test:extension
npm run typecheck
npm run lint
npm run format
npm run build
npm run build:firefox
```

---

## 2. Cloudflare Resource Provisioning

Ensure the required Cloudflare resources exist in your Cloudflare account:

1. **D1 Database**:

   ```bash
   npx wrangler d1 create youtube-ai-db
   ```

   Note the generated `database_id` and update `database_id` in [apps/backend/wrangler.toml](apps/backend/wrangler.toml) under `[env.production]`.

2. **KV Namespace**:

   ```bash
   npx wrangler kv:namespace create CACHE_KV
   ```

   Note the generated namespace ID and update `id` under `[[kv_namespaces]]`.

3. **Vectorize Index (Optional / if enabled)**:
   ```bash
   npx wrangler vectorize create youtube-ai-vectors --dimensions=384 --metric=cosine
   ```

---

## 3. Secret Provisioning

Production secrets must NEVER be committed to version control. Provision them securely using Wrangler:

```bash
cd apps/backend

# 1. Authentication Token Secret (minimum 32 random characters)
npx wrangler secret put AUTH_TOKEN_SECRET

# 2. Admin API Key (minimum 16 random characters)
npx wrangler secret put ADMIN_API_KEY

# 3. AI Provider Credentials (at least one required for live inference)
npx wrangler secret put GEMINI_API_KEY
# OR for Cloudflare Workers AI:
npx wrangler secret put CF_ACCOUNT_ID
npx wrangler secret put CF_API_TOKEN
```

---

## 4. D1 Database Migrations

Apply versioned migrations to the production D1 database before deploying worker code:

```bash
cd apps/backend

# List unapplied migrations
npx wrangler d1 migrations list DB --remote

# Apply migrations sequentially
npx wrangler d1 migrations apply DB --remote
```

> [!CAUTION]
> Never run `DROP TABLE` or destructive resets in production. Migrations (`0001` through `0006`) are strictly additive and backwards-compatible.

---

## 5. Worker Deployment

Deploy the Python Worker to Cloudflare:

```bash
cd apps/backend
uv run pywrangler deploy
```

---

## 6. Post-Deployment Smoke Test

Verify the deployment with live requests against the deployed URL (`https://<worker-domain>`):

1. **Health Check**:

   ```bash
   curl -i https://<worker-domain>/api/v1/health
   # Expected: HTTP 200 OK, {"status": "ok", "service": "youtube-ai-api", ...}
   ```

2. **Readiness Probe**:

   ```bash
   curl -i https://<worker-domain>/api/v1/ready
   # Expected: HTTP 200 OK, {"status": "ready", "database": "connected", ...}
   ```

3. **CORS Preflight Test**:
   ```bash
   curl -i -X OPTIONS https://<worker-domain>/api/v1/videos/dQw4w9WgXcQ/status \
     -H "Origin: chrome-extension://abcdefghijklmnop" \
     -H "Access-Control-Request-Method: GET"
   # Expected: Access-Control-Allow-Origin header matching extension
   ```

---

## 7. Rollback Procedure

If unexpected errors occur after deployment:

1. **Rollback Worker Version**:
   Cloudflare Workers supports instant zero-downtime rollback to the prior version:
   ```bash
   npx wrangler rollback [DEPLOYMENT_ID]
   ```
2. **Verify Restored Version**:
   Repeat health check on `/api/v1/health`.
3. **Database Considerations**:
   Because D1 migrations are additive (new tables and columns only), the previous Worker version continues operating without requiring database rollback.
