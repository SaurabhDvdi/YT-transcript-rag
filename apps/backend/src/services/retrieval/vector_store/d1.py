"""D1-backed persistent vector store with video and embedding version isolation."""

import json
from datetime import UTC, datetime
from typing import Any

from src.schemas.retrieval import RetrievalChunk, RetrievalResult
from src.services.retrieval.vector_store.in_memory import cosine_similarity


class D1PersistentVectorStore:
    """Persistent vector store using Cloudflare D1 with strict video isolation."""

    def __init__(self, db: Any, embedding_version: str = "v1") -> None:
        self.db = db
        self.embedding_version = embedding_version

    async def add_chunks(
        self,
        video_id: str,
        items: list[tuple[RetrievalChunk, list[float]]],
        embedding_version: str | None = None,
    ) -> None:
        ev = embedding_version or self.embedding_version
        if not items:
            return

        now_iso = datetime.now(UTC).isoformat()
        # Clean existing chunks for this video & version before re-inserting
        stmt_del = self.db.prepare(
            "DELETE FROM vector_chunks WHERE video_id = ? AND embedding_version = ?"
        ).bind(video_id, ev)
        await stmt_del.run()

        # Insert chunks (using D1 batch if available, else sequential)
        stmts = []
        for chunk, embedding in items:
            chunk_id = chunk.id if chunk.id.endswith(f":{ev}") else f"{chunk.id}:{ev}"
            blob = json.dumps(embedding)
            stmt = self.db.prepare(
                """
                INSERT OR REPLACE INTO vector_chunks (
                    id, video_id, embedding_version, chunk_index, text,
                    start, end, segment_start_index, segment_end_index,
                    token_count, embedding_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            ).bind(
                chunk_id,
                video_id,
                ev,
                chunk.chunk_index,
                chunk.text,
                chunk.start,
                chunk.end,
                chunk.segment_start_index,
                chunk.segment_end_index,
                chunk.token_count,
                blob,
                now_iso,
            )
            stmts.append(stmt)

        if hasattr(self.db, "batch") and callable(self.db.batch):
            await self.db.batch(stmts)
        else:
            for s in stmts:
                await s.run()

    async def search(
        self,
        video_id: str,
        query_vector: list[float],
        top_k: int = 5,
        min_score: float = -1.0,
        embedding_version: str | None = None,
    ) -> list[RetrievalResult]:
        ev = embedding_version or self.embedding_version
        stmt = self.db.prepare(
            """
            SELECT id, video_id, chunk_index, text, start, end,
                   segment_start_index, segment_end_index, token_count, embedding_blob
            FROM vector_chunks
            WHERE video_id = ? AND embedding_version = ?
            ORDER BY chunk_index ASC
            """
        ).bind(video_id, ev)

        res = await stmt.all()
        if isinstance(res, dict) and "results" in res:
            rows = res["results"]
        elif hasattr(res, "results"):
            rows = res.results
        else:
            rows = res or []

        if not rows:
            return []

        scored: list[RetrievalResult] = []
        for r in rows:
            d = r if isinstance(r, dict) else (r.__dict__ if hasattr(r, "__dict__") else dict(r))
            embedding = json.loads(d["embedding_blob"])
            score = cosine_similarity(query_vector, embedding)
            if score >= min_score:
                cid = d["id"]
                orig_id = cid.rsplit(":", 1)[0] if ":" in cid else cid
                chunk = RetrievalChunk(
                    id=orig_id,
                    video_id=d["video_id"],
                    chunk_index=d["chunk_index"],
                    text=d["text"],
                    start=float(d["start"]),
                    end=float(d["end"]),
                    segment_start_index=int(d["segment_start_index"]),
                    segment_end_index=int(d["segment_end_index"]),
                    token_count=int(d["token_count"]),
                )
                scored.append(RetrievalResult(chunk=chunk, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, top_k)]

    async def upsert_chunks(
        self,
        video_id: str,
        chunks: list[RetrievalChunk],
        embeddings: list[list[float]],
        embedding_version: str | None = None,
    ) -> None:
        items = list(zip(chunks, embeddings, strict=False))
        await self.add_chunks(video_id, items, embedding_version=embedding_version)

    async def query(
        self,
        video_id: str,
        query_vector: list[float],
        top_k: int = 5,
        min_score: float = -1.0,
        embedding_version: str | None = None,
    ) -> list[RetrievalResult]:
        return await self.search(
            video_id,
            query_vector,
            top_k=top_k,
            min_score=min_score,
            embedding_version=embedding_version,
        )

    async def delete_video(self, video_id: str) -> None:
        stmt = self.db.prepare("DELETE FROM vector_chunks WHERE video_id = ?").bind(video_id)
        await stmt.run()

    async def delete_chunks(self, video_id: str) -> None:
        await self.delete_video(video_id)

    async def has_video(self, video_id: str) -> bool:
        stmt = self.db.prepare("SELECT 1 FROM vector_chunks WHERE video_id = ? LIMIT 1").bind(
            video_id
        )
        row = await stmt.first()
        return row is not None

    async def get_chunk_count(self, video_id: str) -> int:
        stmt = self.db.prepare(
            "SELECT COUNT(*) as count FROM vector_chunks WHERE video_id = ?"
        ).bind(video_id)
        row = await stmt.first()
        if not row:
            return 0
        d = (
            row
            if isinstance(row, dict)
            else (row.__dict__ if hasattr(row, "__dict__") else dict(row))
        )
        return int(d.get("count", 0))

    async def clear(self) -> None:
        stmt = self.db.prepare("DELETE FROM vector_chunks")
        await stmt.run()
