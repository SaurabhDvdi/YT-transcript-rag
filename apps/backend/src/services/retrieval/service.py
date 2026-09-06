"""Retrieval service orchestrating chunking, embeddings, and vector similarity search."""

import asyncio
import hashlib
from collections.abc import Callable
from typing import Any

from src.core.errors import AppError
from src.schemas.retrieval import RetrievalChunk, RetrievalResult, RetrievalStatus
from src.schemas.transcript import Transcript
from src.services.cache.service import CacheService, InMemoryCacheService
from src.services.retrieval.chunking.semantic_chunker import SemanticTranscriptChunker
from src.services.retrieval.embeddings.base import EmbeddingProvider
from src.services.retrieval.embeddings.deterministic import DeterministicEmbeddingProvider
from src.services.retrieval.vector_store import (
    CloudflareVectorizeStore,
    D1PersistentVectorStore,
    InMemoryVectorStore,
    VectorStore,
)


class RetrievalService:
    """Orchestrator for semantic chunking, embeddings, and persistent vector similarity search."""

    _instance: "RetrievalService | None" = None

    def __init__(
        self,
        chunker: SemanticTranscriptChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        cache: CacheService | None = None,
    ) -> None:
        self.chunker = chunker or SemanticTranscriptChunker()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.vector_store: VectorStore = vector_store or InMemoryVectorStore()
        self.cache: CacheService = cache or InMemoryCacheService()
        self._statuses: dict[str, RetrievalStatus] = {}
        self._in_flight_indexing: dict[str, asyncio.Task[None]] = {}

    @classmethod
    def get_instance(
        cls,
        db: Any = None,
        vectorize_binding: Any = None,
        cache: CacheService | None = None,
    ) -> "RetrievalService":
        if vectorize_binding is not None:
            fallback = D1PersistentVectorStore(db) if db is not None else InMemoryVectorStore()
            store: VectorStore = CloudflareVectorizeStore(vectorize_binding, fallback)
            return cls(vector_store=store, cache=cache)
        if db is not None:
            return cls(vector_store=D1PersistentVectorStore(db), cache=cache)
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "RetrievalService | None") -> None:
        cls._instance = instance

    def get_embedding_provider(self) -> EmbeddingProvider:
        return self.embedding_provider

    def get_vector_store(self) -> VectorStore:
        return self.vector_store

    def get_chunker(self) -> SemanticTranscriptChunker:
        return self.chunker

    def reset(self) -> None:
        self._statuses.clear()
        for task in self._in_flight_indexing.values():
            task.cancel()
        self._in_flight_indexing.clear()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.vector_store.clear())
        except RuntimeError:
            pass

    def get_status(self, video_id: str) -> RetrievalStatus:
        return self._statuses.get(video_id, "not_ready")

    def set_status(self, video_id: str, status: RetrievalStatus) -> None:
        self._statuses[video_id] = status

    async def get_chunk_count(self, video_id: str) -> int:
        return await self.vector_store.get_chunk_count(video_id)

    async def index_transcript(
        self,
        transcript: Transcript,
        wait_until: Callable[[Any], None] | None = None,
        embedding_version: str = "v1",
    ) -> None:
        """Indexes a normalized transcript into the persistent vector store."""
        video_id = transcript.video_id
        self._statuses[video_id] = "indexing"

        try:
            chunks = self.chunker.chunk_transcript(transcript)
            if not chunks:
                await self.vector_store.add_chunks(video_id, [], embedding_version)
                self._statuses[video_id] = "ready"
                return

            texts = [c.text for c in chunks]
            embeddings = await self.embedding_provider.embed_documents(texts)
            items = list(zip(chunks, embeddings, strict=False))

            await self.vector_store.add_chunks(video_id, items, embedding_version)
            self._statuses[video_id] = "ready"

            # Invalidate cached retrieval queries for this video
            await self.cache.delete_prefix(f"retrieval:v1:{video_id}:")
        except Exception:
            self._statuses[video_id] = "error"
            raise

    async def index_chunks(
        self,
        video_id: str,
        chunks: list[RetrievalChunk],
        embedding_version: str = "v1",
    ) -> None:
        """Indexes pre-formed retrieval chunks directly."""
        self._statuses[video_id] = "indexing"
        try:
            if not chunks:
                await self.vector_store.add_chunks(video_id, [], embedding_version)
                self._statuses[video_id] = "ready"
                return

            texts = [c.text for c in chunks]
            embeddings = await self.embedding_provider.embed_documents(texts)
            items = list(zip(chunks, embeddings, strict=False))

            await self.vector_store.add_chunks(video_id, items, embedding_version)
            self._statuses[video_id] = "ready"

            # Invalidate cached retrieval queries
            await self.cache.delete_prefix(f"retrieval:v1:{video_id}:")
        except Exception:
            self._statuses[video_id] = "error"
            raise

    async def search(
        self,
        video_id: str,
        query: str,
        top_k: int = 5,
        embedding_version: str = "v1",
    ) -> list[RetrievalResult]:
        """Performs semantic similarity search against the video's indexed chunks with cache support."""
        status = self.get_status(video_id)
        # Also check underlying store if status map is cold in this Worker isolate
        if status != "ready":
            has_video = await self.vector_store.has_video(video_id)
            if has_video:
                self._statuses[video_id] = "ready"
                status = "ready"

        if status != "ready":
            raise AppError(
                "RETRIEVAL_NOT_READY",
                409,
                f"Retrieval index is not ready for video {video_id} (current status: {status})",
            )

        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        cache_key = f"retrieval:v1:{video_id}:{embedding_version}:{q_hash}:{top_k}"

        cached_results = await self.cache.get(cache_key)
        if cached_results is not None:
            # Reconstruct models from cache dicts
            return [RetrievalResult.model_validate(r) for r in cached_results]

        query_vector = await self.embedding_provider.embed_query(query)
        results = await self.vector_store.search(
            video_id, query_vector, top_k=top_k, embedding_version=embedding_version
        )

        # Cache results for 1 hour (3600 seconds)
        dumpable = [r.model_dump(by_alias=True) for r in results]
        await self.cache.set(cache_key, dumpable, ttl_seconds=3600)

        return results

    async def delete_video(self, video_id: str) -> None:
        self._statuses.pop(video_id, None)
        await self.vector_store.delete_video(video_id)
        await self.cache.delete_prefix(f"retrieval:v1:{video_id}:")
