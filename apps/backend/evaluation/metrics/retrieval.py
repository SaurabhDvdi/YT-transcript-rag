"""Retrieval quality metrics: Recall@K, Precision@K, MRR, and Temporal IoU."""

from collections import defaultdict

from evaluation.models import EvidenceInterval, RetrievalMetrics, RetrievalTestCase
from src.schemas.retrieval import RetrievalResult


def compute_temporal_iou(
    retrieved_start: float,
    retrieved_end: float,
    gold_start: float,
    gold_end: float,
) -> float:
    """Calculates temporal Intersection over Union (IoU) between two time intervals."""
    intersection_start = max(retrieved_start, gold_start)
    intersection_end = min(retrieved_end, gold_end)
    intersection = max(0.0, intersection_end - intersection_start)

    union_start = min(retrieved_start, gold_start)
    union_end = max(retrieved_end, gold_end)
    union = max(1e-6, union_end - union_start)

    return intersection / union


def is_chunk_relevant(
    result: RetrievalResult,
    gold_intervals: list[EvidenceInterval],
    gold_chunk_ids: list[str],
    min_iou: float = 0.15,
) -> tuple[bool, float]:
    """Determines if a retrieved chunk is relevant via exact chunkId match or temporal IoU."""
    # 1. Exact chunkId match
    if result.chunk.id in gold_chunk_ids:
        return True, 1.0

    # 2. Temporal IoU match against any gold interval
    max_iou = 0.0
    for interval in gold_intervals:
        iou = compute_temporal_iou(
            result.chunk.start,
            result.chunk.end,
            interval.start,
            interval.end,
        )
        if iou > max_iou:
            max_iou = iou

    if max_iou >= min_iou:
        return True, max_iou

    return False, max_iou


def evaluate_retrieval_suite(
    test_cases: list[RetrievalTestCase],
    results_map: dict[str, list[RetrievalResult]],
    video_metadata_map: dict[str, dict[str, str]],
) -> RetrievalMetrics:
    """Evaluates the entire retrieval test suite and produces aggregate and sliced metrics."""
    cases_with_evidence = [tc for tc in test_cases if tc.expectedEvidence or tc.expectedChunkIds]
    if not cases_with_evidence:
        return RetrievalMetrics(
            recall_at_1=0.0,
            recall_at_3=0.0,
            recall_at_5=0.0,
            recall_at_10=0.0,
            precision_at_5=0.0,
            mrr=0.0,
            mean_iou=0.0,
        )

    r_at_1_hits = 0
    r_at_3_hits = 0
    r_at_5_hits = 0
    r_at_10_hits = 0
    precision_at_5_sum = 0.0
    reciprocal_ranks: list[float] = []
    all_ious: list[float] = []

    # Breakdowns
    category_mrr: dict[str, list[float]] = defaultdict(list)
    category_r5: dict[str, list[float]] = defaultdict(list)

    qtype_mrr: dict[str, list[float]] = defaultdict(list)
    qtype_r5: dict[str, list[float]] = defaultdict(list)

    duration_mrr: dict[str, list[float]] = defaultdict(list)
    duration_r5: dict[str, list[float]] = defaultdict(list)

    for tc in cases_with_evidence:
        retrieved = results_map.get(tc.id, [])
        first_relevant_rank = 0
        hits_in_top_5 = 0
        case_best_iou = 0.0

        for rank, res in enumerate(retrieved, start=1):
            is_rel, iou = is_chunk_relevant(res, tc.expectedEvidence, tc.expectedChunkIds)
            if iou > case_best_iou:
                case_best_iou = iou

            if is_rel:
                if first_relevant_rank == 0:
                    first_relevant_rank = rank
                if rank <= 5:
                    hits_in_top_5 += 1

        all_ious.append(case_best_iou)

        # Hits at K
        hit_1 = 1.0 if (0 < first_relevant_rank <= 1) else 0.0
        hit_3 = 1.0 if (0 < first_relevant_rank <= 3) else 0.0
        hit_5 = 1.0 if (0 < first_relevant_rank <= 5) else 0.0
        hit_10 = 1.0 if (0 < first_relevant_rank <= 10) else 0.0

        r_at_1_hits += int(hit_1)
        r_at_3_hits += int(hit_3)
        r_at_5_hits += int(hit_5)
        r_at_10_hits += int(hit_10)

        # Precision@5
        precision_at_5_sum += hits_in_top_5 / 5.0

        # Reciprocal rank
        rr = 1.0 / first_relevant_rank if first_relevant_rank > 0 else 0.0
        reciprocal_ranks.append(rr)

        # Record slices
        v_meta = video_metadata_map.get(tc.videoId, {})
        category = tc.category
        qtype = tc.questionType
        dur_tier = v_meta.get("durationTier", "unknown")

        category_mrr[category].append(rr)
        category_r5[category].append(hit_5)

        qtype_mrr[qtype].append(rr)
        qtype_r5[qtype].append(hit_5)

        duration_mrr[dur_tier].append(rr)
        duration_r5[dur_tier].append(hit_5)

    n = len(cases_with_evidence)

    def avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    category_breakdown = {
        cat: {"mrr": avg(category_mrr[cat]), "recall_at_5": avg(category_r5[cat])}
        for cat in category_mrr
    }

    qtype_breakdown = {
        qt: {"mrr": avg(qtype_mrr[qt]), "recall_at_5": avg(qtype_r5[qt])} for qt in qtype_mrr
    }

    duration_breakdown = {
        dt: {"mrr": avg(duration_mrr[dt]), "recall_at_5": avg(duration_r5[dt])}
        for dt in duration_mrr
    }

    return RetrievalMetrics(
        recall_at_1=round(r_at_1_hits / n, 4),
        recall_at_3=round(r_at_3_hits / n, 4),
        recall_at_5=round(r_at_5_hits / n, 4),
        recall_at_10=round(r_at_10_hits / n, 4),
        precision_at_5=round(precision_at_5_sum / n, 4),
        mrr=avg(reciprocal_ranks),
        mean_iou=avg(all_ious),
        category_breakdown=category_breakdown,
        question_type_breakdown=qtype_breakdown,
        duration_tier_breakdown=duration_breakdown,
    )
