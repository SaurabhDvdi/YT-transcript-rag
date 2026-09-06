"""End-to-end durability test simulating worker reboot and persistent state restoration."""

import pytest

from src.repositories.transcript import D1TranscriptRepository
from src.repositories.video import D1VideoRepository
from src.schemas.transcript import Transcript, TranscriptSegment
from src.schemas.video import VideoRecord
from src.services.conversation.repositories.d1 import (
    D1ConversationRepository,
    D1MessageRepository,
)
from src.services.conversation.service import ConversationService
from src.services.retrieval.service import RetrievalService
from src.services.retrieval.vector_store.d1 import D1PersistentVectorStore
from src.services.transcript.service import TranscriptService
from tests.conftest import MockD1Database


@pytest.mark.asyncio
async def test_end_to_end_durability_across_restarts(d1_db: MockD1Database):
    video_id = "durable_e2e_video_101"

    # === PHASE A: Write state into D1 using Phase 8 repositories ===
    video_repo = D1VideoRepository(d1_db)
    transcript_repo = D1TranscriptRepository(d1_db)
    vector_store = D1PersistentVectorStore(d1_db, embedding_version="v1")
    conv_repo = D1ConversationRepository(d1_db)
    msg_repo = D1MessageRepository(d1_db)

    # 1. Register video
    await video_repo.save(
        VideoRecord(
            video_id=video_id,
            status="ready",
            transcript_status="ready",
            retrieval_status="ready",
            language="English",
            language_code="en",
        )
    )

    # 2. Persist transcript
    t = Transcript(
        video_id=video_id,
        language="English",
        language_code="en",
        is_auto_generated=False,
        total_duration=60.0,
        segments=[
            TranscriptSegment(
                text="The Cloudflare Python runtime is durable and fast.",
                start=0.0,
                duration=5.0,
                end=5.0,
                index=0,
            )
        ],
    )
    await transcript_repo.save(t)

    # 3. Index vector chunks into D1
    retrieval_service = RetrievalService(vector_store=vector_store)
    await retrieval_service.index_transcript(t)

    # 4. Create conversation and add messages
    conv_service = ConversationService(conversation_repo=conv_repo, message_repo=msg_repo)
    conv = await conv_service.create_conversation(video_id, "Durability Chat")
    await conv_service.add_user_message(conv.id, "Is the system durable?")
    await conv_service.add_assistant_message(
        conv.id,
        "Yes, all state is durably persisted in Cloudflare D1.",
        citations=[],
    )

    # === PHASE B: Simulate Backend Worker Restart / Reboot ===
    # Reset all singletons and create brand new service instances connected to the same D1 DB
    new_video_repo = D1VideoRepository(d1_db)
    new_transcript_repo = D1TranscriptRepository(d1_db)
    new_vector_store = D1PersistentVectorStore(d1_db, embedding_version="v1")
    new_conv_repo = D1ConversationRepository(d1_db)
    new_msg_repo = D1MessageRepository(d1_db)

    new_transcript_service = TranscriptService(
        video_repo=new_video_repo,
        transcript_repo=new_transcript_repo,
    )
    new_retrieval_service = RetrievalService(vector_store=new_vector_store)
    new_conv_service = ConversationService(
        conversation_repo=new_conv_repo, message_repo=new_msg_repo
    )

    # === PHASE C: Verify all state is preserved and functional after reboot ===
    # 1. Video record is preserved
    restored_video = await new_video_repo.get(video_id)
    assert restored_video is not None
    assert restored_video.status == "ready"
    assert restored_video.language_code == "en"

    # 2. Transcript is retrieved from D1 without re-fetching
    restored_transcript = await new_transcript_service.get_transcript_async(video_id)
    assert restored_transcript is not None
    assert restored_transcript.video_id == video_id
    assert len(restored_transcript.segments) == 1
    assert "Cloudflare Python" in restored_transcript.segments[0].text

    # 3. Vector chunks are queried directly from D1
    results = await new_retrieval_service.search(video_id, "runtime speed", top_k=1)
    assert len(results) == 1
    assert "Cloudflare Python runtime" in results[0].chunk.text

    # 4. Conversation history and messages are fully intact
    restored_conv = await new_conv_service.get_conversation(conv.id)
    assert restored_conv is not None
    assert restored_conv.title == "Durability Chat"
    messages = await new_conv_service.get_recent_messages(conv.id, limit=10)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Is the system durable?"
    assert messages[1].role == "assistant"
    assert "durably persisted" in messages[1].content
