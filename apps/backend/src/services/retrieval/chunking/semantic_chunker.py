"""Semantic transcript chunker respecting segment boundaries and managing token overlap."""

from dataclasses import dataclass

from src.core.constants import CHUNK_OVERLAP_TOKENS, TARGET_CHUNK_TOKENS
from src.schemas.retrieval import RetrievalChunk
from src.schemas.transcript import Transcript, TranscriptSegment
from src.services.retrieval.chunking.token_counter import HeuristicTokenCounter

DEFAULT_TARGET_TOKENS = TARGET_CHUNK_TOKENS
DEFAULT_OVERLAP_TOKENS = CHUNK_OVERLAP_TOKENS
MAX_CHUNK_TOKENS = 450
MIN_CHUNK_TOKENS = 50


def fnv1a_hash(s: str) -> str:
    """Fast 32-bit FNV-1a hash implementation matching TypeScript Math.imul behavior."""
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def generate_chunk_id(video_id: str, index: int, text: str) -> str:
    h = fnv1a_hash(text[:48])
    return f"chunk_{video_id}_{index}_{h}"


@dataclass
class ChunkOptions:
    target_tokens: int = DEFAULT_TARGET_TOKENS
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS
    max_tokens: int = MAX_CHUNK_TOKENS
    min_tokens: int = MIN_CHUNK_TOKENS


class SemanticTranscriptChunker:
    """Semantic transcript chunker that respects sentence boundaries and sliding-window overlap."""

    def __init__(
        self,
        token_counter: HeuristicTokenCounter | None = None,
        target_tokens: int = DEFAULT_TARGET_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> None:
        self.token_counter = token_counter or HeuristicTokenCounter()
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_transcript(
        self, transcript: Transcript | list[TranscriptSegment], options: ChunkOptions | None = None
    ) -> list[RetrievalChunk]:
        if isinstance(transcript, list):
            segments = transcript
            video_id = "test"
        else:
            segments = transcript.segments
            video_id = transcript.video_id

        if not segments:
            return []

        target_tokens = options.target_tokens if options else self.target_tokens
        overlap_tokens = options.overlap_tokens if options else self.overlap_tokens
        max_tokens = options.max_tokens if options else MAX_CHUNK_TOKENS
        min_tokens = options.min_tokens if options else MIN_CHUNK_TOKENS

        chunks: list[RetrievalChunk] = []
        current_start_index = 0
        total_segments = len(segments)

        while current_start_index < total_segments:
            current_segments: list[TranscriptSegment] = []
            accumulated_text = ""
            accumulated_tokens = 0
            last_included_index = current_start_index

            for i in range(current_start_index, total_segments):
                seg = segments[i]
                candidate_text = f"{accumulated_text} {seg.text}" if accumulated_text else seg.text
                candidate_tokens = self.token_counter.count_tokens(candidate_text)

                # First segment always included
                if not current_segments:
                    current_segments.append(seg)
                    accumulated_text = candidate_text
                    accumulated_tokens = candidate_tokens
                    last_included_index = i
                    continue

                # Exceeds max tokens
                if candidate_tokens > max_tokens:
                    break

                current_segments.append(seg)
                accumulated_text = candidate_text
                accumulated_tokens = candidate_tokens
                last_included_index = i

                if accumulated_tokens >= target_tokens:
                    break

            if not current_segments:
                break

            first_seg = current_segments[0]
            last_seg = current_segments[-1]

            # Merge trailing chunk if too small
            if (
                last_included_index == total_segments - 1
                and chunks
                and accumulated_tokens < min_tokens
            ):
                prev_chunk = chunks[-1]
                merged_text = f"{prev_chunk.text} {accumulated_text}"
                merged_tokens = self.token_counter.count_tokens(merged_text)
                if merged_tokens <= max_tokens:
                    prev_chunk.text = merged_text
                    prev_chunk.end = last_seg.end
                    prev_chunk.segment_end_index = last_included_index
                    prev_chunk.token_count = merged_tokens
                    prev_chunk.id = generate_chunk_id(
                        video_id,
                        prev_chunk.chunk_index,
                        merged_text,
                    )
                    break

            chunk_index = len(chunks)
            chunks.append(
                RetrievalChunk(
                    id=generate_chunk_id(video_id, chunk_index, accumulated_text),
                    video_id=video_id,
                    chunk_index=chunk_index,
                    text=accumulated_text,
                    start=first_seg.start,
                    end=last_seg.end,
                    segment_start_index=current_start_index,
                    segment_end_index=last_included_index,
                    token_count=accumulated_tokens,
                )
            )

            if last_included_index >= total_segments - 1:
                break

            # Calculate nextStartIndex for overlap
            next_start = last_included_index
            overlap_acc = 0

            for j in range(last_included_index, current_start_index, -1):
                seg_tokens = self.token_counter.count_tokens(segments[j].text)
                if overlap_acc + seg_tokens > overlap_tokens and overlap_acc > 0:
                    break
                overlap_acc += seg_tokens
                next_start = j

            if next_start <= current_start_index:
                next_start = current_start_index + 1

            current_start_index = next_start

        return chunks
