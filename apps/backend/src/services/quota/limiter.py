"""Usage limiter and quota accounting service."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol

from src.core.config import get_settings
from src.repositories.usage import InMemoryUsageRepository, UsageRepository
from src.schemas.quota import QuotaDecision, UsageEvent, UsageEventType


class UsageLimiter(Protocol):
    """Protocol for session-scoped quota enforcement and usage recording."""

    async def check_quota(
        self, session_id: str, operation: str, user_id: str | None = None
    ) -> QuotaDecision: ...

    async def record_usage(
        self,
        session_id: str,
        operation: UsageEventType,
        video_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        user_id: str | None = None,
    ) -> None: ...


class PersistentUsageLimiter:
    """Production usage limiter backed by UsageRepository (D1 or InMemory)."""

    def __init__(self, usage_repo: UsageRepository | None = None) -> None:
        self.repo = usage_repo or InMemoryUsageRepository()

    def _get_start_of_day_utc(self) -> tuple[str, str]:
        now = datetime.now(UTC)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        next_day = start_of_day + timedelta(days=1)
        return start_of_day.isoformat(), next_day.isoformat()

    async def check_quota(
        self, session_id: str, operation: str, user_id: str | None = None
    ) -> QuotaDecision:
        settings = get_settings()
        since_iso, reset_iso = self._get_start_of_day_utc()

        if operation in ("ask", "generation"):
            max_allowed = settings.daily_question_quota
            used = await self.repo.count_events(
                session_id,
                ["generation_requested", "generation_succeeded"],
                since_iso,
                user_id=user_id,
            )
            if used >= max_allowed:
                return QuotaDecision(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_iso,
                    reason=f"Daily question quota of {max_allowed} exceeded.",
                )
            return QuotaDecision(
                allowed=True,
                remaining=max(0, max_allowed - used),
                reset_at=reset_iso,
            )

        if operation in ("transcript", "process_video"):
            max_allowed = settings.daily_transcript_quota
            used = await self.repo.count_events(
                session_id,
                ["video_registered", "transcript_processed"],
                since_iso,
                user_id=user_id,
            )
            if used >= max_allowed:
                return QuotaDecision(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_iso,
                    reason=f"Daily transcript processing quota of {max_allowed} exceeded.",
                )
            return QuotaDecision(
                allowed=True,
                remaining=max(0, max_allowed - used),
                reset_at=reset_iso,
            )

        # Default allowed for other non-billable ops
        return QuotaDecision(allowed=True, remaining=None, reset_at=reset_iso)

    async def record_usage(
        self,
        session_id: str,
        operation: UsageEventType,
        video_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        user_id: str | None = None,
    ) -> None:
        event = UsageEvent(
            id=f"usage-{uuid.uuid4().hex}",
            session_id=session_id,
            user_id=user_id,
            video_id=video_id,
            event_type=operation,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            created_at=datetime.now(UTC).isoformat(),
        )
        await self.repo.record_event(event)
