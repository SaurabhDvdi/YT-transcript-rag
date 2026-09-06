"""Tests for generation service, prompt building, citation resolver, and query rewriter."""

import pytest

from src.schemas.conversation import ConversationMessage
from src.schemas.retrieval import RetrievalChunk, RetrievalResult
from src.services.conversation.service import ConversationService
from src.services.generation.citation_resolver import CitationResolver
from src.services.generation.context_builder import ContextBuilder
from src.services.generation.providers.mock import MockLLMProvider
from src.services.generation.rewriter.deterministic import DeterministicQueryRewriter
from src.services.generation.router import LLMRouter
from src.services.generation.service import GenerationService
from src.services.generation.types import GenerationOptions
from src.services.retrieval.service import RetrievalService


def test_context_builder_budgeting():
    builder = ContextBuilder(max_chunks=2, min_similarity=0.25)
    chunks = [
        RetrievalResult(
            chunk=RetrievalChunk(
                id="c1",
                text="Chunk one content.",
                start=10.0,
                end=20.0,
                duration=10.0,
                segment_indices=[0],
            ),
            score=0.9,
        ),
        RetrievalResult(
            chunk=RetrievalChunk(
                id="c2",
                text="Chunk two content.",
                start=25.0,
                end=35.0,
                duration=10.0,
                segment_indices=[1],
            ),
            score=0.8,
        ),
        RetrievalResult(
            chunk=RetrievalChunk(
                id="c3",
                text="Chunk three content.",
                start=40.0,
                end=50.0,
                duration=10.0,
                segment_indices=[2],
            ),
            score=0.7,
        ),
    ]
    ctx = builder.build_context(chunks)
    assert ctx.has_evidence is True
    assert ctx.evidence_count == 2
    assert "[E1]" in ctx.formatted_context
    assert "[E2]" in ctx.formatted_context
    assert "[E3]" not in ctx.formatted_context


@pytest.mark.asyncio
async def test_deterministic_query_rewriter():
    rewriter = DeterministicQueryRewriter()
    history = [
        ConversationMessage(
            id="m1",
            conversation_id="c1",
            role="user",
            content="What is self-attention?",
            created_at="2026-01-01T00:00:00Z",
        ),
        ConversationMessage(
            id="m2",
            conversation_id="c1",
            role="assistant",
            content="It is an attention mechanism.",
            created_at="2026-01-01T00:00:01Z",
        ),
    ]

    # Exact follow-up match
    res1 = await rewriter.rewrite("Why?", history)
    assert res1 == "Why is self-attention useful?"

    # Pronoun match
    res2 = await rewriter.rewrite("How does it work?", history)
    assert "self-attention" in res2


def test_citation_resolver_valid_and_phantom():
    resolver = CitationResolver()
    evidence = [
        RetrievalChunk(
            id="chk_real_1",
            text="Real fact one.",
            start=10.0,
            end=15.0,
            duration=5.0,
            segment_indices=[0],
        ),
        RetrievalChunk(
            id="chk_real_2",
            text="Real fact two.",
            start=20.0,
            end=25.0,
            duration=5.0,
            segment_indices=[1],
        ),
    ]

    text = "The system was proposed in 2017 [E1]. Some phantom claim [E999]."
    res = resolver.resolve_citations(text, evidence)

    assert res.grounded is True
    assert len(res.citations) == 1
    assert res.citations[0].chunk_id == "chk_real_1"
    assert "[E1]" in res.cleaned_text
    assert "[E999]" not in res.cleaned_text


@pytest.mark.asyncio
async def test_generation_service_end_to_end():
    video_id = "test_vid_gen"
    chunk = RetrievalChunk(
        id="chk_transformers",
        text="The Transformer architecture was introduced in the Attention Is All You Need paper.",
        start=30.0,
        end=45.0,
        duration=15.0,
        segment_indices=[0],
    )
    await RetrievalService.get_instance().index_chunks(video_id, [chunk])

    mock_llm = MockLLMProvider()
    mock_llm.setDefaultResponse("Transformers were introduced in Attention Is All You Need. [E1]")
    router = LLMRouter(mock_llm)

    gen_service = GenerationService(router=router)
    conv_service = ConversationService.get_instance()
    conv = await conv_service.create_conversation(video_id)

    result = await gen_service.answer_question(
        video_id=video_id,
        question="When were transformers introduced?",
        options=GenerationOptions(conversation_id=conv.id),
    )

    assert result.grounded is True
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chk_transformers"

    # Verify auto-titling happened
    updated_conv = await conv_service.get_conversation(conv.id)
    assert updated_conv is not None
    assert updated_conv.title != "New Conversation"
