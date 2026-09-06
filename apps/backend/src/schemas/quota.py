"""Quota and usage tracking schemas."""

from typing import Literal

from src.schemas.base import CamelModel

UsageEventType = Literal[
    "video_registered",
    "transcript_processed",
    "retrieval_requested",
    "generation_requested",
    "generation_succeeded",
    "generation_failed",
    "stream_cancelled",
]


class QuotaDecision(CamelModel):
    allowed: bool
    remaining: int | None = None
    reset_at: str | None = None
    reason: str | None = None


class UsageEvent(CamelModel):
    id: str
    session_id: str
    user_id: str | None = None
    video_id: str | None = None
    event_type: UsageEventType
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    created_at: str
