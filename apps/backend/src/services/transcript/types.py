"""Internal types for transcript acquisition and processing."""

from dataclasses import dataclass
from typing import Literal, Protocol

from src.schemas.transcript import Transcript, TranscriptSegment, TranscriptSummary

VideoProcessingStatus = Literal["accepted", "processing", "ready", "unavailable", "error"]


@dataclass
class RawCaptionTrack:
    base_url: str
    name: str
    vss_id: str
    language_code: str
    is_auto_generated: bool
    kind: str | None = None


@dataclass
class RawCaptionEvent:
    t_start_ms: int
    d_duration_ms: int
    text: str


@dataclass
class TranscriptOptions:
    preferred_languages: list[str] | None = None


@dataclass
class TranscriptSource:
    provider: str
    language_code: str
    is_auto_generated: bool


CaptionTrackSource = TranscriptSource


@dataclass
class TranscriptResult:
    video_id: str
    language: str
    language_code: str
    is_auto_generated: bool
    segments: list[TranscriptSegment]
    total_duration: float
    source: TranscriptSource


class TranscriptProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult: ...


@dataclass
class VideoProcessingRecord:
    video_id: str
    status: VideoProcessingStatus
    transcript: Transcript | None = None
    summary: TranscriptSummary | None = None
    error: str | None = None
    updated_at: float = 0.0
