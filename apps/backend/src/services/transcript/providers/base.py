"""Base TranscriptProvider protocol definition."""

from typing import Protocol

from src.services.transcript.types import TranscriptOptions, TranscriptResult


class TranscriptProvider(Protocol):
    """Abstract provider for acquiring YouTube transcripts."""

    @property
    def name(self) -> str: ...

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult: ...
