-- Phase 6: Multi-Turn Conversational Storage Schema (Cloudflare D1)

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  video_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_video_updated 
ON conversations (video_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  citations TEXT,
  grounded INTEGER,
  client_request_id TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created 
ON messages (conversation_id, created_at ASC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_client_request 
ON messages (client_request_id) 
WHERE client_request_id IS NOT NULL;
