# Cloudflare Workers Deployment Runbook

## 1. Prerequisites

- Node.js >= 20.x
- Python >= 3.13
- Wrangler CLI (`npm install -g wrangler` or `npx wrangler`)
- Cloudflare Account with Workers Paid (for D1, KV, Vectorize, and Python Workers)

---

## 2. Infrastructure Setup & Bindings

### 2.1 Cloudflare D1 Database

Create the production D1 database:

```bash
npx wrangler d1 create youtube-ai-db
```

Record the database ID and configure in `apps/backend/wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "youtube-ai-db"
database_id = "<DATABASE_ID>"
```

Apply all migrations:

```bash
npx wrangler d1 migrations apply youtube-ai-db --remote
```

### 2.2 Cloudflare KV Namespace

Create the production KV namespace:

```bash
npx wrangler kv:namespace create CACHE_KV
```

Configure binding in `apps/backend/wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "CACHE_KV"
id = "<KV_NAMESPACE_ID>"
```

---

## 3. Production Secrets Provisioning

Set required secrets using Wrangler (never commit secrets to git):

```bash
# 1. JWT Authentication Secret (must be >= 32 characters)
npx wrangler secret put AUTH_TOKEN_SECRET

# 2. Administrative Operations Key
npx wrangler secret put ADMIN_API_KEY

# 3. AI Providers (configure Gemini or Cloudflare Workers AI)
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put CF_ACCOUNT_ID
npx wrangler secret put CF_API_TOKEN
```

---

## 4. Deploying Backend Cloudflare Worker

From `apps/backend/`:

```bash
npx wrangler deploy
```

Verify deployment:

```bash
curl -i https://<worker-subdomain>.workers.dev/api/v1/health
curl -i https://<worker-subdomain>.workers.dev/api/v1/ready
```

---

## 5. Scheduled Maintenance / Cron Triggers

Configure operational retention and cleanup cron in `wrangler.toml`:

```toml
[triggers]
crons = ["0 3 * * *"]  # Daily at 03:00 UTC
```

The scheduled handler triggers `CleanupService.run_cleanup()`, pruning stale jobs and usage events older than retention thresholds.
