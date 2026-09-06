"""Transcript structure and safety limit validation."""

from src.core.errors import AppError
from src.schemas.transcript import Transcript, TranscriptSegment
from src.services.transcript.normalization.constants import (
    MAX_SEGMENTS_COUNT,
    MAX_TRANSCRIPT_CHARACTERS,
)


def validate_transcript_segment(seg: TranscriptSegment, index: int) -> None:
    """Validates an individual transcript segment."""
    if seg.index != index:
        raise AppError(
            "PROVIDER_INVALID_RESPONSE",
            502,
            f"Invalid segment index at position {index}: expected {index}, got {seg.index}.",
        )
    if seg.start is None or seg.start < 0:
        raise AppError(
            "PROVIDER_INVALID_RESPONSE",
            502,
            f"Invalid segment start timestamp at index {index}: {seg.start}.",
        )
    if seg.duration is None or seg.duration < 0:
        raise AppError(
            "PROVIDER_INVALID_RESPONSE",
            502,
            f"Invalid segment duration timestamp at index {index}: {seg.duration}.",
        )
    if seg.end is None or seg.end < seg.start:
        raise AppError(
            "PROVIDER_INVALID_RESPONSE",
            502,
            f"Invalid segment end timestamp at index {index}: start={seg.start}, end={seg.end}.",
        )
    if not isinstance(seg.text, str) or not seg.text.strip():
        raise AppError(
            "PROVIDER_INVALID_RESPONSE",
            502,
            f"Empty or non-string segment text at index {index}.",
        )


def validate_transcript(transcript: Transcript) -> None:
    """Enforces safety limits and structural invariants on the normalized transcript."""
    if not transcript:
        raise AppError("PROVIDER_INVALID_RESPONSE", 502, "Transcript object is null or None.")

    if not transcript.video_id:
        raise AppError(
            "PROVIDER_INVALID_RESPONSE", 502, "Missing or invalid videoId in transcript."
        )

    if not transcript.language or not transcript.language_code:
        raise AppError("PROVIDER_INVALID_RESPONSE", 502, "Missing language metadata in transcript.")

    if not transcript.segments or len(transcript.segments) == 0:
        raise AppError(
            "TRANSCRIPT_NOT_FOUND",
            404,
            "No valid transcript segments found for this video.",
        )

    if len(transcript.segments) > MAX_SEGMENTS_COUNT:
        raise AppError(
            "TRANSCRIPT_TOO_LARGE",
            413,
            f"Transcript segment count ({len(transcript.segments)}) exceeds maximum allowable limit ({MAX_SEGMENTS_COUNT}).",
        )

    total_chars = 0
    for i, seg in enumerate(transcript.segments):
        validate_transcript_segment(seg, i)
        total_chars += len(seg.text)

    if total_chars > MAX_TRANSCRIPT_CHARACTERS:
        raise AppError(
            "TRANSCRIPT_TOO_LARGE",
            413,
            f"Total transcript characters ({total_chars}) exceeds maximum allowable limit ({MAX_TRANSCRIPT_CHARACTERS}).",
        )


def validate_segments(segments: list[TranscriptSegment]) -> None:
    """Helper validating a list of segments."""
    if not segments:
        raise AppError("TRANSCRIPT_NOT_FOUND", 404, "No segments to validate.")
    for i, seg in enumerate(segments):
        validate_transcript_segment(seg, i)
