"""Context quality metrics: precision, recall, duplicate chunk rate, and unique evidence coverage."""

from evaluation.metrics.retrieval import compute_temporal_iou
from evaluation.models import ContextMetrics, RetrievalTestCase
from src.schemas.retrieval import RetrievalChunk


def compute_text_similarity(t1: str, t2: str) -> float:
    """Computes Jaccard word-level similarity between two chunk texts."""
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1.intersection(words2)) / len(words1.union(words2))


def evaluate_context_quality(
    test_cases: list[RetrievalTestCase],
    context_chunks_map: dict[str, list[RetrievalChunk]],
) -> ContextMetrics:
    """Evaluates context precision, context recall, duplicate rate, and evidence coverage."""
    cases_with_evidence = [tc for tc in test_cases if tc.expectedEvidence or tc.expectedChunkIds]
    if not cases_with_evidence:
        return ContextMetrics(
            context_precision=1.0,
            context_recall=1.0,
            duplicate_chunk_rate=0.0,
            unique_evidence_coverage=1.0,
        )

    precisions: list[float] = []
    recalls: list[float] = []
    duplicate_counts = 0
    total_chunks = 0
    coverage_ratios: list[float] = []

    for tc in cases_with_evidence:
        chunks = context_chunks_map.get(tc.id, [])
        if not chunks:
            precisions.append(0.0)
            recalls.append(0.0)
            coverage_ratios.append(0.0)
            continue

        total_chunks += len(chunks)

        # Check duplicates among returned chunks
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                sim = compute_text_similarity(chunks[i].text, chunks[j].text)
                if sim >= 0.85:
                    duplicate_counts += 1

        # Check precision and recall against gold intervals
        relevant_chunks = 0
        intervals_covered = set()

        for c in chunks:
            is_c_rel = False
            for idx, interval in enumerate(tc.expectedEvidence):
                iou = compute_temporal_iou(c.start, c.end, interval.start, interval.end)
                if iou >= 0.15 or c.id in tc.expectedChunkIds:
                    is_c_rel = True
                    intervals_covered.add(idx)
            if is_c_rel:
                relevant_chunks += 1

        prec = relevant_chunks / len(chunks)
        precisions.append(prec)

        expected_count = max(1, len(tc.expectedEvidence) or len(tc.expectedChunkIds))
        rec = len(intervals_covered) / expected_count
        recalls.append(min(1.0, rec))
        coverage_ratios.append(len(intervals_covered) / expected_count)

    dup_rate = duplicate_counts / max(1, total_chunks)

    def avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    return ContextMetrics(
        context_precision=avg(precisions),
        context_recall=avg(recalls),
        duplicate_chunk_rate=round(dup_rate, 4),
        unique_evidence_coverage=avg(coverage_ratios),
    )
