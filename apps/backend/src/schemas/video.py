"""Video request and response schemas."""

import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from src.schemas.base import CamelModel
from src.schemas.retrieval import RetrievalStatus
from src.schemas.transcript import TranscriptSummary

VideoProcessingStatus = Literal["accepted", "processing", "ready", "unavailable", "error"]

YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def is_valid_youtube_video_id(video_id: str | None) -> bool:
    """Validates that a string is a valid 11-character YouTube video ID."""
    if not video_id or not isinstance(video_id, str):
        return False
    return bool(YOUTUBE_VIDEO_ID_REGEX.match(video_id.strip()))


class VideoAnalyzeRequest(CamelModel):
    video_id: str


class VideoRecordSummary(CamelModel):
    video_id: str
    status: VideoProcessingStatus
    transcript_status: str | None = None
    retrieval_status: RetrievalStatus | None = None
    updated_at: str | None = None


class VideoRecord(CamelModel):
    video_id: str
    status: VideoProcessingStatus
    transcript_status: str = "not_ready"
    retrieval_status: RetrievalStatus = "not_ready"
    language_code: str | None = None
    language: str | None = None
    transcript_provider: str | None = None
    transcript_hash: str | None = None
    transcript_version: str = "v1"
    normalization_version: str = "v1"
    chunker_version: str = "v1"
    embedding_model: str = "deterministic-384"
    embedding_version: str = "v1"
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class VideoAnalyzeResponse(CamelModel):
    success: bool = True
    video: VideoRecordSummary
    transcript: TranscriptSummary | None = None
    retrieval_status: RetrievalStatus | None = None
    request_id: str | None = None


class VideoStatusResponse(CamelModel):
    success: bool = True
    video: VideoRecordSummary
    transcript: TranscriptSummary | None = None
    retrieval_status: RetrievalStatus | None = None
    request_id: str | None = None
