"""Transcript data models and schemas."""

from src.schemas.base import CamelModel


class TranscriptSegment(CamelModel):
    index: int
    start: float
    duration: float
    end: float
    text: str


class TranscriptSummary(CamelModel):
    language: str
    language_code: str
    is_auto_generated: bool
    segment_count: int
    duration: float


class Transcript(CamelModel):
    video_id: str
    language: str
    language_code: str
    is_auto_generated: bool
    segments: list[TranscriptSegment]
    total_duration: float


class TranscriptResponse(CamelModel):
    success: bool = True
    video_id: str
    transcript: Transcript | None = None
    request_id: str | None = None
