"""Generation quality metrics: groundedness, hallucination, no-answer accuracy, and correctness."""

import re
from collections import defaultdict

from evaluation.models import GenerationMetrics, QATestCase
from src.core.constants import NO_EVIDENCE_ANSWER_TEXT


def extract_claims(text: str) -> list[str]:
    """Splits answer text into discrete sentences or clauses to evaluate claim attribution."""
    sentences = re.split(r"[.!?]\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def is_claim_supported_by_context(claim: str, context_text: str) -> bool:
    """Verifies whether key non-stopword tokens of a claim appear in the context."""
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "it",
        "this",
        "that",
    }
    claim_words = [
        w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", claim) if w.lower() not in stop_words
    ]
    if not claim_words:
        return True

    context_lower = context_text.lower()
    matches = sum(1 for w in claim_words if w in context_lower)
    return (matches / len(claim_words)) >= 0.5


def evaluate_generation_suite(
    qa_cases: list[QATestCase],
    actual_answers: dict[str, str],
    contexts: dict[str, str],
) -> GenerationMetrics:
    """Evaluates groundedness rate, hallucination rate, correct abstention, and rubric correctness."""
    if not qa_cases:
        return GenerationMetrics(
            grounded_answer_rate=1.0,
            unsupported_claim_rate=0.0,
            hallucination_rate=0.0,
            correct_abstention_rate=1.0,
            no_answer_precision=1.0,
            no_answer_recall=1.0,
            answer_correctness_score=1.0,
        )

    canonical_no_evidence = NO_EVIDENCE_ANSWER_TEXT.lower()

    grounded_answers_count = 0
    total_claims = 0
    unsupported_claims_count = 0
    hallucination_cases_count = 0

    true_no_evidence_count = 0
    model_abstained_count = 0
    correct_abstained_count = 0

    correctness_scores: list[float] = []
    category_scores: dict[str, list[float]] = defaultdict(list)

    for case in qa_cases:
        actual = actual_answers.get(case.id, "").strip()
        context = contexts.get(case.id, "")
        is_abstention = canonical_no_evidence in actual.lower() or len(actual) == 0

        if is_abstention:
            model_abstained_count += 1

        if case.isNoEvidence:
            true_no_evidence_count += 1
            if is_abstention:
                correct_abstained_count += 1
                correctness_scores.append(1.0)
                category_scores[case.questionType].append(1.0)
            else:
                # Answered when it should have abstained -> hallucination
                hallucination_cases_count += 1
                correctness_scores.append(0.0)
                category_scores[case.questionType].append(0.0)
            continue

        # Answerable case
        if is_abstention:
            # Failed to answer despite evidence available
            correctness_scores.append(0.0)
            category_scores[case.questionType].append(0.0)
            continue

        claims = extract_claims(actual)
        case_unsupported = 0

        for claim in claims:
            total_claims += 1
            if not is_claim_supported_by_context(claim, context):
                case_unsupported += 1
                unsupported_claims_count += 1

        if case_unsupported == 0 and len(claims) > 0:
            grounded_answers_count += 1
        elif case_unsupported > 0:
            hallucination_cases_count += 1

        # Check key fact coverage
        actual_lower = actual.lower()
        facts_covered = 0
        for fact in case.keyFacts:
            fact_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", fact) if len(w) > 3]
            if fact_words:
                matches = sum(1 for w in fact_words if w in actual_lower)
                if (matches / len(fact_words)) >= 0.5:
                    facts_covered += 1
            else:
                facts_covered += 1

        score = facts_covered / max(1, len(case.keyFacts))
        correctness_scores.append(score)
        category_scores[case.questionType].append(score)

    total_answerable = len(qa_cases) - true_no_evidence_count
    grounded_rate = grounded_answers_count / max(1, total_answerable)
    unsupported_rate = unsupported_claims_count / max(1, total_claims)
    hallucination_rate = hallucination_cases_count / len(qa_cases)

    no_ans_prec = (
        correct_abstained_count / model_abstained_count if model_abstained_count > 0 else 1.0
    )
    no_ans_rec = (
        correct_abstained_count / true_no_evidence_count if true_no_evidence_count > 0 else 1.0
    )
    abstention_rate = no_ans_rec

    cat_breakdown = {
        qt: {"correctness": round(sum(scores) / len(scores), 4)}
        for qt, scores in category_scores.items()
        if scores
    }

    return GenerationMetrics(
        grounded_answer_rate=round(grounded_rate, 4),
        unsupported_claim_rate=round(unsupported_rate, 4),
        hallucination_rate=round(hallucination_rate, 4),
        correct_abstention_rate=round(abstention_rate, 4),
        no_answer_precision=round(no_ans_prec, 4),
        no_answer_recall=round(no_ans_rec, 4),
        answer_correctness_score=round(sum(correctness_scores) / len(correctness_scores), 4),
        category_breakdown=cat_breakdown,
    )
