"""Usage repository protocol and implementations (InMemory and D1)."""

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from src.schemas.quota import UsageEvent


class UsageRepository(Protocol):
    """Protocol for operational usage event storage and quota aggregation."""

    async def record_event(self, event: UsageEvent) -> None: ...

    async def count_events(
        self,
        session_id: str,
        event_types: list[str],
        since_iso: str,
        user_id: str | None = None,
    ) -> int: ...

    async def purge_old_events(self, retention_days: int) -> int: ...


class InMemoryUsageRepository:
    """In-memory usage repository for unit testing and local development."""

    def __init__(self) -> None:
        self._events: list[UsageEvent] = []

    async def record_event(self, event: UsageEvent) -> None:
        self._events.append(event)

    async def count_events(
        self,
        session_id: str,
        event_types: list[str],
        since_iso: str,
        user_id: str | None = None,
    ) -> int:
        count = 0
        for ev in self._events:
            matches_owner = (
                (ev.user_id == user_id) if user_id is not None else (ev.session_id == session_id)
            )
            if matches_owner and ev.event_type in event_types and ev.created_at >= since_iso:
                count += 1
        return count

    async def purge_old_events(self, retention_days: int) -> int:
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        initial_len = len(self._events)
        self._events = [ev for ev in self._events if ev.created_at >= cutoff]
        return initial_len - len(self._events)


class D1UsageRepository:
    """D1-backed usage repository for Cloudflare Workers."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def record_event(self, event: UsageEvent) -> None:
        stmt = self.db.prepare(
            """
            INSERT INTO usage_events (
                id, session_id, user_id, video_id, event_type, provider, model,
                input_tokens, output_tokens, latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        ).bind(
            event.id,
            event.session_id,
            event.user_id,
            event.video_id,
            event.event_type,
            event.provider,
            event.model,
            event.input_tokens,
            event.output_tokens,
            event.latency_ms,
            event.created_at,
        )
        await stmt.run()

    async def count_events(
        self,
        session_id: str,
        event_types: list[str],
        since_iso: str,
        user_id: str | None = None,
    ) -> int:
        if not event_types:
            return 0
        placeholders = ",".join("?" for _ in event_types)
        if user_id is not None:
            query = f"""
                SELECT COUNT(*) as count FROM usage_events
                WHERE user_id = ? AND event_type IN ({placeholders}) AND created_at >= ?
            """
            params = [user_id, *event_types, since_iso]
        else:
            query = f"""
                SELECT COUNT(*) as count FROM usage_events
                WHERE session_id = ? AND event_type IN ({placeholders}) AND created_at >= ?
            """
            params = [session_id, *event_types, since_iso]
        stmt = self.db.prepare(query).bind(*params)
        row = await stmt.first()
        if not row:
            return 0
        d = (
            row
            if isinstance(row, dict)
            else (row.__dict__ if hasattr(row, "__dict__") else dict(row))
        )
        return int(d.get("count", 0))

    async def purge_old_events(self, retention_days: int) -> int:
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        stmt = self.db.prepare("DELETE FROM usage_events WHERE created_at < ?").bind(cutoff)
        res = await stmt.run()
        meta = res.get("meta", {}) if isinstance(res, dict) else (getattr(res, "meta", {}) or {})
        return meta.get("changes", 0) if isinstance(meta, dict) else 0
