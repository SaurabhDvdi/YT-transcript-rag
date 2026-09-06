"""Comprehensive integration tests for all REST API endpoints."""

import pytest
from httpx import AsyncClient

from src.services.transcript.service import TranscriptService


@pytest.mark.asyncio
async def test_video_registration_and_status(async_client: AsyncClient):
    # Invalid video ID
    resp = await async_client.post("/api/v1/videos", json={"videoId": "invalid_id!"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_VIDEO_ID"

    # Missing video ID
    resp = await async_client.post("/api/v1/videos", json={})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"

    # Valid registration (11 chars)
    valid_id = "dQw4w9WgXcQ"
    resp = await async_client.post("/api/v1/videos", json={"videoId": valid_id})
    assert resp.status_code == 202
    data = resp.json()
    assert data["success"] is True
    assert data["video"]["videoId"] == valid_id
    assert "retrievalStatus" in data

    # Get status
    resp_status = await async_client.get(f"/api/v1/videos/{valid_id}")
    assert resp_status.status_code == 200
    assert resp_status.json()["video"]["videoId"] == valid_id


@pytest.mark.asyncio
async def test_transcript_endpoint(async_client: AsyncClient):
    valid_id = "abc12345678"
    # Register video and await completion
    await async_client.post("/api/v1/videos", json={"videoId": valid_id})
    await TranscriptService.get_instance().process_video_sync(valid_id)

    # Fetch transcript
    resp = await async_client.get(f"/api/v1/videos/{valid_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["videoId"] == valid_id
    assert len(data["transcript"]["segments"]) > 0


@pytest.mark.asyncio
async def test_retrieval_endpoint(async_client: AsyncClient):
    valid_id = "xyz98765432"
    # Search unregistered video -> 404
    resp = await async_client.post(f"/api/v1/videos/{valid_id}/retrieval", json={"query": "test"})
    assert resp.status_code == 404

    # Register video and await indexing
    await async_client.post("/api/v1/videos", json={"videoId": valid_id})
    await TranscriptService.get_instance().process_video_sync(valid_id)

    # Search with valid query
    resp = await async_client.post(
        f"/api/v1/videos/{valid_id}/retrieval",
        json={"query": "overview and architecture", "topK": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "results" in data


@pytest.mark.asyncio
async def test_conversation_routes(async_client: AsyncClient):
    valid_id = "conv1234567"
    await async_client.post("/api/v1/videos", json={"videoId": valid_id})

    # Create conversation
    resp = await async_client.post(f"/api/v1/videos/{valid_id}/conversations")
    assert resp.status_code == 201
    conv = resp.json()["conversation"]
    conv_id = conv["id"]
    assert conv["videoId"] == valid_id

    # List conversations
    resp = await async_client.get(f"/api/v1/videos/{valid_id}/conversations")
    assert resp.status_code == 200
    assert len(resp.json()["conversations"]) == 1

    # Get conversation detail
    resp = await async_client.get(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["conversation"]["id"] == conv_id

    # Rename conversation
    resp = await async_client.patch(
        f"/api/v1/conversations/{conv_id}", json={"title": "Updated Title"}
    )
    assert resp.status_code == 200
    assert resp.json()["conversation"]["title"] == "Updated Title"

    # Delete conversation
    resp = await async_client.delete(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_ask_endpoint_non_streaming_and_streaming(async_client: AsyncClient):
    valid_id = "ask12345678"
    await async_client.post("/api/v1/videos", json={"videoId": valid_id})
    await TranscriptService.get_instance().process_video_sync(valid_id)

    # Non-streaming ask
    resp = await async_client.post(
        f"/api/v1/videos/{valid_id}/ask",
        json={"question": "What is discussed in this video?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "answer" in data
    assert data["answer"]["text"] is not None

    # Streaming ask (?stream=true)
    resp_stream = await async_client.post(
        f"/api/v1/videos/{valid_id}/ask?stream=true",
        json={"question": "Explain the key concepts."},
    )
    assert resp_stream.status_code == 200
    assert "text/event-stream" in resp_stream.headers["content-type"]
    text_content = resp_stream.text
    assert "event: start" in text_content
    assert "event: token" in text_content
    assert "event: done" in text_content
