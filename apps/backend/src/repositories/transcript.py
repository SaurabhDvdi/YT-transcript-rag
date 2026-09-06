"""Transcript repository protocol and implementations (InMemory and D1)."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

from src.schemas.transcript import Transcript, TranscriptSegment


class TranscriptRepository(Protocol):
    """Protocol for durable transcript artifact storage."""

    async def save(
        self,
        transcript: Transcript,
        provider_name: str = "youtube-innertube",
        normalization_version: str = "v1",
    ) -> None: ...

    async def get(self, video_id: str, language_code: str | None = None) -> Transcript | None: ...

    async def delete(self, video_id: str) -> None: ...


class InMemoryTranscriptRepository:
    """In-memory transcript repository for unit testing and local development."""

    def __init__(self) -> None:
        self._store: dict[str, Transcript] = {}

    async def save(
        self,
        transcript: Transcript,
        provider_name: str = "youtube-innertube",
        normalization_version: str = "v1",
    ) -> None:
        key = f"{transcript.video_id}:{transcript.language_code}"
        self._store[key] = transcript

    async def get(self, video_id: str, language_code: str | None = None) -> Transcript | None:
        if language_code:
            return self._store.get(f"{video_id}:{language_code}")
        # Find any matching video_id
        for key, trans in self._store.items():
            if key.startswith(f"{video_id}:"):
                return trans
        return None

    async def delete(self, video_id: str) -> None:
        keys_to_del = [k for k in self._store if k.startswith(f"{video_id}:")]
        for k in keys_to_del:
            del self._store[k]


class D1TranscriptRepository:
    """D1-backed transcript repository for Cloudflare Workers."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def save(
        self,
        transcript: Transcript,
        provider_name: str = "youtube-innertube",
        normalization_version: str = "v1",
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        segments_json = json.dumps([s.model_dump(by_alias=True) for s in transcript.segments])
        t_hash = hashlib.sha256(segments_json.encode("utf-8")).hexdigest()[:32]

        stmt = self.db.prepare(
            """
            INSERT INTO transcripts (
                video_id, language_code, language, is_auto_generated,
                segments, total_duration, transcript_hash, normalization_version,
                provider_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id, language_code) DO UPDATE SET
                language = excluded.language,
                is_auto_generated = excluded.is_auto_generated,
                segments = excluded.segments,
                total_duration = excluded.total_duration,
                transcript_hash = excluded.transcript_hash,
                normalization_version = excluded.normalization_version,
                provider_name = excluded.provider_name,
                updated_at = excluded.updated_at
            """
        ).bind(
            transcript.video_id,
            transcript.language_code,
            transcript.language,
            1 if transcript.is_auto_generated else 0,
            segments_json,
            transcript.total_duration,
            t_hash,
            normalization_version,
            provider_name,
            now_iso,
            now_iso,
        )
        await stmt.run()

    async def get(self, video_id: str, language_code: str | None = None) -> Transcript | None:
        if language_code:
            stmt = self.db.prepare(
                "SELECT * FROM transcripts WHERE video_id = ? AND language_code = ? LIMIT 1"
            ).bind(video_id, language_code)
        else:
            stmt = self.db.prepare(
                "SELECT * FROM transcripts WHERE video_id = ? ORDER BY is_auto_generated ASC LIMIT 1"
            ).bind(video_id)

        row = await stmt.first()
        if not row:
            return None
        return self._row_to_transcript(row)

    async def delete(self, video_id: str) -> None:
        stmt = self.db.prepare("DELETE FROM transcripts WHERE video_id = ?").bind(video_id)
        await stmt.run()

    def _row_to_transcript(self, row: Any) -> Transcript:
        d = (
            row
            if isinstance(row, dict)
            else (row.__dict__ if hasattr(row, "__dict__") else dict(row))
        )
        raw_segs = json.loads(d["segments"])
        segments = [
            TranscriptSegment(
                index=s["index"],
                start=s["start"],
                duration=s["duration"],
                end=s["end"],
                text=s["text"],
            )
            for s in raw_segs
        ]
        return Transcript(
            video_id=d["video_id"],
            language=d["language"],
            language_code=d["language_code"],
            is_auto_generated=bool(d.get("is_auto_generated", 0)),
            segments=segments,
            total_duration=float(d["total_duration"]),
        )
