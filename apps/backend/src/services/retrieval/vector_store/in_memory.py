"""In-memory vector store implementation with strict video-level isolation."""

import math
from dataclasses import dataclass

from src.schemas.retrieval import RetrievalChunk, RetrievalResult


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Robust cosine similarity calculation between two numeric vectors."""
    if len(a) != len(b) or not a:
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for va, vb in zip(a, b, strict=False):
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    sim = dot / denom
    if math.isnan(sim) or math.isinf(sim):
        return 0.0

    return sim


@dataclass
class VectorEntry:
    chunk: RetrievalChunk
    embedding: list[float]


class InMemoryVectorStore:
    """In-memory vector store partitioned strictly by videoId."""

    def __init__(self) -> None:
        self._store: dict[str, list[VectorEntry]] = {}

    async def upsert_vectors(self, video_id: str, entries: list[VectorEntry]) -> None:
        existing = self._store.get(video_id, [])
        entry_map: dict[str, VectorEntry] = {e.chunk.id: e for e in existing}

        for entry in entries:
            entry_map[entry.chunk.id] = entry

        self._store[video_id] = list(entry_map.values())

    async def add_chunks(
        self,
        video_id: str,
        items: list[tuple[RetrievalChunk, list[float]]],
        embedding_version: str = "v1",
    ) -> None:
        entries = [VectorEntry(chunk=c, embedding=v) for c, v in items]
        await self.upsert_vectors(video_id, entries)

    async def search(
        self,
        video_id: str,
        query_vector: list[float],
        top_k: int = 5,
        min_score: float = -1.0,
        embedding_version: str = "v1",
    ) -> list[RetrievalResult]:
        entries = self._store.get(video_id)
        if not entries:
            return []

        scored: list[RetrievalResult] = []
        for entry in entries:
            score = cosine_similarity(query_vector, entry.embedding)
            if score >= min_score:
                scored.append(RetrievalResult(chunk=entry.chunk, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[: max(1, top_k)]

    async def delete_video(self, video_id: str) -> None:
        self._store.pop(video_id, None)

    async def has_video(self, video_id: str) -> bool:
        return video_id in self._store

    async def get_chunk_count(self, video_id: str) -> int:
        entries = self._store.get(video_id)
        return len(entries) if entries else 0

    async def clear(self) -> None:
        self._store.clear()
