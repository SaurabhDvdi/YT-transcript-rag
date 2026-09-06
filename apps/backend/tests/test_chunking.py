"""Tests for semantic transcript chunking and token counting."""

from src.schemas.transcript import TranscriptSegment
from src.services.retrieval.chunking.semantic_chunker import SemanticTranscriptChunker
from src.services.retrieval.chunking.token_counter import HeuristicTokenCounter


def test_token_counter():
    counter = HeuristicTokenCounter()
    text = "Hello world, this is a test of the token counter."
    tokens = counter.count_tokens(text)
    assert tokens > 0
    assert tokens == round(len(text.split()) * 1.3)


def test_chunking_preserves_timestamps():
    chunker = SemanticTranscriptChunker(target_tokens=50, overlap_tokens=10)
    segments = [
        TranscriptSegment(index=0, start=0.0, duration=2.0, end=2.0, text="First sentence here."),
        TranscriptSegment(
            index=1, start=2.5, duration=3.0, end=5.5, text="Second sentence follows up."
        ),
        TranscriptSegment(
            index=2, start=6.0, duration=4.0, end=10.0, text="Third sentence completes the thought."
        ),
    ]
    chunks = chunker.chunk_transcript(segments)
    assert len(chunks) >= 1
    assert chunks[0].start == 0.0
    assert chunks[0].end >= 2.0
    assert chunks[0].id.startswith("chunk_")


def test_chunking_deterministic_ids():
    chunker = SemanticTranscriptChunker()
    segments = [
        TranscriptSegment(
            index=0,
            start=10.0,
            duration=5.0,
            end=15.0,
            text="Identical content for testing deterministic IDs.",
        ),
    ]
    chunks1 = chunker.chunk_transcript(segments)
    chunks2 = chunker.chunk_transcript(segments)
    assert chunks1[0].id == chunks2[0].id
