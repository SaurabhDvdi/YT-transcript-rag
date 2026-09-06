# Production Security Specification & Architecture

## 1. Executive Summary & Security Philosophy

The YouTube AI Assistant is designed with a defense-in-depth security model treating all incoming inputs, browser environments, and external transcripts as untrusted. The backend runs on Cloudflare Workers using Python ASGI (`workers-py`), and the frontend is an extension built with WXT supporting Chrome MV3 and Firefox MV2.

---

## 2. Threat Model & Trust Boundaries

### 2.1 System Trust Boundaries

1. **Client / Browser Extension (Untrusted Boundary):**
   - Content scripts operate in YouTube DOM (hostiled/dynamic environment).
   - Sidepanel runs isolated React UI within extension origin (`chrome-extension://...` or `moz-extension://...`).
   - Extension storage stores access/refresh tokens and anonymous session IDs locally.
2. **API Gateway / Cloudflare Edge (First Line of Defense):**
   - Enforces origin verification (CORS), request rate limits, body size limits (max 1 MB), and security response headers.
   - Extracts and normalizes client IP, session ID, and request ID.
3. **Application & ASGI Layer (Trusted Processing):**
   - Validates HMAC signatures of access tokens, resolves session ownership, enforces quota budgets, and isolates conversations.
4. **Data Persistence (Cloudflare D1 & KV):**
   - Parameterized SQL queries only (no dynamic SQL string interpolation).
   - Hash-only storage of credentials and refresh tokens.
5. **AI Model Providers (External Service Boundary):**
   - Prompts sent to Gemini or Cloudflare Workers AI with explicit XML delimiter tagging and strict untrusted evidence clauses.

---

## 3. Authentication & Credential Architecture

### 3.1 Password Hashing & Timing Attack Defense

- **Algorithm:** PBKDF2-SHA-256 with 600,000 iterations and a cryptographically secure 16-byte random salt (`secrets.token_hex(16)`).
- **Constant-Time Verification:** Both valid and invalid user logins execute full PBKDF2 key derivation. When an email does not exist, a dummy verification executes against a constant salt and hash (`_DUMMY_SALT`, `_DUMMY_HASH`), completely neutralizing timing-based email enumeration attacks.

### 3.2 Access Tokens

- **Format:** Signed opaque base64url token: `<b64url(payload_json)>.<hmac_hex>`
- **Signing:** HMAC-SHA-256 using `AUTH_TOKEN_SECRET`.
- **TTL:** 15 minutes (900 seconds).
- **Validation:** Constant-time HMAC comparison via `hmac.compare_digest`. Expired tokens return `401` with `SESSION_EXPIRED` to trigger automatic client rotation.

### 3.3 Refresh Tokens & Active Replay Attack Mitigation

- **Format:** 32-byte cryptographically-random hex string (`secrets.token_hex(32)`).
- **Storage:** Only the SHA-256 hash of the token is persisted in Cloudflare D1; the plaintext token exists only on the client.
- **Rotation:** Single-use rotation on each refresh. The old session is marked revoked and a fresh pair is minted.
- **Active Defense / Replay Detection:** If an incoming refresh request provides a token whose session is already marked revoked (`revoked_at IS NOT NULL`), the system identifies an active replay/theft attempt and immediately revokes all active sessions for that user (`revoke_all_user_sessions`).

---

## 4. Authorization Matrix & Scoping

| Principal         | Resource / Action                    | Enforcement Mechanism                          | Failure Status               |
| :---------------- | :----------------------------------- | :--------------------------------------------- | :--------------------------- |
| **Anonymous**     | Create Video Conversation            | Bound to `x-session-id`, `user_id = NULL`      | 429 if quota exceeded        |
| **Anonymous**     | List Conversations                   | Filtered: `user_id IS NULL AND session_id = ?` | Empty list if none           |
| **Authenticated** | Create Video Conversation            | Bound to JWT `user_id`                         | 429 if quota exceeded        |
| **Authenticated** | List Conversations                   | Filtered: `user_id = ?`                        | Scoped strictly to caller    |
| **Cross-User**    | View/Update Conversation of User B   | `_assert_ownership` check                      | `403 CONVERSATION_FORBIDDEN` |
| **Public / Any**  | Admin Maintenance (`/admin/cleanup`) | `X-Admin-Key` constant-time HMAC comparison    | `401 UNAUTHORIZED`           |

---

## 5. Abuse Prevention & Edge Hardening

### 5.1 Multi-Tier Sliding Window Rate Limiting

The API Gateway Middleware enforces sliding window rate limiting per IP and route tier:

- **Auth Mutation (`/auth/login`, `/auth/register`):** 10 requests / minute.
- **AI Inference (`/ask`):** 30 requests / minute.
- **Retrieval (`/retrieval`):** 50 requests / minute.
- **Standard Endpoints (`/health`, `/videos`):** 100 requests / minute.

### 5.2 Payload Size Protection

- Strict 1 MB (`1,048,576 bytes`) content-length ceiling on incoming request bodies.
- Oversized uploads are rejected at the ASGI middleware boundary with `413 PAYLOAD_TOO_LARGE`.

### 5.3 Security Response Headers

Every HTTP response automatically includes:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- Sensitive endpoints (`/auth`, `/conversations`, `/ask`, `/admin`) emit `Cache-Control: no-store, no-cache, must-revalidate, private` and `Pragma: no-cache`.

### 5.4 Production Environment Safeguards

- In `production` environment, `validate_production_settings()` rejects default dev secrets and wildcard `*` CORS.
- Localhost development origins (`http://localhost:*`, `http://127.0.0.1:*`) are automatically rejected in production.

---

## 6. Prompt Injection Defense & AI Safety

External video transcripts are inherently untrusted user-controlled data. The system enforces strict isolation:

1. **XML Boundary Demarcation:**
   - Transcript chunks are wrapped within `<transcript_evidence>...</transcript_evidence>`.
   - User questions are wrapped within `<user_question>...</user_question>`.
2. **Untrusted Evidence Clause:**
   - System prompts instruct the LLM that text inside `<transcript_evidence>` is passive data and must never be treated as system commands, role shifts, or instructions.
3. **Strict Citation Grounding:**
   - The LLM is prohibited from answering questions without citing specific `[E#]` evidence markers from the provided chunks.
   - If insufficient evidence is found in the video transcript, the system outputs a fixed string: `"I cannot answer this question based on the video transcript as no relevant evidence was found."`

---

## 7. Incident Response & Vulnerability Disclosure

- **Reporting:** Security disclosures should be sent to `security@youtube-ai-assistant.local` (or repository security tab).
- **Triage SLA:** Critical vulnerabilities triaged within 24 hours.
- **Remediation:** Cloudflare Worker edge deployment enables instant global rollout of hotfixes without requiring client extension updates.
