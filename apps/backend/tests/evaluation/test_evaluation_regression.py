import asyncio

import pytest

from evaluation.models import EvaluationReportSummary
from evaluation.runner import EvaluationRunner

_CACHED_RUNNER: EvaluationRunner | None = None
_CACHED_REPORT: EvaluationReportSummary | None = None


def get_cached_runner() -> EvaluationRunner:
    global _CACHED_RUNNER
    if _CACHED_RUNNER is None:
        _CACHED_RUNNER = EvaluationRunner()
        _CACHED_RUNNER.load_datasets()
    return _CACHED_RUNNER


def get_cached_report() -> EvaluationReportSummary:
    global _CACHED_REPORT
    if _CACHED_REPORT is None:
        runner = get_cached_runner()
        _CACHED_REPORT = asyncio.run(runner.run())
    return _CACHED_REPORT


@pytest.fixture
def runner() -> EvaluationRunner:
    return get_cached_runner()


@pytest.fixture
def report() -> EvaluationReportSummary:
    return get_cached_report()


# ---------------------------------------------------------------------------
# 1. Retrieval Regression Gate (>= 20 cases)
# ---------------------------------------------------------------------------


def test_retrieval_cases_count_meets_minimum(runner: EvaluationRunner):
    assert len(runner.retrieval_cases) >= 20, (
        "Golden regression suite requires at least 20 retrieval cases"
    )


def test_retrieval_recall_at_5_regression(report: EvaluationReportSummary):
    assert report.retrieval.recall_at_5 >= 0.85, (
        f"Retrieval Recall@5 regressed below 0.85: got {report.retrieval.recall_at_5:.4f}"
    )


def test_retrieval_mrr_regression(report: EvaluationReportSummary):
    assert report.retrieval.mrr >= 0.75, (
        f"Retrieval MRR regressed below 0.75: got {report.retrieval.mrr:.4f}"
    )


def test_retrieval_temporal_iou_regression(report: EvaluationReportSummary):
    assert report.retrieval.mean_iou >= 0.50, (
        f"Retrieval Temporal IoU regressed below 0.50: got {report.retrieval.mean_iou:.4f}"
    )


# ---------------------------------------------------------------------------
# 2. QA & Groundedness Regression Gate (>= 20 cases)
# ---------------------------------------------------------------------------


def test_qa_cases_count_meets_minimum(runner: EvaluationRunner):
    assert len(runner.qa_cases) >= 20, "Golden regression suite requires at least 20 QA cases"


def test_grounded_answer_rate_regression(report: EvaluationReportSummary):
    assert report.generation.grounded_answer_rate >= 0.85, (
        f"Grounded answer rate regressed below 0.85: got {report.generation.grounded_answer_rate:.4f}"
    )


def test_hallucination_rate_regression(report: EvaluationReportSummary):
    assert report.generation.hallucination_rate <= 0.10, (
        f"Hallucination rate exceeded 0.10 threshold: got {report.generation.hallucination_rate:.4f}"
    )


def test_unsupported_claim_rate_regression(report: EvaluationReportSummary):
    assert report.generation.unsupported_claim_rate <= 0.10, (
        f"Unsupported claim rate exceeded 0.10 threshold: got {report.generation.unsupported_claim_rate:.4f}"
    )


# ---------------------------------------------------------------------------
# 3. No-Answer & Abstention Behavior Regression (>= 10 cases)
# ---------------------------------------------------------------------------


def test_no_answer_behavior(report: EvaluationReportSummary):
    assert report.generation.correct_abstention_rate >= 0.80, (
        f"Correct abstention rate regressed: got {report.generation.correct_abstention_rate:.4f}"
    )
    assert report.generation.no_answer_recall >= 0.80, (
        f"No-answer recall regressed: got {report.generation.no_answer_recall:.4f}"
    )


# ---------------------------------------------------------------------------
# 4. Citation Accuracy & Phantom Rejection (>= 10 cases)
# ---------------------------------------------------------------------------


def test_citation_cases_count_meets_minimum(runner: EvaluationRunner):
    assert len(runner.citation_cases) >= 10, (
        "Golden regression suite requires at least 10 citation cases"
    )


def test_citation_validity_rate_regression(report: EvaluationReportSummary):
    assert report.citations.citation_validity_rate >= 0.95, (
        f"Citation validity rate regressed below 0.95: got {report.citations.citation_validity_rate:.4f}"
    )


def test_phantom_citation_rejection_regression(report: EvaluationReportSummary):
    assert report.citations.phantom_rejection_rate >= 0.95, (
        f"Phantom citation rejection rate regressed below 0.95: got {report.citations.phantom_rejection_rate:.4f}"
    )


def test_citation_temporal_overlap_regression(report: EvaluationReportSummary):
    assert report.citations.mean_temporal_iou >= 0.50, (
        f"Citation temporal IoU regressed below 0.50: got {report.citations.mean_temporal_iou:.4f}"
    )


# ---------------------------------------------------------------------------
# 5. Conversational & Query Rewriting Regression (>= 10 cases)
# ---------------------------------------------------------------------------


def test_conversational_cases_count_meets_minimum(runner: EvaluationRunner):
    assert len(runner.conversational_cases) >= 10, (
        "Golden regression suite requires at least 10 conversational cases"
    )


def test_rewriting_semantic_accuracy_regression(report: EvaluationReportSummary):
    assert report.rewriting.rewrite_accuracy >= 0.85, (
        f"Query rewriting accuracy regressed below 0.85: got {report.rewriting.rewrite_accuracy:.4f}"
    )


def test_no_rewrite_preservation_regression(report: EvaluationReportSummary):
    assert report.rewriting.no_rewrite_preservation_rate >= 0.90, (
        f"Self-contained no-rewrite preservation regressed: got {report.rewriting.no_rewrite_preservation_rate:.4f}"
    )


def test_entity_preservation_regression(report: EvaluationReportSummary):
    assert report.rewriting.entity_preservation_rate >= 0.90, (
        f"Entity/subject preservation regressed: got {report.rewriting.entity_preservation_rate:.4f}"
    )


# ---------------------------------------------------------------------------
# 6. Security & Adversarial Resilience Regression (>= 10 cases)
# ---------------------------------------------------------------------------


def test_adversarial_cases_count_meets_minimum(runner: EvaluationRunner):
    assert len(runner.adversarial_cases) >= 10, (
        "Golden regression suite requires at least 10 adversarial cases"
    )


def test_overall_security_defense_regression(report: EvaluationReportSummary):
    assert report.security.overall_safety_rate >= 0.95, (
        f"Overall security defense regressed below 0.95: got {report.security.overall_safety_rate:.4f}"
    )


def test_cross_video_isolation_regression(report: EvaluationReportSummary):
    assert report.security.cross_video_isolation_rate >= 0.95, (
        f"Cross-video isolation regressed: got {report.security.cross_video_isolation_rate:.4f}"
    )


def test_cross_user_isolation_regression(report: EvaluationReportSummary):
    assert report.security.cross_user_isolation_rate >= 0.95, (
        f"Cross-user isolation regressed: got {report.security.cross_user_isolation_rate:.4f}"
    )


# ---------------------------------------------------------------------------
# 7. Release Gate Composite Status
# ---------------------------------------------------------------------------


def test_evaluation_regression_gate_passes(report: EvaluationReportSummary):
    assert report.regression_gate_status == "PASS", (
        "Overall evaluation regression gate FAILED. Inspect evaluation/results/latest.md for failing stages."
    )
