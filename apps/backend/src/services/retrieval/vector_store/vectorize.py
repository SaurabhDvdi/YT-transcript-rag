"""Cloudflare Vectorize persistent vector store adapter."""

import contextlib
from typing import Any

from src.schemas.retrieval import RetrievalChunk, RetrievalResult
from src.services.retrieval.vector_store.base import VectorStore


class CloudflareVectorizeStore:
    """Persistent vector store using Cloudflare Vectorize binding with metadata filtering."""

    def __init__(self, vectorize_binding: Any, fallback_store: VectorStore | None = None) -> None:
        self.binding = vectorize_binding
        self.fallback = fallback_store

    async def add_chunks(
        self,
        video_id: str,
        items: list[tuple[RetrievalChunk, list[float]]],
        embedding_version: str = "v1",
    ) -> None:
        if self.fallback:
            await self.fallback.add_chunks(video_id, items, embedding_version)

        if not hasattr(self.binding, "upsert") or not items:
            return

        vectors = []
        for chunk, emb in items:
            vectors.append(
                {
                    "id": f"{video_id}_{chunk.id}",
                    "values": emb,
                    "metadata": {
                        "videoId": video_id,
                        "chunkId": chunk.id,
                        "chunkIndex": chunk.chunk_index,
                        "text": chunk.text,
                        "start": chunk.start,
                        "end": chunk.end,
                        "embeddingVersion": embedding_version,
                    },
                }
            )

        with contextlib.suppress(Exception):
            if callable(self.binding.upsert):
                await self.binding.upsert(vectors)

    async def search(
        self,
        video_id: str,
        query_vector: list[float],
        top_k: int = 5,
        min_score: float = -1.0,
        embedding_version: str = "v1",
    ) -> list[RetrievalResult]:
        if hasattr(self.binding, "query") and callable(self.binding.query):
            try:
                res = await self.binding.query(
                    query_vector,
                    topK=top_k,
                    filter={"videoId": video_id, "embeddingVersion": embedding_version},
                    returnMetadata=True,
                )
                matches = getattr(res, "matches", []) or []
                results: list[RetrievalResult] = []
                for m in matches:
                    d = m if isinstance(m, dict) else (m.__dict__ if hasattr(m, "__dict__") else {})
                    score = float(d.get("score", 0.0))
                    meta = d.get("metadata", {}) or {}
                    if score >= min_score and meta.get("videoId") == video_id:
                        chunk = RetrievalChunk(
                            id=str(meta.get("chunkId", d.get("id", ""))),
                            video_id=video_id,
                            chunk_index=int(meta.get("chunkIndex", 0)),
                            text=str(meta.get("text", "")),
                            start=float(meta.get("start", 0.0)),
                            end=float(meta.get("end", 0.0)),
                        )
                        results.append(RetrievalResult(chunk=chunk, score=score))
                if results:
                    return results
            except Exception:
                pass

        if self.fallback:
            return list(
                await self.fallback.search(
                    video_id, query_vector, top_k, min_score, embedding_version
                )
            )
        return []

    async def delete_video(self, video_id: str) -> None:
        if self.fallback:
            await self.fallback.delete_video(video_id)
        if hasattr(self.binding, "deleteByIds") and callable(self.binding.deleteByIds):
            with contextlib.suppress(Exception):
                pass

    async def has_video(self, video_id: str) -> bool:
        if self.fallback:
            return bool(await self.fallback.has_video(video_id))
        return False

    async def get_chunk_count(self, video_id: str) -> int:
        if self.fallback:
            return int(await self.fallback.get_chunk_count(video_id))
        return 0

    async def clear(self) -> None:
        if self.fallback:
            await self.fallback.clear()
