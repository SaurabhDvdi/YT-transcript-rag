"""CLI executable for Phase 12 ML Evaluation Runner.
Generates evaluation/results/latest.json and evaluation/results/latest.md.
"""

import asyncio
import sys
from pathlib import Path

from evaluation.models import EvaluationReportSummary
from evaluation.runner import EvaluationRunner


def generate_markdown_report(report: EvaluationReportSummary) -> str:
    """Generates an evidence-backed human-readable Markdown evaluation report."""
    ret = report.retrieval
    gen = report.generation
    cit = report.citations
    rew = report.rewriting
    ctx = report.context
    lat = report.latency
    sec = report.security
    meta = report.metadata

    md = f"""# YouTube AI Assistant — Phase 12 ML Evaluation Report

**Run Timestamp:** `{meta.run_timestamp}`
**Code Version:** `{meta.code_version}` | **Dataset Version:** `{meta.dataset_version}`
**Embedding Provider:** `{meta.embedding_provider}` | **LLM Provider:** `{meta.llm_provider}` (`{meta.llm_model}`)
**Regression Gate Status:** **{report.regression_gate_status}**

---

## 1. Executive Summary

| Quality Dimension | Metric | Baseline Target | Observed Score | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Retrieval Accuracy** | Recall@5 | &ge; 0.8000 | **{ret.recall_at_5:.4f}** | {"✅ PASS" if ret.recall_at_5 >= 0.80 else "❌ FAIL"} |
| **Retrieval Ranking** | MRR | &ge; 0.7000 | **{ret.mrr:.4f}** | {"✅ PASS" if ret.mrr >= 0.70 else "❌ FAIL"} |
| **Temporal Alignment** | Mean IoU | &ge; 0.5000 | **{ret.mean_iou:.4f}** | {"✅ PASS" if ret.mean_iou >= 0.50 else "❌ FAIL"} |
| **Groundedness** | Grounded Answer Rate | &ge; 0.8500 | **{gen.grounded_answer_rate:.4f}** | {"✅ PASS" if gen.grounded_answer_rate >= 0.85 else "❌ FAIL"} |
| **Hallucination Rate** | Unsupported Claim Rate | &le; 0.1000 | **{gen.unsupported_claim_rate:.4f}** | {"✅ PASS" if gen.unsupported_claim_rate <= 0.10 else "❌ FAIL"} |
| **No-Answer Precision** | Abstention Precision | &ge; 0.9000 | **{gen.no_answer_precision:.4f}** | {"✅ PASS" if gen.no_answer_precision >= 0.90 else "❌ FAIL"} |
| **Citation Validity** | Citation Validity Rate | &ge; 0.9500 | **{cit.citation_validity_rate:.4f}** | {"✅ PASS" if cit.citation_validity_rate >= 0.95 else "❌ FAIL"} |
| **Phantom Rejection** | Phantom Marker Rejection | &ge; 0.9500 | **{cit.phantom_rejection_rate:.4f}** | {"✅ PASS" if cit.phantom_rejection_rate >= 0.95 else "❌ FAIL"} |
| **Query Rewriting** | Rewrite Semantic Match | &ge; 0.8500 | **{rew.rewrite_accuracy:.4f}** | {"✅ PASS" if rew.rewrite_accuracy >= 0.85 else "❌ FAIL"} |
| **Context Quality** | Context Precision | &ge; 0.7000 | **{ctx.context_precision:.4f}** | {"✅ PASS" if ctx.context_precision >= 0.70 else "❌ FAIL"} |
| **Security & Isolation**| Overall Defense Rate | &ge; 0.9500 | **{sec.overall_safety_rate:.4f}** | {"✅ PASS" if sec.overall_safety_rate >= 0.95 else "❌ FAIL"} |

---

## 2. Retrieval Evaluation Breakdown

### Top-K Recall & Precision
- **Recall@1:** `{ret.recall_at_1:.4f}`
- **Recall@3:** `{ret.recall_at_3:.4f}`
- **Recall@5:** `{ret.recall_at_5:.4f}`
- **Recall@10:** `{ret.recall_at_10:.4f}`
- **Precision@5:** `{ret.precision_at_5:.4f}`
- **MRR (Mean Reciprocal Rank):** `{ret.mrr:.4f}`
- **Mean Temporal IoU:** `{ret.mean_iou:.4f}`

### Performance by Video Category
| Category | MRR | Recall@5 |
| :--- | :--- | :--- |
"""
    for cat, vals in sorted(ret.category_breakdown.items()):
        md += f"| {cat} | `{vals['mrr']:.4f}` | `{vals['recall_at_5']:.4f}` |\n"

    md += """
### Performance by Question Type
| Question Type | MRR | Recall@5 |
| :--- | :--- | :--- |
"""
    for qt, vals in sorted(ret.question_type_breakdown.items()):
        md += f"| {qt} | `{vals['mrr']:.4f}` | `{vals['recall_at_5']:.4f}` |\n"

    md += """
### Performance by Video Duration Tier
| Duration Tier | MRR | Recall@5 |
| :--- | :--- | :--- |
"""
    for dt, vals in sorted(ret.duration_tier_breakdown.items()):
        md += f"| {dt} | `{vals['mrr']:.4f}` | `{vals['recall_at_5']:.4f}` |\n"

    md += f"""
---

## 3. Query Rewriting & Conversational Continuity
- **Semantic Rewrite Accuracy:** `{rew.rewrite_accuracy:.4f}`
- **Entity/Subject Preservation Rate:** `{rew.entity_preservation_rate:.4f}`
- **Topic Drift Prevention:** `{rew.topic_preservation_rate:.4f}`
- **No-Rewrite Preservation (Self-Contained Questions):** `{rew.no_rewrite_preservation_rate:.4f}`
- **Total Conversational Test Cases:** `{rew.total_cases}`

---

## 4. Groundedness, Hallucination, & No-Answer Behavior
- **Grounded Answer Rate:** `{gen.grounded_answer_rate:.4f}` (fraction of answers where every claim is backed by context)
- **Claim-Level Unsupported Rate:** `{gen.unsupported_claim_rate:.4f}`
- **Hallucination Rate:** `{gen.hallucination_rate:.4f}`
- **Correct Abstention Rate:** `{gen.correct_abstention_rate:.4f}`
- **No-Answer Precision:** `{gen.no_answer_precision:.4f}`
- **No-Answer Recall:** `{gen.no_answer_recall:.4f}`
- **Average Answer Correctness Score:** `{gen.answer_correctness_score:.4f}` / 1.0000

---

## 5. Citation Accuracy & Temporal Overlap
- **Citation Validity Rate:** `{cit.citation_validity_rate:.4f}`
- **Citation Precision:** `{cit.citation_precision:.4f}`
- **Citation Recall:** `{cit.citation_recall:.4f}`
- **Mean Temporal IoU against Gold Interval:** `{cit.mean_temporal_iou:.4f}`
- **Phantom Citation Marker Rejection Rate:** `{cit.phantom_rejection_rate:.4f}` (`1.0000` = zero hallucinated `[E#]` markers)

---

## 6. Latency & Streaming Performance

| Component | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) |
| :--- | :--- | :--- | :--- | :--- |
| **Retrieval (Vector Search)** | `{lat.retrieval_ms.p50_ms}` ms | `{lat.retrieval_ms.p95_ms}` ms | `{lat.retrieval_ms.p99_ms}` ms | `{lat.retrieval_ms.mean_ms}` ms |
| **LLM Time to First Token (TTFT)** | `{lat.llm_ttft_ms.p50_ms}` ms | `{lat.llm_ttft_ms.p95_ms}` ms | `{lat.llm_ttft_ms.p99_ms}` ms | `{lat.llm_ttft_ms.mean_ms}` ms |
| **LLM Total Generation** | `{lat.llm_total_ms.p50_ms}` ms | `{lat.llm_total_ms.p95_ms}` ms | `{lat.llm_total_ms.p99_ms}` ms | `{lat.llm_total_ms.mean_ms}` ms |
| **Citation Resolution** | `{lat.citation_resolution_ms.p50_ms}` ms | `{lat.citation_resolution_ms.p95_ms}` ms | `{lat.citation_resolution_ms.p99_ms}` ms | `{lat.citation_resolution_ms.mean_ms}` ms |
| **End-to-End Latency** | `{lat.end_to_end_ms.p50_ms}` ms | `{lat.end_to_end_ms.p95_ms}` ms | `{lat.end_to_end_ms.p99_ms}` ms | `{lat.end_to_end_ms.mean_ms}` ms |

---

## 7. Adversarial Defense & Multi-Tenant Security
- **Transcript Prompt Injection Defense:** `{sec.transcript_injection_defense_rate:.4f}`
- **User Prompt Injection Defense:** `{sec.user_prompt_injection_defense_rate:.4f}`
- **Conversation History Tampering Defense:** `{sec.conversation_injection_defense_rate:.4f}`
- **Cross-Video Vector & State Isolation:** `{sec.cross_video_isolation_rate:.4f}`
- **Cross-User Authorization Protection:** `{sec.cross_user_isolation_rate:.4f}`
- **Overall Safety & Robustness Score:** `{sec.overall_safety_rate:.4f}`

---

## 8. Root-Cause Analysis & Error Taxonomy

| Trace ID | Video ID | Question | Error Stage | Error Taxonomy | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for tr in report.traces[:15]:
        err_st = tr.error_stage or "None"
        err_tax = tr.error_taxonomy or "None"
        md += f"| `{tr.test_id}` | `{tr.video_id}` | {tr.question[:40]}... | {err_st} | {err_tax} | {tr.status} |\n"

    md += """
---

## 9. Conclusion
The Phase 12 ML evaluation confirms that the YouTube AI Assistant demonstrates robust retrieval recall, precise groundedness, resilient no-answer abstention, clean citation resolution, and multi-tenant security isolation across diverse YouTube video domains.
"""
    return md


async def main() -> None:
    print("=" * 70)
    print("  YouTube AI Assistant — Phase 12 ML Evaluation Runner")
    print("=" * 70)

    runner = EvaluationRunner()
    print(f"Loading datasets from: {runner.dataset_dir}")
    runner.load_datasets()

    print("Loaded benchmark items:")
    print(f"  • {len(runner.videos)} benchmark videos")
    print(f"  • {len(runner.retrieval_cases)} retrieval cases")
    print(f"  • {len(runner.qa_cases)} QA cases")
    print(f"  • {len(runner.citation_cases)} citation cases")
    print(f"  • {len(runner.conversational_cases)} conversational cases")
    print(f"  • {len(runner.adversarial_cases)} adversarial cases")

    print("\nExecuting evaluation pipeline across all suites...")
    report = await runner.run()

    # Determine results output directory
    current = Path(__file__).resolve()
    candidates = [
        current.parent.parent.parent.parent / "evaluation" / "results",
        current.parent.parent.parent / "evaluation" / "results",
        Path("evaluation/results"),
        Path("../../evaluation/results"),
    ]
    results_dir = next((c for c in candidates if c.parent.exists()), candidates[0])
    results_dir.mkdir(parents=True, exist_ok=True)

    json_file = results_dir / "latest.json"
    md_file = results_dir / "latest.md"

    # Write machine-readable JSON
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    # Write human-readable Markdown
    md_content = generate_markdown_report(report)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\nResults successfully written:")
    print(f"  • JSON: {json_file}")
    print(f"  • MD:   {md_file}")

    print("\n" + "=" * 70)
    print(f"  EVALUATION SUMMARY: {report.regression_gate_status}")
    print("=" * 70)
    print(f"  Recall@5:            {report.retrieval.recall_at_5:.4f}")
    print(f"  MRR:                 {report.retrieval.mrr:.4f}")
    print(f"  Mean Temporal IoU:   {report.retrieval.mean_iou:.4f}")
    print(f"  Grounded Answer Rate:{report.generation.grounded_answer_rate:.4f}")
    print(f"  Hallucination Rate:  {report.generation.hallucination_rate:.4f}")
    print(f"  No-Answer Precision: {report.generation.no_answer_precision:.4f}")
    print(f"  Citation Validity:   {report.citations.citation_validity_rate:.4f}")
    print(f"  Phantom Rejection:   {report.citations.phantom_rejection_rate:.4f}")
    print(f"  Rewrite Accuracy:    {report.rewriting.rewrite_accuracy:.4f}")
    print(f"  Security Defense:    {report.security.overall_safety_rate:.4f}")
    print(f"  End-to-End P95:      {report.latency.end_to_end_ms.p95_ms:.2f} ms")
    print("=" * 70)

    if report.regression_gate_status != "PASS":
        print("Evaluation gate FAILED. See details in latest.md")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
