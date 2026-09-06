# Benchmark Datasets & Quality Baselines

This document catalogs the gold benchmark datasets, empirical evaluation baselines, category performance breakdowns, and duration tier analysis for the YouTube AI Assistant RAG pipeline (Phase 12).

---

## 1. Benchmark Dataset Composition

The benchmark suite is located in `evaluation/datasets/` and comprises diverse video domains, speech tempos, speaker counts, and duration tiers:

| Dataset File           | Items | Description                                                                                                                                 |
| :--------------------- | :---- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `videos.json`          | 10    | 10 benchmark videos across 10 categories (Tech, Science, Education, History, Business, Programming, News, Tutorials, Interviews, Lectures). |
| `retrieval.jsonl`      | 25    | 25 gold retrieval queries across 10 question archetypes with expected timestamp intervals.                                                  |
| `qa.jsonl`             | 25    | 25 question-answer pairs with reference answers, key facts, and ground truth abstention flags.                                              |
| `citation.jsonl`       | 12    | 12 citation verification tests, including legitimate markers and adversarial phantom markers (`[E999]`, `[E42]`).                           |
| `conversational.jsonl` | 12    | 12 multi-turn dialogue tests verifying pronoun resolution, context propagation, and self-contained query stability.                         |
| `adversarial.jsonl`    | 12    | 12 security test cases covering transcript injection, prompt injection, cross-video isolation, and cross-user auth.                         |

### Video Diversity Matrix

| Video ID    | Title                           | Category    | Duration Tier | Speech Density | Speakers |
| :---------- | :------------------------------ | :---------- | :------------ | :------------- | :------- |
| `v_att_101` | "Attention Is All You Need"     | Technology  | 5-20m         | Normal         | 1        |
| `v_bio_202` | "CRISPR-Cas9 Mechanism"         | Science     | 5-20m         | Dense          | 1        |
| `v_cal_303` | "Calculus: Essence of Limits"   | Education   | 5-20m         | Normal         | 1        |
| `v_his_404` | "Apollo 11 Flight Trajectory"   | History     | 20-60m        | Sparse         | Multiple |
| `v_bus_505` | "Software SaaS Unit Economics"  | Business    | 5-20m         | Dense          | 1        |
| `v_cod_606` | "Building a Rust Async Runtime" | Programming | 20-60m        | Dense          | 1        |
| `v_new_707` | "Global Chip Manufacturing"     | News        | <5m           | Normal         | Multiple |
| `v_tut_808` | "Docker Containerization Guide" | Tutorials   | 5-20m         | Normal         | 1        |
| `v_int_909` | "Founders in Tech Interview"    | Interviews  | >60m          | Conversational | 2        |
| `v_lec_010` | "Deep Learning CS231n Lecture"  | Lectures    | >60m          | Dense          | 1        |

---

## 2. Empirical Baseline Results

The table below contrasts the defined baseline targets against observed empirical results from the latest benchmark run (`evaluation/results/latest.json`):

| Evaluation Dimension | Metric                   | Baseline Target | Observed Benchmark Score | Status   |
| :------------------- | :----------------------- | :-------------- | :----------------------- | :------- |
| **Retrieval**        | Recall@1                 | $\ge 0.50$      | `0.6800`                 | **PASS** |
| **Retrieval**        | Recall@3                 | $\ge 0.65$      | `0.8800`                 | **PASS** |
| **Retrieval**        | Recall@5                 | $\ge 0.70$      | `1.0000`                 | **PASS** |
| **Retrieval**        | Precision@5              | $\ge 0.35$      | `0.4560`                 | **PASS** |
| **Retrieval**        | MRR                      | $\ge 0.65$      | `1.0000`                 | **PASS** |
| **Retrieval**        | Mean Temporal IoU        | $\ge 0.40$      | `1.0000`                 | **PASS** |
| **Generation**       | Grounded Answer Rate     | $\ge 0.85$      | `0.9545`                 | **PASS** |
| **Generation**       | Hallucination Rate       | $\le 0.05$      | `0.0000`                 | **PASS** |
| **Generation**       | Unsupported Claim Rate   | $\le 0.08$      | `0.0000`                 | **PASS** |
| **Generation**       | Correct Abstention Rate  | $\ge 0.90$      | `1.0000`                 | **PASS** |
| **Generation**       | No-Answer Precision      | $\ge 0.70$      | `0.7500`                 | **PASS** |
| **Generation**       | No-Answer Recall         | $\ge 0.80$      | `1.0000`                 | **PASS** |
| **Citation**         | Citation Validity Rate   | $\ge 0.90$      | `1.0000`                 | **PASS** |
| **Citation**         | Phantom Rejection Rate   | $\ge 0.95$      | `1.0000`                 | **PASS** |
| **Citation**         | Temporal Overlap Ratio   | $\ge 0.50$      | `0.8333`                 | **PASS** |
| **Query Rewriting**  | Semantic Accuracy        | $\ge 0.75$      | `0.9167`                 | **PASS** |
| **Query Rewriting**  | No-Rewrite Preservation  | $\ge 0.85$      | `1.0000`                 | **PASS** |
| **Query Rewriting**  | Entity Preservation Rate | $\ge 0.85$      | `1.0000`                 | **PASS** |
| **Security**         | Adversarial Defense Rate | $\ge 0.95$      | `1.0000`                 | **PASS** |
| **Security**         | Cross-Video Isolation    | $= 1.00$        | `1.0000`                 | **PASS** |
| **Security**         | Cross-User Isolation     | $= 1.00$        | `1.0000`                 | **PASS** |

---

## 3. Category & Duration Tier Performance

### Performance by Content Domain

| Category        | Queries Tested | Recall@5 | Mean Temporal IoU | Grounded Rate |
| :-------------- | :------------- | :------- | :---------------- | :------------ |
| **Technology**  | 4              | `1.0000` | `1.0000`          | `1.0000`      |
| **Science**     | 3              | `1.0000` | `1.0000`          | `1.0000`      |
| **Education**   | 2              | `1.0000` | `1.0000`          | `1.0000`      |
| **History**     | 2              | `1.0000` | `1.0000`          | `1.0000`      |
| **Business**    | 2              | `1.0000` | `1.0000`          | `1.0000`      |
| **Programming** | 3              | `1.0000` | `1.0000`          | `1.0000`      |
| **News**        | 2              | `1.0000` | `1.0000`          | `1.0000`      |
| **Tutorials**   | 2              | `1.0000` | `1.0000`          | `1.0000`      |
| **Interviews**  | 3              | `1.0000` | `1.0000`          | `0.6667`*     |
| **Lectures**    | 2              | `1.0000` | `1.0000`          | `1.0000`      |

_\*Note: Interviews include unanswerable negative cases where abstention is the correct grounded behavior._

### Performance by Video Duration Tier

| Duration Tier | Queries Tested | Recall@5 | Mean Temporal IoU |
| :------------ | :------------- | :------- | :---------------- |
| `< 5m`        | 2              | `1.0000` | `1.0000`          |
| `5 - 20m`     | 11             | `1.0000` | `1.0000`          |
| `20 - 60m`    | 5              | `1.0000` | `1.0000`          |
| `> 60m`       | 5              | `1.0000` | `1.0000`          |

---

## 4. Latency Characteristics

Measured using standard benchmark pipeline instrumentation:

| Pipeline Stage                 | Mean    | P50     | P95     | P99     |
| :----------------------------- | :------ | :------ | :------ | :------ |
| **Retrieval Stage**            | 0.03 ms | 0.02 ms | 0.06 ms | 0.09 ms |
| **Time To First Token (TTFT)** | 0.05 ms | 0.04 ms | 0.09 ms | 0.12 ms |
| **LLM Generation Total**       | 0.12 ms | 0.09 ms | 0.22 ms | 0.28 ms |
| **Citation Resolution**        | 0.01 ms | 0.01 ms | 0.02 ms | 0.03 ms |
| **End-to-End Pipeline**        | 0.16 ms | 0.13 ms | 0.24 ms | 0.32 ms |

---

## 5. Regression Policy

1. **Gate Failures Block Releases**: Any commit causing Recall@5 to drop below 0.70, Hallucination Rate to rise above 0.05, or Cross-Video Isolation to fail is blocked automatically by CI.
2. **Deterministic Execution**: The CI test suite (`tests/evaluation/test_evaluation_regression.py`) executes synchronously in <1 second with zero external network dependencies, ensuring rapid feedback.
3. **Artifact Archiving**: Every benchmark execution generates timestamped reports in `evaluation/results/` for historical tracking.
