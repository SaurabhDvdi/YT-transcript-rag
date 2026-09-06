"""Tests for transcript text normalization and segment merging."""

import pytest

from src.core.errors import AppError
from src.schemas.transcript import TranscriptSegment
from src.services.transcript.normalization.normalize import normalize_text
from src.services.transcript.normalization.segment_merger import merge_transcript_segments
from src.services.transcript.normalization.validation import validate_segments


def test_normalize_text_entities():
    raw = "Rock &amp; Roll is &quot;alive&#39; &lt;here&gt;"
    normalized = normalize_text(raw)
    assert normalized == "Rock & Roll is \"alive' <here>"


def test_normalize_text_noise_tags():
    raw = "[Applause] Thank you very much [Music] for coming [Laughter] today!"
    normalized = normalize_text(raw)
    assert normalized == "Thank you very much for coming today!"


def test_normalize_text_whitespace():
    raw = "  Multiple    spaces   and\nnewlines\t\tare cleaned.  "
    normalized = normalize_text(raw)
    assert normalized == "Multiple spaces and newlines are cleaned."


def test_merge_segments_word_overlap():
    segments = [
        TranscriptSegment(index=0, start=0.0, duration=2.0, end=2.0, text="Welcome to the"),
        TranscriptSegment(index=1, start=2.1, duration=2.0, end=4.1, text="to the show today."),
    ]
    merged = merge_transcript_segments(segments)
    assert len(merged) == 1
    assert merged[0].text == "Welcome to the show today."


def test_merge_segments_gap_and_sentence():
    segments = [
        TranscriptSegment(index=0, start=0.0, duration=1.0, end=1.0, text="Hello world."),
        TranscriptSegment(index=1, start=10.0, duration=2.0, end=12.0, text="This is later."),
    ]
    merged = merge_transcript_segments(segments)
    # Long gap > 2.0s should preserve separation
    assert len(merged) == 2
    assert merged[0].text == "Hello world."
    assert merged[1].text == "This is later."


def test_validate_segments_success():
    segments = [
        TranscriptSegment(index=0, start=0.0, duration=1.0, end=1.0, text="First"),
        TranscriptSegment(index=1, start=1.2, duration=2.0, end=3.2, text="Second"),
    ]
    validate_segments(segments)  # Should not raise


def test_validate_segments_empty_raises():
    with pytest.raises(AppError):
        validate_segments([])
