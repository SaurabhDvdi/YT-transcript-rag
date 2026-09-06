"""Processing job repository protocol and implementations (InMemory and D1)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from src.schemas.job import JobType, ProcessingJob


class JobRepository(Protocol):
    """Protocol for durable processing job state management."""

    async def get_active_job(self, video_id: str, job_type: JobType) -> ProcessingJob | None: ...

    async def get_by_id(self, job_id: str) -> ProcessingJob | None: ...

    async def create_job(
        self, video_id: str, job_type: JobType, max_attempts: int = 3
    ) -> ProcessingJob: ...

    async def update_job(self, job: ProcessingJob) -> None: ...

    async def find_stale_jobs(self, threshold_seconds: float) -> list[ProcessingJob]: ...

    async def purge_old_jobs(self, retention_days: int) -> int: ...


class InMemoryJobRepository:
    """In-memory job repository for testing and local development."""

    def __init__(self) -> None:
        self._store: dict[str, ProcessingJob] = {}

    async def get_active_job(self, video_id: str, job_type: JobType) -> ProcessingJob | None:
        for job in self._store.values():
            if (
                job.video_id == video_id
                and job.job_type == job_type
                and job.status in ("queued", "processing")
            ):
                return job
        return None

    async def get_by_id(self, job_id: str) -> ProcessingJob | None:
        return self._store.get(job_id)

    async def create_job(
        self, video_id: str, job_type: JobType, max_attempts: int = 3
    ) -> ProcessingJob:
        existing = await self.get_active_job(video_id, job_type)
        if existing:
            return existing

        now_iso = datetime.now(UTC).isoformat()
        job_id = f"job-{video_id}-{job_type.lower()}-{uuid.uuid4().hex[:8]}"
        job = ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type=job_type,
            status="queued",
            attempts=0,
            max_attempts=max_attempts,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._store[job_id] = job
        return job

    async def update_job(self, job: ProcessingJob) -> None:
        self._store[job.id] = job

    async def find_stale_jobs(self, threshold_seconds: float) -> list[ProcessingJob]:
        now = datetime.now(UTC)
        stale: list[ProcessingJob] = []
        for job in self._store.values():
            if job.status == "processing":
                try:
                    updated_dt = datetime.fromisoformat(job.updated_at)
                    if (now - updated_dt).total_seconds() > threshold_seconds:
                        stale.append(job)
                except Exception:
                    stale.append(job)
        return stale

    async def purge_old_jobs(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        to_delete: list[str] = []
        for j_id, job in self._store.items():
            if job.status in ("completed", "failed", "cancelled"):
                try:
                    updated_dt = datetime.fromisoformat(job.updated_at)
                    if updated_dt < cutoff:
                        to_delete.append(j_id)
                except Exception:
                    pass
        for j_id in to_delete:
            del self._store[j_id]
        return len(to_delete)


class D1JobRepository:
    """D1-backed processing job repository for Cloudflare Workers."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def get_active_job(self, video_id: str, job_type: JobType) -> ProcessingJob | None:
        stmt = self.db.prepare(
            """
            SELECT * FROM processing_jobs
            WHERE video_id = ? AND job_type = ? AND status IN ('queued', 'processing')
            ORDER BY updated_at DESC LIMIT 1
            """
        ).bind(video_id, job_type)
        row = await stmt.first()
        if not row:
            return None
        return self._row_to_job(row)

    async def get_by_id(self, job_id: str) -> ProcessingJob | None:
        stmt = self.db.prepare("SELECT * FROM processing_jobs WHERE id = ? LIMIT 1").bind(job_id)
        row = await stmt.first()
        if not row:
            return None
        return self._row_to_job(row)

    async def create_job(
        self, video_id: str, job_type: JobType, max_attempts: int = 3
    ) -> ProcessingJob:
        existing = await self.get_active_job(video_id, job_type)
        if existing:
            return existing

        now_iso = datetime.now(UTC).isoformat()
        job_id = f"job-{video_id}-{job_type.lower()}-{uuid.uuid4().hex[:8]}"

        stmt = self.db.prepare(
            """
            INSERT INTO processing_jobs (
                id, video_id, job_type, status, attempts, max_attempts,
                created_at, updated_at
            ) VALUES (?, ?, ?, 'queued', 0, ?, ?, ?)
            """
        ).bind(job_id, video_id, job_type, max_attempts, now_iso, now_iso)
        await stmt.run()

        return ProcessingJob(
            id=job_id,
            video_id=video_id,
            job_type=job_type,
            status="queued",
            attempts=0,
            max_attempts=max_attempts,
            created_at=now_iso,
            updated_at=now_iso,
        )

    async def update_job(self, job: ProcessingJob) -> None:
        updated_at = job.updated_at or datetime.now(UTC).isoformat()
        stmt = self.db.prepare(
            """
            UPDATE processing_jobs
            SET status = ?, attempts = ?, error_code = ?, error_message = ?,
                started_at = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
            """
        ).bind(
            job.status,
            job.attempts,
            job.error_code,
            job.error_message,
            job.started_at,
            job.completed_at,
            updated_at,
            job.id,
        )
        await stmt.run()

    async def find_stale_jobs(self, threshold_seconds: float) -> list[ProcessingJob]:
        cutoff = (datetime.now(UTC) - timedelta(seconds=threshold_seconds)).isoformat()
        stmt = self.db.prepare(
            """
            SELECT * FROM processing_jobs
            WHERE status = 'processing' AND updated_at < ?
            ORDER BY updated_at ASC
            """
        ).bind(cutoff)
        res = await stmt.all()
        if isinstance(res, dict) and "results" in res:
            results = res["results"]
        elif hasattr(res, "results"):
            results = res.results
        else:
            results = res or []
        return [self._row_to_job(r) for r in (results or [])]

    async def purge_old_jobs(self, retention_days: int) -> int:
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        stmt = self.db.prepare(
            """
            DELETE FROM processing_jobs
            WHERE status IN ('completed', 'failed', 'cancelled') AND updated_at < ?
            """
        ).bind(cutoff)
        res = await stmt.run()
        meta = res.get("meta", {}) if isinstance(res, dict) else (getattr(res, "meta", {}) or {})
        return meta.get("changes", 0) if isinstance(meta, dict) else 0

    def _row_to_job(self, row: Any) -> ProcessingJob:
        d = (
            row
            if isinstance(row, dict)
            else (row.__dict__ if hasattr(row, "__dict__") else dict(row))
        )
        return ProcessingJob(
            id=d["id"],
            video_id=d["video_id"],
            job_type=d["job_type"],
            status=d["status"],
            attempts=d.get("attempts", 0),
            max_attempts=d.get("max_attempts", 3),
            error_code=d.get("error_code"),
            error_message=d.get("error_message"),
            created_at=d["created_at"],
            started_at=d.get("started_at"),
            updated_at=d["updated_at"],
            completed_at=d.get("completed_at"),
        )
