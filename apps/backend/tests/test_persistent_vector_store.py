"""Tests for durable vector store persistence and video-isolated retrieval."""

import pytest

from src.repositories.video import D1VideoRepository
from src.schemas.retrieval import RetrievalChunk
from src.schemas.video import VideoRecord
from src.services.retrieval.vector_store.d1 import D1PersistentVectorStore
from tests.conftest import MockD1Database


def _make_chunk(video_id: str, index: int, text: str) -> RetrievalChunk:
    return RetrievalChunk(
        id=f"{video_id}_chunk_{index}",
        video_id=video_id,
        chunk_index=index,
        text=text,
        start=float(index * 10),
        end=float((index + 1) * 10),
        segment_start_index=index,
        segment_end_index=index,
        token_count=len(text.split()),
    )


@pytest.mark.asyncio
async def test_d1_persistent_vector_store(d1_db: MockD1Database):
    # Ensure foreign key videos exist
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="vid_vec_1", status="ready"))
    await video_repo.save(VideoRecord(video_id="vid_vec_2", status="ready"))

    store = D1PersistentVectorStore(d1_db, embedding_version="v1")

    # 1. Upsert chunks for video 1
    c1 = _make_chunk("vid_vec_1", 0, "Cloudflare Workers deploy instantly at the edge.")
    c2 = _make_chunk("vid_vec_1", 1, "Python 3.13 runs via WebAssembly in Pyodide.")
    # Dimension 3 unit vectors
    embeddings_v1 = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    await store.upsert_chunks("vid_vec_1", [c1, c2], embeddings_v1, "v1")

    # 2. Upsert chunks for video 2
    c3 = _make_chunk("vid_vec_2", 0, "Completely different topic about gardening.")
    embeddings_v2 = [
        [1.0, 0.0, 0.0],
    ]
    await store.upsert_chunks("vid_vec_2", [c3], embeddings_v2, "v1")

    # 3. Query vid_vec_1 with vector pointing to c1
    query_vec = [1.0, 0.0, 0.0]
    matches = await store.query("vid_vec_1", query_vec, top_k=2, min_score=0.0)
    assert len(matches) == 2
    top = matches[0]
    assert top.chunk.id == "vid_vec_1_chunk_0"
    assert top.chunk.text == "Cloudflare Workers deploy instantly at the edge."
    assert top.score == pytest.approx(1.0, rel=1e-3)

    # 4. Strict video isolation: video 2 query NEVER returns video 1 chunks
    matches_v2 = await store.query("vid_vec_2", query_vec, top_k=10)
    assert len(matches_v2) == 1
    assert matches_v2[0].chunk.video_id == "vid_vec_2"
    assert matches_v2[0].chunk.id == "vid_vec_2_chunk_0"

    # 5. Delete chunks for video 1
    await store.delete_chunks("vid_vec_1")
    empty_matches = await store.query("vid_vec_1", query_vec, top_k=5)
    assert len(empty_matches) == 0

    # Video 2 chunks remain untouched
    matches_v2_after = await store.query("vid_vec_2", query_vec, top_k=5)
    assert len(matches_v2_after) == 1


@pytest.mark.asyncio
async def test_d1_vector_store_version_isolation(d1_db: MockD1Database):
    video_repo = D1VideoRepository(d1_db)
    await video_repo.save(VideoRecord(video_id="vid_versions", status="ready"))

    store_v1 = D1PersistentVectorStore(d1_db, embedding_version="v1")
    store_v2 = D1PersistentVectorStore(d1_db, embedding_version="v2")

    c_v1 = _make_chunk("vid_versions", 0, "Chunk with v1 embedding")
    await store_v1.upsert_chunks("vid_versions", [c_v1], [[0.5, 0.5]], "v1")

    c_v2 = _make_chunk("vid_versions", 0, "Chunk with v2 embedding")
    await store_v2.upsert_chunks("vid_versions", [c_v2], [[0.5, 0.5]], "v2")

    # Querying with store_v1 only sees v1 chunks
    matches_v1 = await store_v1.query("vid_versions", [0.5, 0.5], top_k=5)
    assert len(matches_v1) == 1
    assert matches_v1[0].chunk.text == "Chunk with v1 embedding"

    # Querying with store_v2 only sees v2 chunks
    matches_v2 = await store_v2.query("vid_versions", [0.5, 0.5], top_k=5)
    assert len(matches_v2) == 1
    assert matches_v2[0].chunk.text == "Chunk with v2 embedding"
