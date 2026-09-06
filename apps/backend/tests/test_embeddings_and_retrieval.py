"""Tests for embeddings, vector store, and semantic retrieval service."""

import math

import pytest

from src.schemas.retrieval import RetrievalChunk
from src.services.retrieval.embeddings.deterministic import DeterministicEmbeddingProvider
from src.services.retrieval.service import RetrievalService
from src.services.retrieval.vector_store.in_memory import InMemoryVectorStore


@pytest.mark.asyncio
async def test_deterministic_embeddings_dimension_and_norm():
    provider = DeterministicEmbeddingProvider()
    text = "Machine learning and artificial intelligence."
    vector = await provider.embed_query(text)
    assert len(vector) == 384

    # Check unit norm (length ~ 1.0)
    norm = math.sqrt(sum(x * x for x in vector))
    assert pytest.approx(norm, rel=1e-3) == 1.0


@pytest.mark.asyncio
async def test_vector_store_isolation_and_search():
    store = InMemoryVectorStore()
    provider = DeterministicEmbeddingProvider()

    chunk1 = RetrievalChunk(
        id="chk_vid1_1",
        text="Quantum computing utilizes qubits and superposition.",
        start=0.0,
        end=10.0,
        duration=10.0,
        segment_indices=[0],
    )
    chunk2 = RetrievalChunk(
        id="chk_vid2_1",
        text="Baking sourdough bread requires flour, water, salt, and yeast.",
        start=0.0,
        end=12.0,
        duration=12.0,
        segment_indices=[0],
    )

    vec1 = await provider.embed_query(chunk1.text)
    vec2 = await provider.embed_query(chunk2.text)

    await store.add_chunks("video_1", [(chunk1, vec1)])
    await store.add_chunks("video_2", [(chunk2, vec2)])

    # Search in video_1
    query_vec = await provider.embed_query("qubits and superposition")
    results1 = await store.search("video_1", query_vec, top_k=5)
    assert len(results1) == 1
    assert results1[0].chunk.id == "chk_vid1_1"

    # Search in video_2 should not return video_1's chunks
    results2 = await store.search("video_2", query_vec, top_k=5)
    assert len(results2) == 1
    assert results2[0].chunk.id == "chk_vid2_1"


@pytest.mark.asyncio
async def test_retrieval_service_index_and_search():
    service = RetrievalService.get_instance()
    video_id = "test_vid_123"

    chunks = [
        RetrievalChunk(
            id="chk_1",
            text="Python is a popular programming language.",
            start=0.0,
            end=5.0,
            duration=5.0,
            segment_indices=[0],
        ),
        RetrievalChunk(
            id="chk_2",
            text="TypeScript adds static types to JavaScript.",
            start=6.0,
            end=12.0,
            duration=6.0,
            segment_indices=[1],
        ),
    ]

    await service.index_chunks(video_id, chunks)
    assert service.get_status(video_id) == "ready"

    results = await service.search(video_id, "static types JavaScript", top_k=1)
    assert len(results) == 1
    assert results[0].chunk.id == "chk_2"
