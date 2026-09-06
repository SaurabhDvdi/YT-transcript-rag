"""Tests for pseudonymous session quota accounting and daily limits."""

import pytest

from src.core.config import get_settings
from src.repositories.usage import D1UsageRepository, InMemoryUsageRepository
from src.services.quota.limiter import PersistentUsageLimiter
from tests.conftest import MockD1Database


@pytest.mark.asyncio
async def test_in_memory_quota_limiter():
    usage_repo = InMemoryUsageRepository()
    limiter = PersistentUsageLimiter(usage_repo)
    session_id = "test_quota_session_1"
    settings = get_settings()

    # Initially quota is available
    decision = await limiter.check_quota(session_id, "ask")
    assert decision.allowed is True
    assert decision.remaining == settings.daily_question_quota

    # Record up to quota
    for _ in range(settings.daily_question_quota):
        await limiter.record_usage(session_id, "generation_succeeded", video_id="vid_1")

    # Next check exceeds quota
    exceeded = await limiter.check_quota(session_id, "ask")
    assert exceeded.allowed is False
    assert exceeded.remaining == 0

    # Other session has independent quota
    other_session_decision = await limiter.check_quota("other_session_2", "ask")
    assert other_session_decision.allowed is True
    assert other_session_decision.remaining == settings.daily_question_quota


@pytest.mark.asyncio
async def test_d1_quota_limiter(d1_db: MockD1Database):
    usage_repo = D1UsageRepository(d1_db)
    limiter = PersistentUsageLimiter(usage_repo)
    session_id = "d1_quota_session"
    settings = get_settings()

    # Initially allowed
    d1 = await limiter.check_quota(session_id, "transcript")
    assert d1.allowed is True
    assert d1.remaining == settings.daily_transcript_quota

    # Record all allowed transcript events
    for _ in range(settings.daily_transcript_quota):
        await limiter.record_usage(session_id, "video_registered", video_id="v1")

    # Exceeded
    d_exceeded = await limiter.check_quota(session_id, "transcript")
    assert d_exceeded.allowed is False
    assert d_exceeded.remaining == 0
