"""Base protocol and models for vector stores."""

from typing import Protocol

from src.schemas.retrieval import RetrievalChunk, RetrievalResult


class VectorStore(Protocol):
    """Protocol for partitioned vector storage and semantic search."""

    async def add_chunks(
        self,
        video_id: str,
        items: list[tuple[RetrievalChunk, list[float]]],
        embedding_version: str = "v1",
    ) -> None: ...

    async def search(
        self,
        video_id: str,
        query_vector: list[float],
        top_k: int = 5,
        min_score: float = -1.0,
        embedding_version: str = "v1",
    ) -> list[RetrievalResult]: ...

    async def delete_video(self, video_id: str) -> None: ...

    async def has_video(self, video_id: str) -> bool: ...

    async def get_chunk_count(self, video_id: str) -> int: ...

    async def clear(self) -> None: ...
