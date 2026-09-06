-- Phase 8: Operational Usage Events for Quota Accounting and Retention

CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    video_id TEXT,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'video_registered',
        'transcript_processed',
        'retrieval_requested',
        'generation_requested',
        'generation_succeeded',
        'generation_failed',
        'stream_cancelled'
    )),
    provider TEXT,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    latency_ms REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_events_session_time ON usage_events (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_video_time ON usage_events (video_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events (created_at);
