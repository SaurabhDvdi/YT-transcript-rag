"""Tests for data retention, cleanup service, and administrative endpoint."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.repositories.video import D1VideoRepository
from src.schemas.video import VideoRecord
from src.services.cleanup.service import CleanupService
from tests.conftest import MockD1Database


@pytest.mark.asyncio
async def test_cleanup_service_retention(d1_db: MockD1Database):
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="cleanup_vid", status="ready"))

    cleanup = CleanupService(db=d1_db)

    # 1. Insert old usage event (> 30 days ago)
    old_date = (datetime.now(UTC) - timedelta(days=35)).isoformat()
    recent_date = (datetime.now(UTC) - timedelta(days=2)).isoformat()

    await (
        d1_db.prepare(
            "INSERT INTO usage_events (id, session_id, event_type, created_at) VALUES (?, ?, ?, ?)"
        )
        .bind("old_event", "sess_1", "generation_succeeded", old_date)
        .run()
    )
    await (
        d1_db.prepare(
            "INSERT INTO usage_events (id, session_id, event_type, created_at) VALUES (?, ?, ?, ?)"
        )
        .bind("recent_event", "sess_1", "generation_succeeded", recent_date)
        .run()
    )

    # 2. Insert old completed job (> 7 days ago)
    old_job_date = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    await (
        d1_db.prepare(
            "INSERT INTO processing_jobs (id, video_id, job_type, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        .bind("old_job", "cleanup_vid", "TRANSCRIPT", "completed", old_job_date, old_job_date)
        .run()
    )

    # 3. Run cleanup
    res = await cleanup.run_all(usage_retention_days=30, job_retention_days=7)
    assert res["deleted_usage_events"] >= 1
    assert res["deleted_jobs"] >= 1

    # Verify old event was purged, recent event preserved
    assert (
        await d1_db.prepare("SELECT id FROM usage_events WHERE id = ?").bind("old_event").first()
        is None
    )
    assert (
        await d1_db.prepare("SELECT id FROM usage_events WHERE id = ?").bind("recent_event").first()
        is not None
    )


@pytest.mark.asyncio
async def test_admin_cleanup_route_auth(async_client: AsyncClient):
    # 1. No key -> 401
    res1 = await async_client.post("/api/v1/admin/cleanup")
    assert res1.status_code == 401

    # 2. Invalid key -> 401
    res2 = await async_client.post("/api/v1/admin/cleanup", headers={"X-Admin-Key": "wrong-secret"})
    assert res2.status_code == 401

    # 3. Valid key -> 200
    res3 = await async_client.post(
        "/api/v1/admin/cleanup", headers={"X-Admin-Key": settings.admin_api_key}
    )
    assert res3.status_code == 200
    data = res3.json()
    assert data["success"] is True
    assert "deleted_usage_events" in data["data"]
