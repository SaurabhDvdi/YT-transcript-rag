"""Retrieval data models and schemas."""

from typing import Literal

from src.schemas.base import CamelModel

RetrievalStatus = Literal["not_ready", "indexing", "ready", "error"]


class RetrievalChunk(CamelModel):
    id: str
    video_id: str = ""
    chunk_index: int = 0
    text: str
    start: float
    end: float
    segment_start_index: int = 0
    segment_end_index: int = 0
    token_count: int = 0


class RetrievalResult(CamelModel):
    chunk: RetrievalChunk
    score: float


class RetrievalRequest(CamelModel):
    query: str
    top_k: int = 5


class RetrievalResponse(CamelModel):
    success: bool = True
    video_id: str
    results: list[RetrievalResult]
    request_id: str | None = None
