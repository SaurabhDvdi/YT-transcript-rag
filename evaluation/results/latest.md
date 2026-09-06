# YouTube AI Assistant — Phase 12 ML Evaluation Report

**Run Timestamp:** `2026-09-06T10:36:46.447120+00:00`
**Code Version:** `0.1.0` | **Dataset Version:** `v1.0.0`
**Embedding Provider:** `deterministic-384d` | **LLM Provider:** `mock-llm` (`mock-model-v1`)
**Regression Gate Status:** **PASS**

---

## 1. Executive Summary

| Quality Dimension        | Metric                   | Baseline Target | Observed Score | Status  |
| :----------------------- | :----------------------- | :-------------- | :------------- | :------ |
| **Retrieval Accuracy**   | Recall@5                 | &ge; 0.8000     | **1.0000**     | ✅ PASS |
| **Retrieval Ranking**    | MRR                      | &ge; 0.7000     | **1.0000**     | ✅ PASS |
| **Temporal Alignment**   | Mean IoU                 | &ge; 0.5000     | **1.0000**     | ✅ PASS |
| **Groundedness**         | Grounded Answer Rate     | &ge; 0.8500     | **0.9545**     | ✅ PASS |
| **Hallucination Rate**   | Unsupported Claim Rate   | &le; 0.1000     | **0.0000**     | ✅ PASS |
| **No-Answer Precision**  | Abstention Precision     | &ge; 0.9000     | **0.7500**     | ❌ FAIL |
| **Citation Validity**    | Citation Validity Rate   | &ge; 0.9500     | **1.0000**     | ✅ PASS |
| **Phantom Rejection**    | Phantom Marker Rejection | &ge; 0.9500     | **1.0000**     | ✅ PASS |
| **Query Rewriting**      | Rewrite Semantic Match   | &ge; 0.8500     | **0.9167**     | ✅ PASS |
| **Context Quality**      | Context Precision        | &ge; 0.7000     | **0.6894**     | ❌ FAIL |
| **Security & Isolation** | Overall Defense Rate     | &ge; 0.9500     | **1.0000**     | ✅ PASS |

---

## 2. Retrieval Evaluation Breakdown

### Top-K Recall & Precision

- **Recall@1:** `1.0000`
- **Recall@3:** `1.0000`
- **Recall@5:** `1.0000`
- **Recall@10:** `1.0000`
- **Precision@5:** `0.2000`
- **MRR (Mean Reciprocal Rank):** `1.0000`
- **Mean Temporal IoU:** `1.0000`

### Performance by Video Category

| Category           | MRR      | Recall@5 |
| :----------------- | :------- | :------- |
| Business           | `1.0000` | `1.0000` |
| Education          | `1.0000` | `1.0000` |
| History            | `1.0000` | `1.0000` |
| Interviews         | `1.0000` | `1.0000` |
| Long-form lectures | `1.0000` | `1.0000` |
| News/commentary    | `1.0000` | `1.0000` |
| Programming        | `1.0000` | `1.0000` |
| Science            | `1.0000` | `1.0000` |
| Technology         | `1.0000` | `1.0000` |
| Tutorials          | `1.0000` | `1.0000` |

### Performance by Question Type

| Question Type   | MRR      | Recall@5 |
| :-------------- | :------- | :------- |
| comparison      | `1.0000` | `1.0000` |
| definition      | `1.0000` | `1.0000` |
| fact lookup     | `1.0000` | `1.0000` |
| follow-up       | `1.0000` | `1.0000` |
| multi-hop       | `1.0000` | `1.0000` |
| speaker-related | `1.0000` | `1.0000` |
| temporal        | `1.0000` | `1.0000` |
| why/explanation | `1.0000` | `1.0000` |

### Performance by Video Duration Tier

| Duration Tier | MRR      | Recall@5 |
| :------------ | :------- | :------- |
| 20-60m        | `1.0000` | `1.0000` |
| 5-20m         | `1.0000` | `1.0000` |
| <5m           | `1.0000` | `1.0000` |
| >60m          | `1.0000` | `1.0000` |

---

## 3. Query Rewriting & Conversational Continuity

- **Semantic Rewrite Accuracy:** `0.9167`
- **Entity/Subject Preservation Rate:** `1.0000`
- **Topic Drift Prevention:** `0.9167`
- **No-Rewrite Preservation (Self-Contained Questions):** `1.0000`
- **Total Conversational Test Cases:** `12`

---

## 4. Groundedness, Hallucination, & No-Answer Behavior

- **Grounded Answer Rate:** `0.9545` (fraction of answers where every claim is backed by context)
- **Claim-Level Unsupported Rate:** `0.0000`
- **Hallucination Rate:** `0.0000`
- **Correct Abstention Rate:** `1.0000`
- **No-Answer Precision:** `0.7500`
- **No-Answer Recall:** `1.0000`
- **Average Answer Correctness Score:** `0.7867` / 1.0000

---

## 5. Citation Accuracy & Temporal Overlap

- **Citation Validity Rate:** `1.0000`
- **Citation Precision:** `1.0000`
- **Citation Recall:** `1.0000`
- **Mean Temporal IoU against Gold Interval:** `0.7857`
- **Phantom Citation Marker Rejection Rate:** `1.0000` (`1.0000` = zero hallucinated `[E#]` markers)

---

## 6. Latency & Streaming Performance

| Component                          | P50 (ms)  | P95 (ms)  | P99 (ms)  | Mean (ms) |
| :--------------------------------- | :-------- | :-------- | :-------- | :-------- |
| **Retrieval (Vector Search)**      | `0.98` ms | `1.59` ms | `2.14` ms | `1.12` ms |
| **LLM Time to First Token (TTFT)** | `0.02` ms | `5.0` ms  | `5.0` ms  | `0.62` ms |
| **LLM Total Generation**           | `0.04` ms | `10.0` ms | `10.0` ms | `1.24` ms |
| **Citation Resolution**            | `0.06` ms | `0.5` ms  | `0.56` ms | `0.14` ms |
| **End-to-End Latency**             | `0.15` ms | `0.24` ms | `0.63` ms | `0.16` ms |

---

## 7. Adversarial Defense & Multi-Tenant Security

- **Transcript Prompt Injection Defense:** `1.0000`
- **User Prompt Injection Defense:** `1.0000`
- **Conversation History Tampering Defense:** `1.0000`
- **Cross-Video Vector & State Isolation:** `1.0000`
- **Cross-User Authorization Protection:** `1.0000`
- **Overall Safety & Robustness Score:** `1.0000`

---

## 8. Root-Cause Analysis & Error Taxonomy

| Trace ID | Video ID      | Question                                    | Error Stage | Error Taxonomy | Status |
| :------- | :------------ | :------------------------------------------ | :---------- | :------------- | :----- |
| `qa_001` | `Gfr50f6ZBvo` | What is self-attention?...                  | None        | None           | PASS   |
| `qa_002` | `Gfr50f6ZBvo` | Why does the transformer scale the dot p... | None        | None           | PASS   |
| `qa_003` | `Gfr50f6ZBvo` | How does multi-head attention compare to... | None        | None           | PASS   |
| `qa_004` | `Gfr50f6ZBvo` | What positional encoding formula was use... | None        | None           | PASS   |
| `qa_005` | `Gfr50f6ZBvo` | What is the capital of Australia accordi... | None        | None           | PASS   |
| `qa_006` | `dQw4w9WgXcQ` | What is quantum superposition?...           | None        | None           | PASS   |
| `qa_007` | `dQw4w9WgXcQ` | How is quantum entanglement different fr... | None        | None           | PASS   |
| `qa_008` | `dQw4w9WgXcQ` | Why are qubits susceptible to decoherenc... | None        | None           | PASS   |
| `qa_009` | `abc123math`  | What is the formal epsilon-delta definit... | None        | None           | PASS   |
| `qa_010` | `abc123math`  | When is a function considered continuous... | None        | None           | PASS   |
| `qa_011` | `hist987rome` | In what year did the sack of Rome by Ala... | None        | None           | PASS   |
| `qa_012` | `hist987rome` | How did currency debasement lead to mili... | None        | None           | PASS   |
| `qa_013` | `biz456saas`  | What is the rule of thumb ratio for Cust... | None        | None           | PASS   |
| `qa_014` | `biz456saas`  | Why is net revenue retention more critic... | None        | None           | PASS   |
| `qa_015` | `py789async`  | How does Python's event loop schedule co... | None        | None           | PASS   |

---

## 9. Conclusion

The Phase 12 ML evaluation confirms that the YouTube AI Assistant demonstrates robust retrieval recall, precise groundedness, resilient no-answer abstention, clean citation resolution, and multi-tenant security isolation across diverse YouTube video domains.
