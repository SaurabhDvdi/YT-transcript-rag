"""Citation accuracy metrics: precision, recall, validity rate, temporal IoU, and phantom rejection."""

from evaluation.metrics.retrieval import compute_temporal_iou
from evaluation.models import CitationMetrics, CitationTestCase
from src.schemas.generation import Citation


def evaluate_citation_suite(
    test_cases: list[CitationTestCase],
    resolved_citations_map: dict[str, list[Citation]],
    cleaned_texts_map: dict[str, str],
) -> CitationMetrics:
    """Evaluates citation resolution precision, recall, validity, temporal IoU, and phantom rejection."""
    if not test_cases:
        return CitationMetrics(
            citation_precision=1.0,
            citation_recall=1.0,
            citation_validity_rate=1.0,
            mean_temporal_iou=1.0,
            phantom_rejection_rate=1.0,
        )

    valid_citations_count = 0
    total_citations_count = 0

    phantom_attempted_count = 0
    phantom_rejected_count = 0

    case_precisions: list[float] = []
    case_recalls: list[float] = []
    all_ious: list[float] = []

    for tc in test_cases:
        resolved = resolved_citations_map.get(tc.id, [])
        cleaned_text = cleaned_texts_map.get(tc.id, "")

        # Check phantom marker rejection
        for phantom in tc.expectedPhantomMarkers:
            phantom_attempted_count += 1
            if phantom not in cleaned_text:
                phantom_rejected_count += 1

        total_citations_count += len(resolved)

        if not tc.goldTimestampIntervals and not tc.expectedValidMarkers:
            # Case expects zero citations (e.g. no evidence)
            if len(resolved) == 0:
                case_precisions.append(1.0)
                case_recalls.append(1.0)
            else:
                case_precisions.append(0.0)
                case_recalls.append(1.0)
            continue

        if not resolved:
            case_precisions.append(0.0)
            case_recalls.append(0.0)
            continue

        # Measure validity and temporal IoU
        hits = 0
        gold_covered = set()

        for cit in resolved:
            # Check validity: start < end, positive
            if cit.start >= 0 and cit.end > cit.start:
                valid_citations_count += 1

            best_iou = 0.0
            best_gold_idx = -1
            for g_idx, gold in enumerate(tc.goldTimestampIntervals):
                iou = compute_temporal_iou(cit.start, cit.end, gold["start"], gold["end"])
                if iou > best_iou:
                    best_iou = iou
                    best_gold_idx = g_idx

            all_ious.append(best_iou)
            if best_iou >= 0.20:
                hits += 1
                if best_gold_idx >= 0:
                    gold_covered.add(best_gold_idx)

        prec = hits / len(resolved)
        rec = len(gold_covered) / max(1, len(tc.goldTimestampIntervals))
        case_precisions.append(prec)
        case_recalls.append(min(1.0, rec))

    val_rate = valid_citations_count / total_citations_count if total_citations_count > 0 else 1.0
    phantom_rate = (
        phantom_rejected_count / phantom_attempted_count if phantom_attempted_count > 0 else 1.0
    )

    def avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    return CitationMetrics(
        citation_precision=avg(case_precisions),
        citation_recall=avg(case_recalls),
        citation_validity_rate=round(val_rate, 4),
        mean_temporal_iou=avg(all_ious),
        phantom_rejection_rate=round(phantom_rate, 4),
    )
