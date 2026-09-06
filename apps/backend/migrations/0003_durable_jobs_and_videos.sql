-- Phase 8: Durable Videos, Processing Jobs, Transcripts, and Vector Chunks

-- 1. Persistent Video Registry
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'processing', 'ready', 'error')),
    transcript_status TEXT NOT NULL DEFAULT 'not_ready' CHECK (transcript_status IN ('not_ready', 'processing', 'ready', 'error')),
    retrieval_status TEXT NOT NULL DEFAULT 'not_ready' CHECK (retrieval_status IN ('not_ready', 'indexing', 'ready', 'error')),
    language_code TEXT,
    language TEXT,
    transcript_provider TEXT,
    transcript_hash TEXT,
    transcript_version TEXT DEFAULT 'v1',
    normalization_version TEXT DEFAULT 'v1',
    chunker_version TEXT DEFAULT 'v1',
    embedding_model TEXT DEFAULT 'deterministic-384',
    embedding_version TEXT DEFAULT 'v1',
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (status);

-- 2. Durable Processing Jobs
CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    job_type TEXT NOT NULL CHECK (job_type IN ('TRANSCRIPT', 'INDEX')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_video_type ON processing_jobs (video_id, job_type, status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status_updated ON processing_jobs (status, updated_at);

-- 3. Durable Transcripts Table
CREATE TABLE IF NOT EXISTS transcripts (
    video_id TEXT NOT NULL,
    language_code TEXT NOT NULL,
    language TEXT NOT NULL,
    is_auto_generated INTEGER NOT NULL DEFAULT 0,
    segments TEXT NOT NULL,
    total_duration REAL NOT NULL,
    transcript_hash TEXT NOT NULL,
    normalization_version TEXT NOT NULL DEFAULT 'v1',
    provider_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, language_code),
    FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

-- 4. Durable Vector Chunks Store (video-isolated persistent vector index)
CREATE TABLE IF NOT EXISTS vector_chunks (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    embedding_version TEXT NOT NULL DEFAULT 'v1',
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    segment_start_index INTEGER NOT NULL,
    segment_end_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_blob TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vector_chunks_video_version ON vector_chunks (video_id, embedding_version);
