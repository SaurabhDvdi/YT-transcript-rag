"""Scheduled maintenance and data retention cleanup service."""

import logging
from typing import Any

from src.core.config import get_settings
from src.repositories.job import D1JobRepository, InMemoryJobRepository, JobRepository
from src.repositories.usage import D1UsageRepository, InMemoryUsageRepository, UsageRepository
from src.services.job.service import JobService

logger = logging.getLogger("api")


class CleanupService:
    """Service executing data retention rules, stale job recovery, and orphan detection."""

    _instance: "CleanupService | None" = None

    def __init__(
        self,
        job_repo: JobRepository | None = None,
        usage_repo: UsageRepository | None = None,
        db: Any = None,
    ) -> None:
        if db is not None:
            self.job_repo = job_repo or D1JobRepository(db)
            self.usage_repo = usage_repo or D1UsageRepository(db)
            self._db = db
        else:
            self.job_repo = job_repo or InMemoryJobRepository()
            self.usage_repo = usage_repo or InMemoryUsageRepository()
            self._db = None

    @classmethod
    def get_instance(cls, db: Any = None) -> "CleanupService":
        if db is not None:
            return cls(D1JobRepository(db), D1UsageRepository(db), db=db)
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_cleanup(
        self,
        db: Any = None,
        usage_retention_days: int | None = None,
        job_retention_days: int | None = None,
    ) -> dict[str, Any]:
        """Executes all maintenance routines and returns summary metrics."""
        settings = get_settings()
        target_db = db or self._db
        u_days = (
            usage_retention_days
            if usage_retention_days is not None
            else settings.retention_usage_events_days
        )
        j_days = (
            job_retention_days if job_retention_days is not None else settings.retention_jobs_days
        )

        # 1. Purge old usage events
        events_purged = await self.usage_repo.purge_old_events(u_days)

        # 2. Purge old completed/failed jobs
        jobs_purged = await self.job_repo.purge_old_jobs(j_days)

        # 3. Recover stale processing jobs
        job_service = JobService.get_instance(target_db)
        recovered_jobs = await job_service.recover_stale_jobs(settings.stale_job_timeout_seconds)

        # 4. Check for orphaned vectors or transcripts
        orphaned_vectors_cleaned = 0
        orphaned_transcripts_cleaned = 0
        if db is not None:
            try:
                # Clean vectors where video was deleted
                del_vec_stmt = db.prepare(
                    """
                    DELETE FROM vector_chunks
                    WHERE video_id NOT IN (SELECT video_id FROM videos)
                    """
                )
                vec_res = await del_vec_stmt.run()
                v_meta = getattr(vec_res, "meta", {}) or {}
                orphaned_vectors_cleaned = (
                    v_meta.get("changes", 0) if isinstance(v_meta, dict) else 0
                )

                # Clean transcripts where video was deleted
                del_ts_stmt = db.prepare(
                    """
                    DELETE FROM transcripts
                    WHERE video_id NOT IN (SELECT video_id FROM videos)
                    """
                )
                ts_res = await del_ts_stmt.run()
                t_meta = getattr(ts_res, "meta", {}) or {}
                orphaned_transcripts_cleaned = (
                    t_meta.get("changes", 0) if isinstance(t_meta, dict) else 0
                )
            except Exception as e:
                logger.warning("Orphan cleanup warning: %s", e)

        return {
            "events_purged": events_purged,
            "jobs_purged": jobs_purged,
            "jobs_recovered": len(recovered_jobs),
            "orphaned_vectors_cleaned": orphaned_vectors_cleaned,
            "orphaned_transcripts_cleaned": orphaned_transcripts_cleaned,
            "deleted_usage_events": events_purged,
            "deleted_jobs": jobs_purged,
        }

    run_all = run_cleanup
