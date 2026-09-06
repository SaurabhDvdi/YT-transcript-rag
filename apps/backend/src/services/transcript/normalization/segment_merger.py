"""Intelligent segment merger preserving timestamps and removing overlaps."""

import re
from dataclasses import dataclass

from src.schemas.transcript import TranscriptSegment
from src.services.transcript.normalization.constants import (
    MAX_SEGMENT_CHARACTERS,
    MAX_SEGMENT_DURATION,
    MERGE_GAP_SECONDS,
)
from src.services.transcript.normalization.normalize import clean_caption_text
from src.services.transcript.types import RawCaptionEvent

SENTENCE_BOUNDARY_REGEX = re.compile(r'[.?!]["\']?$')


@dataclass
class _IntermediateSegment:
    start: float
    duration: float
    end: float
    text: str


def round_timestamp(seconds: float) -> float:
    """Rounds a number to millisecond precision (3 decimal places in seconds)."""
    return round(seconds, 3)


def ends_with_sentence_boundary(text: str) -> bool:
    """Checks if a string ends with terminal sentence punctuation (. ? !)."""
    return bool(SENTENCE_BOUNDARY_REGEX.search(text.strip()))


def deduplicate_overlap(text_a: str, text_b: str) -> str:
    """Deduplicates overlapping words between two consecutive segments."""
    words_a = text_a.split()
    words_b = text_b.split()
    max_overlap = min(len(words_a), len(words_b), 6)

    for overlap in range(max_overlap, 0, -1):
        suffix_a = " ".join(words_a[-overlap:]).lower()
        prefix_b = " ".join(words_b[:overlap]).lower()
        if suffix_a == prefix_b:
            return " ".join(words_b[overlap:])

    return text_b


def merge_raw_caption_events(events: list[RawCaptionEvent]) -> list[TranscriptSegment]:
    """Merges raw caption events into clean, readable, timestamp-preserved segments."""
    if not events:
        return []

    # 1. Initial cleanup and filtering
    cleaned: list[_IntermediateSegment] = []
    for event in events:
        if event.t_start_ms is None or event.t_start_ms < 0:
            continue
        text = clean_caption_text(event.text or "")
        if not text:
            continue

        start = round_timestamp(event.t_start_ms / 1000.0)
        duration = round_timestamp(max(0.0, (event.d_duration_ms or 0) / 1000.0))
        end = round_timestamp(start + duration)

        cleaned.append(_IntermediateSegment(start=start, duration=duration, end=end, text=text))

    if not cleaned:
        return []

    cleaned.sort(key=lambda s: s.start)

    # 2. Intelligent fragment merging
    merged: list[_IntermediateSegment] = []
    current = _IntermediateSegment(
        start=cleaned[0].start,
        duration=cleaned[0].duration,
        end=cleaned[0].end,
        text=cleaned[0].text,
    )

    for i in range(1, len(cleaned)):
        next_seg = cleaned[i]

        # Exact duplicate in consecutive segments
        if next_seg.text.lower() == current.text.lower():
            current.end = max(current.end, next_seg.end)
            current.duration = round_timestamp(current.end - current.start)
            continue

        # Deduplicate word overlap
        deduped_next = deduplicate_overlap(current.text, next_seg.text)
        if not deduped_next:
            current.end = max(current.end, next_seg.end)
            current.duration = round_timestamp(current.end - current.start)
            continue

        gap = next_seg.start - current.end
        combined_duration = max(current.end, next_seg.end) - current.start
        combined_length = len(current.text) + 1 + len(deduped_next)
        current_is_complete = ends_with_sentence_boundary(current.text) and (
            current.duration >= 3.0 or len(current.text) >= 40
        )

        can_merge = (
            gap <= MERGE_GAP_SECONDS
            and combined_duration <= MAX_SEGMENT_DURATION
            and combined_length <= MAX_SEGMENT_CHARACTERS
            and not current_is_complete
        )

        if can_merge:
            current.end = round_timestamp(max(current.end, next_seg.end))
            current.duration = round_timestamp(current.end - current.start)
            current.text = f"{current.text} {deduped_next}"
        else:
            merged.append(
                _IntermediateSegment(
                    start=current.start,
                    duration=current.duration,
                    end=current.end,
                    text=current.text.strip(),
                )
            )
            current = _IntermediateSegment(
                start=next_seg.start,
                duration=next_seg.duration,
                end=next_seg.end,
                text=deduped_next.strip(),
            )

    if current and current.text.strip():
        merged.append(
            _IntermediateSegment(
                start=current.start,
                duration=current.duration,
                end=current.end,
                text=current.text.strip(),
            )
        )

    # 3. Final sequential model mapping
    return [
        TranscriptSegment(
            index=idx,
            start=seg.start,
            duration=seg.duration,
            end=seg.end,
            text=seg.text,
        )
        for idx, seg in enumerate(merged)
    ]


def merge_transcript_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Helper merging existing TranscriptSegment objects."""
    events = [
        RawCaptionEvent(
            t_start_ms=int(s.start * 1000),
            d_duration_ms=int(s.duration * 1000),
            text=s.text,
        )
        for s in segments
    ]
    return merge_raw_caption_events(events)
