"""Central transcript service managing durable acquisition lifecycle, caching, and jobs."""

import asyncio
import contextlib
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.core.errors import AppError
from src.repositories.transcript import (
    D1TranscriptRepository,
    InMemoryTranscriptRepository,
    TranscriptRepository,
)
from src.repositories.video import D1VideoRepository, InMemoryVideoRepository, VideoRepository
from src.schemas.transcript import Transcript, TranscriptSummary
from src.schemas.video import VideoRecord
from src.services.cache.service import CacheService, InMemoryCacheService
from src.services.job.service import JobService
from src.services.transcript.provider_registry import ProviderRegistry
from src.services.transcript.providers.mock_fallback import MockFallbackProvider
from src.services.transcript.providers.youtube_innertube import YouTubeInnertubeProvider
from src.services.transcript.providers.youtube_watch import YouTubeWatchProvider
from src.services.transcript.types import (
    TranscriptOptions,
    TranscriptResult,
    VideoProcessingRecord,
    VideoProcessingStatus,
)


class TranscriptService:
    """Central transcript service coordinating durable acquisition, state machine, and jobs."""

    _instance: "TranscriptService | None" = None

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        video_repo: VideoRepository | None = None,
        transcript_repo: TranscriptRepository | None = None,
        job_service: JobService | None = None,
        cache: CacheService | None = None,
    ) -> None:
        if registry is not None:
            self.registry = registry
        else:
            self.registry = ProviderRegistry(
                [
                    YouTubeInnertubeProvider(),
                    YouTubeWatchProvider(),
                    MockFallbackProvider(),
                ]
            )
        self.video_repo: VideoRepository = video_repo or InMemoryVideoRepository()
        self.transcript_repo: TranscriptRepository = (
            transcript_repo or InMemoryTranscriptRepository()
        )
        self.job_service: JobService = job_service or JobService()
        self.cache: CacheService = cache or InMemoryCacheService()

        self._records: dict[str, VideoProcessingRecord] = {}
        self._in_flight_jobs: dict[str, asyncio.Task[TranscriptResult]] = {}

    @classmethod
    def get_instance(
        cls,
        db: Any = None,
        cache: CacheService | None = None,
    ) -> "TranscriptService":
        if db is not None:
            video_repo = D1VideoRepository(db)
            transcript_repo = D1TranscriptRepository(db)
            job_service = JobService.get_instance(db)
            return cls(
                video_repo=video_repo,
                transcript_repo=transcript_repo,
                job_service=job_service,
                cache=cache,
            )
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "TranscriptService | None") -> None:
        cls._instance = instance

    def get_registry(self) -> ProviderRegistry:
        return self.registry

    def reset(self) -> None:
        """Resets internal in-memory state (useful in test suites)."""
        self._records.clear()
        for task in self._in_flight_jobs.values():
            task.cancel()
        self._in_flight_jobs.clear()
        from src.services.retrieval.service import RetrievalService

        RetrievalService.get_instance().reset()

    def get_record(self, video_id: str) -> VideoProcessingRecord | None:
        rec = self._records.get(video_id)
        return rec

    async def get_record_async(self, video_id: str) -> VideoProcessingRecord | None:
        """Async record lookup checking memory, cache, and durable VideoRepository."""
        rec = self._records.get(video_id)
        if rec:
            return rec

        cached = await self.cache.get(f"video-status:v1:{video_id}")
        if cached:
            return VideoProcessingRecord(
                video_id=video_id,
                status=cached.get("status", "accepted"),
                updated_at=float(cached.get("updated_at", time.time())),
            )

        v_rec = await self.video_repo.get(video_id)
        if v_rec:
            # Check if transcript is stored
            transcript = await self.transcript_repo.get(video_id)
            summary = None
            if transcript:
                summary = TranscriptSummary(
                    language=transcript.language,
                    language_code=transcript.language_code,
                    is_auto_generated=transcript.is_auto_generated,
                    segment_count=len(transcript.segments),
                    duration=transcript.total_duration,
                )
            record = VideoProcessingRecord(
                video_id=v_rec.video_id,
                status=v_rec.status,
                transcript=transcript,
                summary=summary,
                error=v_rec.error_message,
                updated_at=time.time(),
            )
            self._records[video_id] = record
            return record

        return None

    def get_transcript(self, video_id: str) -> Transcript | None:
        rec = self._records.get(video_id)
        return rec.transcript if rec else None

    async def get_transcript_async(self, video_id: str) -> Transcript | None:
        """Async transcript lookup checking memory, cache, and durable TranscriptRepository."""
        rec = self._records.get(video_id)
        if rec and rec.transcript:
            return rec.transcript

        cached = await self.cache.get(f"transcript:v1:{video_id}")
        if cached:
            return Transcript.model_validate(cached)

        transcript = await self.transcript_repo.get(video_id)
        if transcript:
            if rec:
                rec.transcript = transcript
            await self.cache.set(
                f"transcript:v1:{video_id}",
                transcript.model_dump(by_alias=True),
                ttl_seconds=86400,
            )
            return transcript

        return None

    def process_video(
        self,
        video_id: str,
        options: TranscriptOptions | None = None,
        wait_until: Callable[[Any], None] | None = None,
    ) -> VideoProcessingRecord:
        """Initiates or returns existing transcript processing for a video."""
        existing = self._records.get(video_id)
        if existing:
            if existing.status in ("ready", "processing"):
                return existing
            is_stale = (time.time() - existing.updated_at) > 30.0
            if not is_stale:
                return existing

        initial_record = VideoProcessingRecord(
            video_id=video_id,
            status="accepted",
            updated_at=time.time(),
        )
        self._records[video_id] = initial_record

        # Schedule background acquisition
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._execute_acquisition(video_id, options, wait_until))
            self._in_flight_jobs[video_id] = task
            if wait_until:
                wait_until(task)
        except RuntimeError:
            pass

        return initial_record

    async def process_video_sync(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> VideoProcessingRecord:
        """Processes a video and awaits full completion. Useful for tests and synchronous callers."""
        existing = self._records.get(video_id)
        if existing and existing.status == "ready":
            return existing

        in_flight = self._in_flight_jobs.get(video_id)
        if in_flight:
            with contextlib.suppress(Exception):
                await in_flight
            return self._records.get(video_id) or VideoProcessingRecord(
                video_id=video_id, status="error", updated_at=time.time()
            )

        await self._execute_acquisition(video_id, options)
        return self._records.get(video_id) or VideoProcessingRecord(
            video_id=video_id, status="error", updated_at=time.time()
        )

    async def _execute_acquisition(
        self,
        video_id: str,
        options: TranscriptOptions | None = None,
        wait_until: Callable[[Any], None] | None = None,
    ) -> TranscriptResult:
        # 1. Job deduplication and single-flight control
        job, is_new = await self.job_service.get_or_create_job(video_id, "TRANSCRIPT")
        await self.job_service.mark_started(job.id)

        now_iso = datetime.now(UTC).isoformat()
        now_ts = time.time()

        self._records[video_id] = VideoProcessingRecord(
            video_id=video_id,
            status="processing",
            updated_at=now_ts,
        )

        # Save or update video record in repository
        v_rec = await self.video_repo.get(video_id)
        if not v_rec:
            v_rec = VideoRecord(
                video_id=video_id,
                status="processing",
                transcript_status="processing",
                retrieval_status="not_ready",
                created_at=now_iso,
                updated_at=now_iso,
            )
            await self.video_repo.save(v_rec)
        else:
            await self.video_repo.update_status(
                video_id, status="processing", transcript_status="processing"
            )

        try:
            result = await self.registry.get_transcript(video_id, options)

            transcript = Transcript(
                video_id=result.video_id,
                language=result.language,
                language_code=result.language_code,
                is_auto_generated=result.is_auto_generated,
                segments=result.segments,
                total_duration=result.total_duration,
            )
            summary = TranscriptSummary(
                language=result.language,
                language_code=result.language_code,
                is_auto_generated=result.is_auto_generated,
                segment_count=len(result.segments),
                duration=result.total_duration,
            )

            # 2. Persist transcript in durable TranscriptRepository
            provider = result.source.provider if result.source else "youtube-innertube"
            await self.transcript_repo.save(
                transcript, provider_name=provider, normalization_version="v1"
            )

            # 3. Update video record in durable VideoRepository
            await self.video_repo.update_status(
                video_id,
                status="ready",
                transcript_status="ready",
                retrieval_status="indexing",
            )

            # 4. Mark job completed
            await self.job_service.mark_completed(job.id)

            self._records[video_id] = VideoProcessingRecord(
                video_id=video_id,
                status="ready",
                transcript=transcript,
                summary=summary,
                updated_at=time.time(),
            )

            # Invalidate/update cache
            await self.cache.set(
                f"video-status:v1:{video_id}",
                {"status": "ready", "updated_at": time.time()},
                ttl_seconds=60,
            )
            await self.cache.set(
                f"transcript:v1:{video_id}",
                transcript.model_dump(by_alias=True),
                ttl_seconds=86400,
            )

            # 5. Trigger retrieval indexing upon transcript readiness
            from src.services.retrieval.service import RetrievalService

            retrieval_svc = RetrievalService.get_instance()
            index_coro = retrieval_svc.index_transcript(transcript)
            if wait_until:
                wait_until(index_coro)
            else:
                await index_coro

            await self.video_repo.update_status(
                video_id,
                status="ready",
                transcript_status="ready",
                retrieval_status="ready",
            )

            return result
        except AppError as err:
            err_status: VideoProcessingStatus = (
                "unavailable"
                if err.code
                in (
                    "TRANSCRIPT_UNAVAILABLE",
                    "TRANSCRIPT_NOT_FOUND",
                    "CAPTIONS_UNAVAILABLE",
                    "LANGUAGE_UNAVAILABLE",
                )
                else "error"
            )
            await self.job_service.mark_failed(job.id, err.code, err.message)
            await self.video_repo.update_status(
                video_id,
                status=err_status,
                transcript_status="error",
                error_message=err.message,
            )
            self._records[video_id] = VideoProcessingRecord(
                video_id=video_id,
                status=err_status,
                error=err.message,
                updated_at=time.time(),
            )
            raise
        except Exception as err:
            await self.job_service.mark_failed(job.id, "INTERNAL_ERROR", str(err))
            await self.video_repo.update_status(
                video_id,
                status="error",
                transcript_status="error",
                error_message=str(err),
            )
            self._records[video_id] = VideoProcessingRecord(
                video_id=video_id,
                status="error",
                error=str(err),
                updated_at=time.time(),
            )
            raise
        finally:
            self._in_flight_jobs.pop(video_id, None)
