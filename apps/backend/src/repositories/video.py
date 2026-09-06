from datetime import UTC, datetime
from typing import Any, Protocol

from src.schemas.retrieval import RetrievalStatus
from src.schemas.video import VideoProcessingStatus, VideoRecord


class VideoRepository(Protocol):
    """Protocol for video persistence and status lifecycle."""

    async def get(self, video_id: str) -> VideoRecord | None: ...

    async def save(self, record: VideoRecord) -> None: ...

    async def update_status(
        self,
        video_id: str,
        status: VideoProcessingStatus,
        transcript_status: str | None = None,
        retrieval_status: RetrievalStatus | None = None,
        error_message: str | None = None,
    ) -> VideoRecord | None: ...

    async def delete(self, video_id: str) -> None: ...

    async def list_all(self, limit: int = 100) -> list[VideoRecord]: ...


class InMemoryVideoRepository:
    """In-memory video repository for unit testing and local development."""

    def __init__(self) -> None:
        self._store: dict[str, VideoRecord] = {}

    async def get(self, video_id: str) -> VideoRecord | None:
        return self._store.get(video_id)

    async def save(self, record: VideoRecord) -> None:
        self._store[record.video_id] = record

    async def update_status(
        self,
        video_id: str,
        status: VideoProcessingStatus,
        transcript_status: str | None = None,
        retrieval_status: RetrievalStatus | None = None,
        error_message: str | None = None,
    ) -> VideoRecord | None:
        rec = self._store.get(video_id)
        if not rec:
            return None
        now_iso = datetime.now(UTC).isoformat()
        updated = VideoRecord(
            video_id=rec.video_id,
            status=status,
            transcript_status=transcript_status or rec.transcript_status,
            retrieval_status=retrieval_status or rec.retrieval_status,
            language_code=rec.language_code,
            language=rec.language,
            transcript_provider=rec.transcript_provider,
            transcript_hash=rec.transcript_hash,
            transcript_version=rec.transcript_version,
            normalization_version=rec.normalization_version,
            chunker_version=rec.chunker_version,
            embedding_model=rec.embedding_model,
            embedding_version=rec.embedding_version,
            error_message=error_message if error_message is not None else rec.error_message,
            created_at=rec.created_at,
            updated_at=now_iso,
        )
        self._store[video_id] = updated
        return updated

    async def delete(self, video_id: str) -> None:
        self._store.pop(video_id, None)

    async def list_all(self, limit: int = 100) -> list[VideoRecord]:
        return list(self._store.values())[:limit]


class D1VideoRepository:
    """D1-backed video repository for Cloudflare Workers."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def get(self, video_id: str) -> VideoRecord | None:
        stmt = self.db.prepare("SELECT * FROM videos WHERE video_id = ? LIMIT 1").bind(video_id)
        row = await stmt.first()
        if not row:
            return None
        return self._row_to_record(row)

    async def save(self, record: VideoRecord) -> None:
        stmt = self.db.prepare(
            """
            INSERT INTO videos (
                video_id, status, transcript_status, retrieval_status,
                language_code, language, transcript_provider, transcript_hash,
                transcript_version, normalization_version, chunker_version,
                embedding_model, embedding_version, error_message,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                status = excluded.status,
                transcript_status = excluded.transcript_status,
                retrieval_status = excluded.retrieval_status,
                language_code = excluded.language_code,
                language = excluded.language,
                transcript_provider = excluded.transcript_provider,
                transcript_hash = excluded.transcript_hash,
                transcript_version = excluded.transcript_version,
                normalization_version = excluded.normalization_version,
                chunker_version = excluded.chunker_version,
                embedding_model = excluded.embedding_model,
                embedding_version = excluded.embedding_version,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
            """
        ).bind(
            record.video_id,
            record.status,
            record.transcript_status,
            record.retrieval_status,
            record.language_code,
            record.language,
            record.transcript_provider,
            record.transcript_hash,
            record.transcript_version,
            record.normalization_version,
            record.chunker_version,
            record.embedding_model,
            record.embedding_version,
            record.error_message,
            record.created_at,
            record.updated_at,
        )
        await stmt.run()

    async def update_status(
        self,
        video_id: str,
        status: VideoProcessingStatus,
        transcript_status: str | None = None,
        retrieval_status: RetrievalStatus | None = None,
        error_message: str | None = None,
    ) -> VideoRecord | None:
        existing = await self.get(video_id)
        if not existing:
            return None

        now_iso = datetime.now(UTC).isoformat()
        new_ts_status = transcript_status or existing.transcript_status
        new_ret_status = retrieval_status or existing.retrieval_status
        new_err = error_message if error_message is not None else existing.error_message

        stmt = self.db.prepare(
            """
            UPDATE videos
            SET status = ?, transcript_status = ?, retrieval_status = ?, error_message = ?, updated_at = ?
            WHERE video_id = ?
            """
        ).bind(status, new_ts_status, new_ret_status, new_err, now_iso, video_id)
        await stmt.run()

        return await self.get(video_id)

    async def delete(self, video_id: str) -> None:
        stmt = self.db.prepare("DELETE FROM videos WHERE video_id = ?").bind(video_id)
        await stmt.run()

    async def list_all(self, limit: int = 100) -> list[VideoRecord]:
        stmt = self.db.prepare("SELECT * FROM videos ORDER BY updated_at DESC LIMIT ?").bind(limit)
        res = await stmt.all()
        if isinstance(res, dict) and "results" in res:
            results = res["results"]
        elif hasattr(res, "results"):
            results = res.results
        else:
            results = res or []
        return [self._row_to_record(row) for row in (results or [])]

    def _row_to_record(self, row: Any) -> VideoRecord:
        if hasattr(row, "__dict__"):
            d = row.__dict__
        elif isinstance(row, dict):
            d = row
        else:
            d = dict(row)

        return VideoRecord(
            video_id=d["video_id"],
            status=d["status"],
            transcript_status=d.get("transcript_status", "not_ready"),
            retrieval_status=d.get("retrieval_status", "not_ready"),
            language_code=d.get("language_code"),
            language=d.get("language"),
            transcript_provider=d.get("transcript_provider"),
            transcript_hash=d.get("transcript_hash"),
            transcript_version=d.get("transcript_version", "v1"),
            normalization_version=d.get("normalization_version", "v1"),
            chunker_version=d.get("chunker_version", "v1"),
            embedding_model=d.get("embedding_model", "deterministic-384"),
            embedding_version=d.get("embedding_version", "v1"),
            error_message=d.get("error_message"),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
