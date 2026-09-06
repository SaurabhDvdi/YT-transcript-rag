"""Job coordination service with deduplication, single-flight control, and stale recovery."""

import logging
from datetime import UTC, datetime
from typing import Any

from src.repositories.job import D1JobRepository, InMemoryJobRepository, JobRepository
from src.schemas.job import JobType, ProcessingJob

logger = logging.getLogger("api")


class JobService:
    """Central processing job service orchestrating durable job lifecycle."""

    _instance: "JobService | None" = None

    def __init__(self, job_repo: JobRepository | None = None) -> None:
        self.repo = job_repo or InMemoryJobRepository()

    @classmethod
    def get_instance(cls, db: Any = None) -> "JobService":
        if db is not None:
            return cls(D1JobRepository(db))
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "JobService | None") -> None:
        cls._instance = instance

    async def get_or_create_job(
        self, video_id: str, job_type: JobType, max_attempts: int = 3
    ) -> tuple[ProcessingJob, bool]:
        """Atomically returns existing active job or creates a new queued job."""
        existing = await self.repo.get_active_job(video_id, job_type)
        if existing:
            return existing, False

        job = await self.repo.create_job(video_id, job_type, max_attempts=max_attempts)
        return job, True

    async def mark_started(self, job_id: str) -> None:
        job = await self.repo.get_by_id(job_id)
        if not job:
            return
        now_iso = datetime.now(UTC).isoformat()
        job.status = "processing"
        job.attempts += 1
        job.started_at = now_iso
        job.updated_at = now_iso
        await self.repo.update_job(job)

    async def mark_completed(self, job_id: str) -> None:
        job = await self.repo.get_by_id(job_id)
        if not job:
            return
        now_iso = datetime.now(UTC).isoformat()
        job.status = "completed"
        job.completed_at = now_iso
        job.updated_at = now_iso
        await self.repo.update_job(job)

    async def mark_failed(self, job_id: str, error_code: str, error_message: str) -> None:
        job = await self.repo.get_by_id(job_id)
        if not job:
            return
        now_iso = datetime.now(UTC).isoformat()
        job.error_code = error_code
        job.error_message = error_message
        job.updated_at = now_iso

        if job.attempts < job.max_attempts:
            job.status = "queued"
        else:
            job.status = "failed"
            job.completed_at = now_iso

        await self.repo.update_job(job)

    async def recover_stale_jobs(self, threshold_seconds: float = 120.0) -> list[ProcessingJob]:
        stale_jobs = await self.repo.find_stale_jobs(threshold_seconds)
        recovered: list[ProcessingJob] = []
        for job in stale_jobs:
            if job.attempts >= job.max_attempts:
                logger.warning(
                    "Job %s exceeded max attempts (%d); marking failed",
                    job.id,
                    job.max_attempts,
                )
                await self.mark_failed(
                    job.id, "MAX_ATTEMPTS_EXCEEDED", "Job timed out and exceeded retry limit."
                )
            else:
                logger.info("Recovering stale job %s (attempt %d)", job.id, job.attempts)
                job.status = "queued"
                job.updated_at = datetime.now(UTC).isoformat()
                await self.repo.update_job(job)
                recovered.append(job)
        return recovered
