# API Reference Specification

## 1. Global Conventions

### 1.1 Base URL & Versioning

All endpoints are prefixed with `/api/v1/`.

### 1.2 Headers

- `Authorization: Bearer <accessToken>`: Required for authenticated user endpoints; optional for public endpoints.
- `X-Session-ID`: Client session UUID.
- `X-Request-ID`: Client trace UUID. Automatically echoed in response headers.
- `X-Admin-Key`: Required for admin operations (`/api/v1/admin/*`).

### 1.3 Standard Response Formats

- **Success:**
  ```json
  {
    "success": true,
    "data": { ... },
    "requestId": "req-123456"
  }
  ```
- **Error:**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Invalid email or password."
    },
    "requestId": "req-123456"
  }
  ```

---

## 2. Authentication Endpoints

### `POST /api/v1/auth/register`

Create a new user account.

- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "success": true,
    "user": {
      "id": "usr-uuid",
      "email": "user@example.com",
      "createdAt": "2026-09-06T..."
    },
    "tokens": { "accessToken": "...", "refreshToken": "...", "expiresIn": 900 }
  }
  ```

### `POST /api/v1/auth/login`

Authenticate with email and password. Constant-time response against timing attacks.

- **Rate Limit:** 10 requests / minute per IP.

### `POST /api/v1/auth/refresh`

Rotate refresh token and obtain new access + refresh token pair. Replaying revoked tokens triggers user-wide session invalidation.

- **Request Body:**
  ```json
  {
    "refreshToken": "raw-hex-token"
  }
  ```

### `GET /api/v1/auth/me`

Retrieve authenticated user profile. Requires valid Bearer access token.

### `DELETE /api/v1/auth/me`

Soft delete account and revoke all sessions immediately.

---

## 3. Video Processing & Retrieval Endpoints

### `POST /api/v1/videos`

Register a YouTube video for transcript ingestion and indexing.

- **Request Body:**
  ```json
  {
    "videoId": "dQw4w9WgXcQ"
  }
  ```
- **Response `202 Accepted`:**
  ```json
  {
    "success": true,
    "video": { "videoId": "dQw4w9WgXcQ", "status": "ready" },
    "transcript": { "language": "en", "segmentCount": 120 },
    "retrievalStatus": "indexed"
  }
  ```

### `GET /api/v1/videos/{video_id}`

Check ingestion and indexing status.

### `GET /api/v1/videos/{video_id}/transcript`

Retrieve full normalized transcript segments.

### `POST /api/v1/videos/{video_id}/retrieval`

Perform semantic vector search over transcript chunks.

---

## 4. Conversation & Q&A Endpoints

### `POST /api/v1/videos/{video_id}/conversations`

Create a new conversation scoped to the video and caller.

### `GET /api/v1/videos/{video_id}/conversations`

List conversations for the video (scoped to caller).

### `POST /api/v1/conversations/{conversation_id}/messages`

Send question and generate grounded response. Supports both synchronous JSON (`stream: false`) and Server-Sent Events (`stream: true`).

- **Response Event Stream (`text/event-stream`):**
  ```text
  event: metadata
  data: {"evidence":[{"id":"chunk_001","timestamp_start":12.5,"timestamp_end":45.0,"text":"..."}]}

  event: chunk
  data: {"content":"Based on "}

  event: done
  data: {"content":"..."}
  ```

---

## 5. Health & Admin Endpoints

### `GET /api/v1/health`

Liveness check returning service name, status `ok`, and version.

### `GET /api/v1/ready`

Readiness check verifying database and storage connectivity.

### `POST /api/v1/admin/cleanup`

Trigger retention cleanup and stale job recovery. Protected by constant-time `X-Admin-Key`.
