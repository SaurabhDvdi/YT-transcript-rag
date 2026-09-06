-- Phase 10: Associate conversations with anonymous session IDs for secure session migration

ALTER TABLE conversations ADD COLUMN session_id TEXT;

CREATE INDEX IF NOT EXISTS idx_conversations_session 
ON conversations (session_id, updated_at DESC);
