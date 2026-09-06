"""Tests for persistent video registry (in-memory and D1 implementations)."""

import pytest

from src.repositories.video import D1VideoRepository, InMemoryVideoRepository
from src.schemas.video import VideoRecord
from tests.conftest import MockD1Database


@pytest.mark.asyncio
async def test_in_memory_video_repository():
    repo = InMemoryVideoRepository()

    # 1. Non-existent returns None
    assert await repo.get("nonexistent") is None

    # 2. Save record
    rec = VideoRecord(
        video_id="vid_mem_1",
        status="processing",
        transcript_status="processing",
        retrieval_status="not_ready",
        language_code="en",
        language="English",
    )
    await repo.save(rec)

    fetched = await repo.get("vid_mem_1")
    assert fetched is not None
    assert fetched.video_id == "vid_mem_1"
    assert fetched.status == "processing"

    # 3. Update status
    updated = await repo.update_status(
        "vid_mem_1",
        status="ready",
        transcript_status="ready",
        retrieval_status="ready",
    )
    assert updated is not None
    assert updated.status == "ready"
    assert updated.transcript_status == "ready"
    assert updated.retrieval_status == "ready"


@pytest.mark.asyncio
async def test_d1_video_repository_crud(d1_db: MockD1Database):
    repo = D1VideoRepository(d1_db)

    # 1. Non-existent
    assert await repo.get("vid_d1_missing") is None

    # 2. Save new video record
    rec = VideoRecord(
        video_id="vid_d1_1",
        status="processing",
        transcript_status="processing",
        retrieval_status="not_ready",
        language_code="en",
        language="English",
        transcript_provider="innertube",
        transcript_hash="hash_12345",
        transcript_version="v1",
        normalization_version="v1",
        chunker_version="v1",
        embedding_model="deterministic-384",
        embedding_version="v1",
    )
    await repo.save(rec)

    # 3. Retrieve
    saved = await repo.get("vid_d1_1")
    assert saved is not None
    assert saved.video_id == "vid_d1_1"
    assert saved.status == "processing"
    assert saved.language == "English"
    assert saved.transcript_hash == "hash_12345"
    assert saved.embedding_version == "v1"

    # 4. Update status to ready
    updated = await repo.update_status(
        "vid_d1_1",
        status="ready",
        transcript_status="ready",
        retrieval_status="ready",
    )
    assert updated is not None
    assert updated.status == "ready"
    assert updated.retrieval_status == "ready"

    # 5. Verify update was persisted to D1
    refetched = await repo.get("vid_d1_1")
    assert refetched is not None
    assert refetched.status == "ready"
    assert refetched.transcript_status == "ready"
    assert refetched.retrieval_status == "ready"


@pytest.mark.asyncio
async def test_d1_video_repository_error_state(d1_db: MockD1Database):
    repo = D1VideoRepository(d1_db)

    rec = VideoRecord(
        video_id="vid_d1_error",
        status="processing",
    )
    await repo.save(rec)

    updated = await repo.update_status(
        "vid_d1_error",
        status="error",
        transcript_status="error",
        error_message="Transcript disabled on video",
    )
    assert updated is not None
    assert updated.status == "error"
    assert updated.error_message == "Transcript disabled on video"


@pytest.mark.asyncio
async def test_d1_video_repository_isolation(d1_db: MockD1Database):
    repo = D1VideoRepository(d1_db)

    await repo.save(VideoRecord(video_id="video_A", status="ready"))
    await repo.save(VideoRecord(video_id="video_B", status="error", error_message="Failed"))

    rec_a = await repo.get("video_A")
    rec_b = await repo.get("video_B")

    assert rec_a is not None and rec_a.status == "ready"
    assert rec_b is not None and rec_b.status == "error"
