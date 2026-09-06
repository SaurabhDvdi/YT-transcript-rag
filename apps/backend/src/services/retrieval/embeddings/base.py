"""Base EmbeddingProvider protocol definition."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Abstract embedding provider interface."""

    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_query(self, text: str) -> list[float]: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
