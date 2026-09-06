"""Processing job data models and schemas."""

from typing import Literal

from src.schemas.base import CamelModel

JobType = Literal["TRANSCRIPT", "INDEX"]
JobStatus = Literal["queued", "processing", "completed", "failed", "cancelled"]


class ProcessingJob(CamelModel):
    id: str
    video_id: str
    job_type: JobType
    status: JobStatus
    attempts: int = 0
    max_attempts: int = 3
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    updated_at: str
    completed_at: str | None = None


class JobStatusResponse(CamelModel):
    success: bool = True
    job: ProcessingJob
    request_id: str | None = None
