-- Phase 9: User Authentication – Users, Auth Sessions, Ownership Columns

-- 1. Registered user accounts
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT            -- soft-delete; NULL = active
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- 2. Refresh token sessions (server-side revocation)
CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,   -- SHA-256(refresh_token_hex)
    expires_at TEXT NOT NULL,
    revoked_at TEXT,                   -- NULL = active
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions (user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_token ON auth_sessions (token_hash);

-- 3. Attach optional user ownership to conversations
--    NULL = anonymous (existing rows are unaffected and remain accessible via X-Session-ID)
ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations (user_id, updated_at DESC);

-- 4. Track authenticated quota separately in usage_events
--    NULL = anonymous session (existing rows unaffected)
ALTER TABLE usage_events ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_usage_events_user_time ON usage_events (user_id, created_at DESC);
