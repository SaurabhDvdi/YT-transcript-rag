"""Query rewriting quality metrics: semantic preservation, entity tracking, and no-rewrite cases."""

import re

from evaluation.models import ConversationalTestCase, RewritingMetrics


def clean_words(text: str) -> set[str]:
    """Tokenize lowercase alphanumeric words."""
    return set(re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower()))


def evaluate_rewriting_suite(
    test_cases: list[ConversationalTestCase],
    actual_rewrites: dict[str, str],
) -> RewritingMetrics:
    """Evaluates conversational follow-up query rewriting and self-contained queries."""
    if not test_cases:
        return RewritingMetrics(
            rewrite_accuracy=1.0,
            entity_preservation_rate=1.0,
            topic_preservation_rate=1.0,
            no_rewrite_preservation_rate=1.0,
            total_cases=0,
        )

    entity_hits = 0
    topic_hits = 0
    no_rewrite_correct = 0
    no_rewrite_total = 0
    semantic_matches = 0

    for tc in test_cases:
        actual = actual_rewrites.get(tc.id, tc.currentQuestion).strip()
        expected = tc.expectedRewrittenQuery.strip()

        # Check self-contained queries (should remain unaltered)
        if tc.isSelfContained:
            no_rewrite_total += 1
            if actual.lower() == tc.currentQuestion.strip().lower():
                no_rewrite_correct += 1
                semantic_matches += 1
                entity_hits += 1
                topic_hits += 1
            continue

        # Check entity/subject preservation
        subject_tokens = clean_words(tc.expectedSubject)
        actual_tokens = clean_words(actual)

        has_entity = (
            subject_tokens.issubset(actual_tokens) or tc.expectedSubject.lower() in actual.lower()
        )
        if has_entity:
            entity_hits += 1

        # Check topic preservation (overlap between actual and expected tokens)
        expected_tokens = clean_words(expected)
        overlap = len(actual_tokens.intersection(expected_tokens))
        jaccard = overlap / max(1, len(actual_tokens.union(expected_tokens)))
        if jaccard >= 0.5:
            topic_hits += 1

        # Semantic match (exact or high Jaccard >= 0.7)
        if actual.lower() == expected.lower() or jaccard >= 0.7:
            semantic_matches += 1

    total = len(test_cases)
    no_rew_rate = round(no_rewrite_correct / no_rewrite_total, 4) if no_rewrite_total > 0 else 1.0

    return RewritingMetrics(
        rewrite_accuracy=round(semantic_matches / total, 4),
        entity_preservation_rate=round(entity_hits / total, 4),
        topic_preservation_rate=round(topic_hits / total, 4),
        no_rewrite_preservation_rate=no_rew_rate,
        total_cases=total,
    )
