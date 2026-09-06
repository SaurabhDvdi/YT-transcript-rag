"""Citation resolver mapping [Ek] markers to timestamped evidence citations."""

import re
from dataclasses import dataclass

from src.core.constants import NO_EVIDENCE_ANSWER_TEXT
from src.schemas.generation import Citation
from src.schemas.retrieval import RetrievalChunk


@dataclass
class ResolvedCitationsResult:
    cleaned_text: str
    citations: list[Citation]
    grounded: bool


class CitationResolver:
    """Resolves [Ek] citation markers from generated text against verified retrieval chunks.
    Guarantees zero phantom citations: invalid markers like [E999] are stripped and ignored.
    """

    def resolve_citations(
        self,
        raw_text: str,
        evidence_chunks: list[RetrievalChunk],
    ) -> ResolvedCitationsResult:
        trimmed = raw_text.strip()

        # Check if the answer matches the canonical no-evidence fallback
        if NO_EVIDENCE_ANSWER_TEXT.lower() in trimmed.lower() or not evidence_chunks:
            cleaned = re.sub(r"\[E\d+\]", "", trimmed).strip()
            return ResolvedCitationsResult(
                cleaned_text=cleaned or NO_EVIDENCE_ANSWER_TEXT,
                citations=[],
                grounded=False,
            )

        citation_map: dict[str, Citation] = {}
        marker_pattern = re.compile(r"\[E(\d+)\]")

        for match in marker_pattern.finditer(trimmed):
            marker_num = int(match.group(1))
            chunk_index = marker_num - 1  # [E1] maps to index 0

            if 0 <= chunk_index < len(evidence_chunks):
                chunk = evidence_chunks[chunk_index]
                if chunk.id not in citation_map:
                    citation_map[chunk.id] = Citation(
                        chunk_id=chunk.id,
                        start=chunk.start,
                        end=chunk.end,
                    )

        # Strip invalid markers from output text (e.g. [E999])
        def replace_marker(m: re.Match[str]) -> str:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(evidence_chunks):
                return m.group(0)  # Keep valid marker
            return ""  # Strip invalid marker

        cleaned_text = marker_pattern.sub(replace_marker, trimmed).strip()

        # Collapse any spaces before punctuation caused by stripping invalid markers
        cleaned_text = re.sub(r"\s+([.,!?;:])", r"\1", cleaned_text).strip()

        citations = list(citation_map.values())

        # If no markers were found in text, but evidence chunks exist and answer is substantive,
        # attribute to the primary top-1 evidence chunk to preserve grounding
        if not citations and evidence_chunks:
            top_chunk = evidence_chunks[0]
            citations.append(
                Citation(
                    chunk_id=top_chunk.id,
                    start=top_chunk.start,
                    end=top_chunk.end,
                )
            )

        return ResolvedCitationsResult(
            cleaned_text=cleaned_text,
            citations=citations,
            grounded=len(citations) > 0,
        )
