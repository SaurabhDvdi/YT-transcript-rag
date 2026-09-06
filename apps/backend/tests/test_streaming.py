"""Tests for Server-Sent Events (SSE) and streaming generation."""

import pytest

from src.core.constants import NO_EVIDENCE_ANSWER_TEXT
from src.schemas.generation import TokenStreamEvent
from src.schemas.retrieval import RetrievalChunk
from src.services.conversation.service import ConversationService
from src.services.generation.providers.mock import MockLLMProvider
from src.services.generation.router import LLMRouter
from src.services.generation.service import GenerationService
from src.services.generation.sse_encoder import encode_sse
from src.services.generation.types import GenerationOptions
from src.services.retrieval.service import RetrievalService


def test_encode_sse_wire_format():
    event = TokenStreamEvent(text="Hello world")
    wire = encode_sse(event)
    assert wire.startswith("event: token\n")
    assert 'data: {"type":"token","text":"Hello world"}\n\n' in wire


@pytest.mark.asyncio
async def test_stream_answer_question_full_cycle():
    video_id = "test_vid_stream"
    chunk = RetrievalChunk(
        id="chk_stream_1",
        text="The attention mechanism allows models to focus on different positions.",
        start=0.0,
        end=10.0,
        duration=10.0,
        segment_indices=[0],
    )
    await RetrievalService.get_instance().index_chunks(video_id, [chunk])

    mock_llm = MockLLMProvider()
    mock_llm.set_custom_stream_chunks(["The ", "attention ", "mechanism. ", "[E1]"])
    router = LLMRouter(mock_llm)

    gen_service = GenerationService(router=router)
    conv_service = ConversationService.get_instance()
    conv = await conv_service.create_conversation(video_id)

    events = []
    async for event in gen_service.stream_answer_question(
        video_id=video_id,
        question="What is the attention mechanism?",
        options=GenerationOptions(conversation_id=conv.id),
    ):
        events.append(event)

    types = [e.type for e in events]
    assert "start" in types
    assert "token" in types
    assert "citation" in types
    assert "done" in types

    # Verify atomic persistence in conversation
    messages = await conv_service.get_recent_messages(conv.id)
    assert len(messages) == 2  # 1 user + 1 assistant
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].grounded is True


@pytest.mark.asyncio
async def test_stream_zero_evidence_case():
    video_id = "test_vid_zero_ev"
    # Index with empty chunks to set status="ready" and has_evidence=False
    await RetrievalService.get_instance().index_chunks(video_id, [])
    gen_service = GenerationService()
    conv_service = ConversationService.get_instance()
    conv = await conv_service.create_conversation(video_id)

    events = []
    async for event in gen_service.stream_answer_question(
        video_id=video_id,
        question="Unrelated question about astrophysics?",
        options=GenerationOptions(conversation_id=conv.id),
    ):
        events.append(event)

    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) == 1
    assert token_events[0].text == NO_EVIDENCE_ANSWER_TEXT
