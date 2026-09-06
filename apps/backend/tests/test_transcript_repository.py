"""Tests for durable transcript repository (in-memory and D1 implementations)."""

import pytest

from src.repositories.transcript import D1TranscriptRepository, InMemoryTranscriptRepository
from src.repositories.video import D1VideoRepository
from src.schemas.transcript import Transcript, TranscriptSegment
from src.schemas.video import VideoRecord
from tests.conftest import MockD1Database


def _make_sample_transcript(video_id: str, lang: str = "en") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="English" if lang == "en" else "Spanish",
        language_code=lang,
        is_auto_generated=False,
        total_duration=120.5,
        segments=[
            TranscriptSegment(
                text="Welcome to this video tutorial.",
                start=0.0,
                duration=3.5,
                end=3.5,
                index=0,
            ),
            TranscriptSegment(
                text="Today we learn about Cloudflare Workers.",
                start=3.5,
                duration=4.0,
                end=7.5,
                index=1,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_in_memory_transcript_repository():
    repo = InMemoryTranscriptRepository()
    t = _make_sample_transcript("mem_vid_1")

    # 1. Non-existent returns None
    assert await repo.get("mem_vid_1", "en") is None

    # 2. Save and retrieve
    await repo.save(t)
    saved = await repo.get("mem_vid_1", "en")
    assert saved is not None
    assert saved.video_id == "mem_vid_1"
    assert len(saved.segments) == 2
    assert saved.segments[0].text == "Welcome to this video tutorial."

    # 3. Delete
    await repo.delete("mem_vid_1")
    assert await repo.get("mem_vid_1", "en") is None


@pytest.mark.asyncio
async def test_d1_transcript_repository(d1_db: MockD1Database):
    # Ensure foreign key video exists
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="d1_vid_t", status="ready"))

    repo = D1TranscriptRepository(d1_db)
    t = _make_sample_transcript("d1_vid_t", "en")

    # 1. Save
    await repo.save(t)

    # 2. Retrieve
    saved = await repo.get("d1_vid_t", "en")
    assert saved is not None
    assert saved.video_id == "d1_vid_t"
    assert saved.total_duration == 120.5
    assert len(saved.segments) == 2
    assert saved.segments[1].duration == 4.0

    # 3. Fallback to first available language when language_code is None
    fallback = await repo.get("d1_vid_t", None)
    assert fallback is not None
    assert fallback.language_code == "en"

    # 4. Add Spanish transcript
    t_es = _make_sample_transcript("d1_vid_t", "es")
    await repo.save(t_es)

    # 5. Delete all transcripts for video
    await repo.delete("d1_vid_t")
    assert await repo.get("d1_vid_t", "es") is None
    assert await repo.get("d1_vid_t", "en") is None


@pytest.mark.asyncio
async def test_d1_transcript_cascade_delete(d1_db: MockD1Database):
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="cascade_vid", status="ready"))

    transcript_repo = D1TranscriptRepository(d1_db)
    await transcript_repo.save(_make_sample_transcript("cascade_vid", "en"))
    assert await transcript_repo.get("cascade_vid", "en") is not None

    # Delete parent video directly
    await d1_db.prepare("DELETE FROM videos WHERE video_id = ?").bind("cascade_vid").run()

    # Transcript should be cascaded
    assert await transcript_repo.get("cascade_vid", "en") is None
