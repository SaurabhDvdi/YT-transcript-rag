"""Context builder for bounded, ranked retrieval evidence assembly."""

import math

from src.core.constants import (
    MAX_CONTEXT_CHARACTERS,
    MAX_CONTEXT_CHUNKS,
    MIN_SIMILARITY_THRESHOLD,
)
from src.schemas.retrieval import RetrievalChunk, RetrievalResult
from src.services.generation.types import GenerationContext


def format_seconds(seconds: float) -> str:
    """Formats a numeric second offset into H:MM:SS or MM:SS."""
    s = max(0, math.floor(seconds))
    hrs = s // 3600
    mins = (s % 3600) // 60
    secs = s % 60
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


class ContextBuilder:
    """Builds formatted, bounded evidence context from top-K retrieval results.
    Enforces chunk count, character budgeting, and minimum similarity threshold.
    """

    def __init__(
        self,
        max_chunks: int = MAX_CONTEXT_CHUNKS,
        max_characters: int = MAX_CONTEXT_CHARACTERS,
        min_similarity: float = MIN_SIMILARITY_THRESHOLD,
    ) -> None:
        self.max_chunks = max_chunks
        self.max_characters = max_characters
        self.min_similarity = min_similarity

    def build_context(self, results: list[RetrievalResult]) -> GenerationContext:
        """Filter, rank, budget, and format retrieval results into an evidence block."""
        # 1. Filter out sub-threshold noise
        filtered = [r for r in results if r.score >= self.min_similarity]

        if not filtered:
            return GenerationContext(
                has_evidence=False,
                evidence_count=0,
                formatted_context="",
                evidence_chunks=[],
            )

        # 2. Sort descending by similarity score (highest first)
        sorted_results = sorted(filtered, key=lambda r: r.score, reverse=True)

        # 3. Slice within max_chunks
        candidate_results = sorted_results[: self.max_chunks]

        evidence_chunks: list[RetrievalChunk] = []
        formatted_blocks: list[str] = []
        current_length = 0

        for i, res in enumerate(candidate_results):
            marker = f"[E{i + 1}]"
            time_str = f"{format_seconds(res.chunk.start)} - {format_seconds(res.chunk.end)}"

            block = (
                f"{marker}\n"
                f"Chunk ID: {res.chunk.id}\n"
                f"Timestamp: {time_str} ({res.chunk.start:.1f}s - {res.chunk.end:.1f}s)\n"
                f"Score: {res.score:.4f}\n"
                f"Text: {res.chunk.text}"
            )

            # Check character budget
            if current_length + len(block) > self.max_characters and formatted_blocks:
                break

            formatted_blocks.append(block)
            evidence_chunks.append(res.chunk)
            current_length += len(block) + 2  # account for separator

        return GenerationContext(
            has_evidence=len(evidence_chunks) > 0,
            evidence_count=len(evidence_chunks),
            formatted_context="\n\n".join(formatted_blocks),
            evidence_chunks=evidence_chunks,
        )
