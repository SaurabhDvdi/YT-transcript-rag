# Privacy Policy & Data Management Specification

## 1. Overview & Principles

The YouTube AI Assistant is built with privacy-by-design principles:

- **Data Minimization:** We collect only the data necessary to provide grounded conversational answers for YouTube videos.
- **Client-Side Control:** Users can operate entirely anonymously without creating an account or providing an email address.
- **Zero AI Training on User Data:** User queries and video transcripts processed by AI providers are used solely for real-time inference and are not retained for model training.

---

## 2. Information We Collect & Store

### 2.1 Anonymous Users

- **Session Identifier (`x-session-id`):** A randomly generated client-side UUID stored in browser extension storage. Used solely for rate limiting, quota tracking, and conversation grouping.
- **Video ID & Transcript Cache:** Public YouTube video IDs and extracted transcript text chunks stored in Cloudflare D1/KV to prevent redundant processing.
- **Conversations & Messages:** Prompts and generated responses associated with the anonymous session.

### 2.2 Authenticated Users

- **Account Credentials:** Email address, PBKDF2-SHA-256 hashed password, and salt. Plaintext passwords are never logged or stored.
- **Authentication Sessions:** Session tokens and rotated refresh token hashes stored in D1.
- **User Conversations:** Conversations and chat history linked to `user_id`.

---

## 3. Data Retention & Lifecycle Policies

| Data Category                | Purpose                      | Retention Period             | Automatic Cleanup                  |
| :--------------------------- | :--------------------------- | :--------------------------- | :--------------------------------- |
| **Operational Usage Events** | Quota tracking & telemetry   | 30 days                      | Cleaned by `/api/v1/admin/cleanup` |
| **Background Jobs**          | Ingestion status & retries   | 7 days                       | Cleaned by `/api/v1/admin/cleanup` |
| **Transcript & Index Cache** | Accelerated RAG response     | 1–30 days (LRU / TTL)        | Cleared on cache eviction          |
| **User Account & History**   | Persistent multi-device chat | Retained until user deletion | Upon user account deletion         |

---

## 4. User Rights: Account Deletion & Data Erasure (GDPR / CCPA)

Users have the absolute right to delete their account and associated data:

- **Endpoint:** `DELETE /api/v1/auth/me`
- **Immediate Effect:**
  1. All active and historical refresh sessions for the user are immediately revoked (`revoke_all_user_sessions`).
  2. The user account is soft-deleted with an immutable `deleted_at` timestamp.
  3. Subsequent login attempts with those credentials are permanently blocked with `401 ACCOUNT_DELETED`.
  4. User conversations and messages are orphaned from active retrieval.
- **Anonymous Session Purge:** Anonymous users can clear their local session, chat history, and tokens at any time via the extension's **Clear Conversation** button or browser extension data wipe.

---

## 5. Third-Party Disclosures & Processing

- **Google YouTube:** Transcripts are acquired via public YouTube caption tracks or client-side DOM caption extraction. No personal user credentials or private video contents are accessed.
- **LLM Providers (Google Gemini & Cloudflare Workers AI):** Text context and user questions are transmitted encrypted over HTTPS for inference. No customer conversations are licensed or sold to third parties.
