"""Tests for durable job lifecycle, single-flight deduplication, and stale recovery."""

from datetime import UTC, datetime, timedelta

import pytest

from src.repositories.job import D1JobRepository, InMemoryJobRepository
from src.repositories.video import D1VideoRepository
from src.schemas.video import VideoRecord
from src.services.job.service import JobService
from tests.conftest import MockD1Database


@pytest.mark.asyncio
async def test_job_service_deduplication():
    job_service = JobService(InMemoryJobRepository())
    video_id = "test_vid_job_1"

    # 1. First call creates the job
    job1, created1 = await job_service.get_or_create_job(video_id, "TRANSCRIPT")
    assert created1 is True
    assert job1.video_id == video_id
    assert job1.job_type == "TRANSCRIPT"
    assert job1.status == "queued"

    # 2. Second concurrent call returns the same active job
    job2, created2 = await job_service.get_or_create_job(video_id, "TRANSCRIPT")
    assert created2 is False
    assert job2.id == job1.id
    assert job2.status == "queued"


@pytest.mark.asyncio
async def test_job_service_lifecycle():
    job_service = JobService(InMemoryJobRepository())
    video_id = "test_vid_job_2"

    job, _ = await job_service.get_or_create_job(video_id, "TRANSCRIPT")

    # Mark started
    await job_service.mark_started(job.id)
    running_job = await job_service.repo.get_by_id(job.id)
    assert running_job is not None
    assert running_job.status == "processing"
    assert running_job.attempts == 1
    assert running_job.started_at is not None

    # Mark completed
    await job_service.mark_completed(job.id)
    done_job = await job_service.repo.get_by_id(job.id)
    assert done_job is not None
    assert done_job.status == "completed"
    assert done_job.completed_at is not None

    # New job request after completion creates a fresh job
    job3, created3 = await job_service.get_or_create_job(video_id, "TRANSCRIPT")
    assert created3 is True
    assert job3.id != job.id


@pytest.mark.asyncio
async def test_job_service_failure_and_retry():
    job_service = JobService(InMemoryJobRepository())
    video_id = "test_vid_job_3"

    job, _ = await job_service.get_or_create_job(video_id, "INDEX", max_attempts=2)
    await job_service.mark_started(job.id)

    # First failure -> retry queued
    await job_service.mark_failed(job.id, "INDEX_ERROR", "Temporary network failure")
    retried_job = await job_service.repo.get_by_id(job.id)
    assert retried_job is not None
    assert retried_job.status == "queued"  # attempts=1 < max_attempts=2

    # Second failure -> final failure
    await job_service.mark_started(job.id)  # attempts becomes 2
    await job_service.mark_failed(job.id, "INDEX_ERROR", "Permanent failure")
    final_job = await job_service.repo.get_by_id(job.id)
    assert final_job is not None
    assert final_job.status == "failed"


@pytest.mark.asyncio
async def test_d1_job_repository(d1_db: MockD1Database):
    # Ensure foreign key parent video exists
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="d1_job_vid", status="processing"))

    job_repo = D1JobRepository(d1_db)
    job = await job_repo.create_job("d1_job_vid", "TRANSCRIPT")
    assert job.status == "queued"

    fetched = await job_repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.video_id == "d1_job_vid"

    active = await job_repo.get_active_job("d1_job_vid", "TRANSCRIPT")
    assert active is not None
    assert active.id == job.id


@pytest.mark.asyncio
async def test_stale_job_recovery(d1_db: MockD1Database):
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="stale_vid", status="processing"))

    job_repo = D1JobRepository(d1_db)
    job = await job_repo.create_job("stale_vid", "TRANSCRIPT")

    # Force job into processing state with an old timestamp
    old_time = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
    job.status = "processing"
    job.updated_at = old_time
    job.attempts = 1
    await job_repo.update_job(job)

    # Recover stale jobs older than 10 minutes
    stale_jobs = await job_repo.find_stale_jobs(threshold_seconds=600)
    assert len(stale_jobs) == 1
    assert stale_jobs[0].id == job.id

    # Reset it to queued for retry
    stale = stale_jobs[0]
    stale.status = "queued"
    await job_repo.update_job(stale)

    recovered = await job_repo.get_by_id(job.id)
    assert recovered is not None
    assert recovered.status == "queued"
