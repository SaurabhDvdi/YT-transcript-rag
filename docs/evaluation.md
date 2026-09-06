# Machine Learning Evaluation Framework

This document outlines the evaluation methodology, metric definitions, error taxonomy, automated regression gates, and human review protocol for the YouTube AI Assistant RAG pipeline (Phase 12).

---

## 1. Evaluation Architecture

The evaluation framework objectively measures end-to-end question answering and retrieval performance across diverse YouTube video transcripts without relying on subjective impressions or hardcoded passes.

```text
Benchmark Datasets (evaluation/datasets/)
  ├── videos.json            (10 representative videos across duration & domain tiers)
  ├── retrieval.jsonl        (25 query-evidence retrieval pairs)
  ├── qa.jsonl               (25 question-answer ground truth pairs)
  ├── citation.jsonl         (12 citation validation & phantom marker test cases)
  ├── conversational.jsonl   (12 multi-turn follow-up queries)
  └── adversarial.jsonl      (12 security & boundary injection cases)
          ↓
Evaluation Engine (apps/backend/evaluation/)
  ├── Metrics: Retrieval, Rewriting, Context, Generation, Citation, Latency, Security
  ├── Taxonomy: 12-category Error Diagnoser & Root Cause Analyzer
  └── Runner: Deterministic CI harness producing latest.json and latest.md
          ↓
CI Regression Gate (apps/backend/tests/evaluation/test_evaluation_regression.py)
  └── 22 deterministic assertions guarding against quality degradation
```

---

## 2. Metric Definitions & Formulas

### 2.1 Retrieval Quality

- **Recall@K**: Proportion of test queries where at least one retrieved chunk temporally overlaps the gold evidence interval with $\text{IoU} \ge 0.1$:
  $$\text{Recall@K} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}\left(\exists i \le K: \text{IoU}(\text{chunk}_i, \text{evidence}_q) \ge 0.1\right)$$
- **Precision@K**: Proportion of retrieved chunks within the top $K$ that temporally overlap gold evidence.
- **Mean Reciprocal Rank (MRR)**: Evaluates the rank position of the first relevant chunk:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$
- **Temporal IoU**: Temporal Intersection over Union measuring how closely chunk boundaries match the gold timestamp interval $[t_{\text{start}}, t_{\text{end}}]$:
  $$\text{IoU}(A, B) = \frac{\max(0, \min(A_{\text{end}}, B_{\text{end}}) - \max(A_{\text{start}}, B_{\text{start}}))}{\max(A_{\text{end}}, B_{\text{end}}) - \min(A_{\text{start}}, B_{\text{start}})}$$

### 2.2 Conversational Query Rewriting

- **Semantic Rewrite Accuracy**: Accuracy of resolving pronouns, ellipsis, and context-dependent references while leaving self-contained questions uncorrupted.
- **Topic Drift Prevention Rate**: Fraction of rewritten queries that remain strictly bounded to the conversation topic.
- **Entity Preservation Rate**: Fraction of essential named entities preserved through rewriting.
- **No-Rewrite Preservation**: Fraction of standalone queries that are preserved without unnecessary tampering.

### 2.3 Context Quality

- **Context Precision**: Proportion of evidence chunks passed to the LLM prompt that are relevant to the query.
- **Context Recall**: Proportion of gold evidence intervals covered by the chunks included in the LLM prompt context budget.
- **Duplicate Chunk Rate**: Fraction of duplicate chunks retrieved and passed to generation.
- **Unique Evidence Coverage**: Proportion of distinct information segments represented in the prompt context.

### 2.4 Grounded Generation & Safety

- **Grounded Answer Rate**: Fraction of questions answered where all factual claims are supported by the provided transcript context.
- **Hallucination Rate**: Fraction of generated answers containing unsupported or fabricated factual assertions not found in the transcript:
  $$\text{Hallucination Rate} = \frac{\text{Answers with Unsupported Claims}}{\text{Total Answered Questions}}$$
- **No-Answer Precision & Recall**: Precision and recall of the model abstaining with the standardized notice (`"I couldn't find evidence in the transcript to answer this."`) when no supporting evidence exists.

### 2.5 Citation Accuracy

- **Citation Validity Rate**: Percentage of citations in generated answers that map to legitimate retrieved chunks with active timestamp anchors.
- **Phantom Marker Rejection Rate**: Rate at which hallucinated or non-existent citation markers (e.g., `[E999]`, `[E42]`) are sanitized and stripped before display to the user.
- **Temporal Overlap Ratio**: Average overlap between citation timestamp intervals and ground truth intervals.

### 2.6 Latency & Observability

- Latency percentiles (P50, P95, P99) measured for:
  1. Retrieval stage
  2. Time To First Token (TTFT)
  3. Total LLM generation time
  4. Citation resolution stage
  5. End-to-end turnaround time

---

## 3. Error Taxonomy

Failures are systematically classified into 12 mutually exclusive error categories across 5 pipeline stages:

| Stage          | Error Category        | Description                                                       | Root Cause / Mitigation                |
| :------------- | :-------------------- | :---------------------------------------------------------------- | :------------------------------------- |
| **Data**       | `TRANSCRIPT_ERROR`    | Empty, garbled, or misaligned transcript.                         | Normalizer & Whisper alignment         |
| **Retrieval**  | `RETRIEVAL_MISS`      | Top-K retrieved chunks do not contain gold evidence.              | Embedding fine-tuning, BM25 hybrid     |
| **Retrieval**  | `RETRIEVAL_NOISY`     | Retrieved chunks contain excessive irrelevant noise.              | Threshold filtering, reranking         |
| **Query**      | `REWRITE_CORRUPT`     | Rewriter altered the semantic meaning or injected topic drift.    | Rewriter prompt calibration            |
| **Query**      | `REWRITE_OVERKILL`    | Self-contained query was unnecessarily modified.                  | Standalone classifier tuning           |
| **Context**    | `CONTEXT_OVERFLOW`    | Context builder dropped relevant chunks due to token budget.      | Compact summarization, budget scaling  |
| **Generation** | `HALLUCINATION`       | LLM asserted claims contradicted or unsupported by transcript.    | Strict grounding system prompt         |
| **Generation** | `PREMATURE_ABSTAIN`   | Model claimed no evidence when evidence was present in context.   | Prompt grounding calibration           |
| **Generation** | `UNWARRANTED_ANSWER`  | Model answered a question despite zero evidence in transcript.    | Negative few-shot examples             |
| **Citation**   | `CITATION_INVALID`    | Citation marker points to non-existent chunk ID.                  | Resolver sanitization                  |
| **Citation**   | `CITATION_MISALIGNED` | Citation interval does not match the claim.                       | Segment-level mapping                  |
| **Security**   | `ADVERSARIAL_LEAK`    | Transcript or conversation injection hijacked model instructions. | XML boundaries, system untrusted rules |

---

## 4. Automated CI Regression Gates

The regression suite runs on every pull request and release build via `pytest tests/evaluation/test_evaluation_regression.py`. A build fails immediately if any threshold is violated:

| Metric                                    | Minimum Passing Threshold |
| :---------------------------------------- | :------------------------ |
| `retrieval.recall_at_5`                   | $\ge 0.70$                |
| `retrieval.mrr`                           | $\ge 0.65$                |
| `retrieval.mean_temporal_iou`             | $\ge 0.40$                |
| `generation.grounded_answer_rate`         | $\ge 0.85$                |
| `generation.hallucination_rate`           | $\le 0.05$                |
| `generation.claim_level_unsupported_rate` | $\le 0.08$                |
| `citation.validity_rate`                  | $\ge 0.90$                |
| `citation.phantom_marker_rejection_rate`  | $\ge 0.95$                |
| `rewriting.semantic_accuracy`             | $\ge 0.75$                |
| `security.overall_defense_rate`           | $\ge 0.95$                |
| `security.cross_video_isolation_rate`     | $= 1.00$                  |
| `security.cross_user_isolation_rate`      | $= 1.00$                  |

---

## 5. Human Review Protocol

For production releases, an expert review pass evaluates 50 sampled interactions using a standardized rubric:

1. **Groundedness Score (1–5)**:
   - 5: Every single claim directly supported with clear timestamp evidence.
   - 3: Minor peripheral statements lack explicit transcript quotes.
   - 1: Central thesis contains unsupported assumptions or external memory.
2. **Citation Accuracy (Yes/No)**:
   - Verify clicking each citation chip opens and jumps to the exact second where the speaker explains the concept.
3. **Appropriate Abstention (Yes/No)**:
   - Verify that out-of-scope or unmentioned topics correctly trigger the standard `"I couldn't find evidence..."` notice.
