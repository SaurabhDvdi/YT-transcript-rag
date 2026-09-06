# YouTube AI Assistant — Evaluation Benchmark Datasets (Phase 12)

This directory contains version-controlled evaluation benchmarks designed to measure retrieval quality, groundedness, hallucination rate, citation accuracy, conversational continuity, and adversarial resilience across real YouTube videos.

## Dataset Structure

```text
evaluation/
├── datasets/
│   ├── videos.json           # Metadata and inclusion rationale for benchmark videos
│   ├── retrieval.jsonl       # Retrieval test cases with gold timestamp intervals & chunks
│   ├── qa.jsonl              # Q&A cases with reference answers, rubrics, and key facts
│   ├── citation.jsonl        # Citation verification cases with temporal IoU bounds
│   ├── conversational.jsonl  # Multi-turn conversational follow-ups and no-rewrite cases
│   └── adversarial.jsonl     # Prompt injections, cross-video, and cross-user security attacks
├── results/
│   ├── latest.json           # Machine-readable evaluation report
│   └── latest.md             # Human-readable engineering evaluation report
└── README.md                 # Dataset documentation and schema specifications
```

---

## Benchmark Design & Category Matrix

Videos are sampled across diverse domains to prevent domain-specific overfitting:

| Video ID      | Category           | Duration | Speech Density          | Speaker Count | Rationale                                                |
| :------------ | :----------------- | :------- | :---------------------- | :------------ | :------------------------------------------------------- |
| `Gfr50f6ZBvo` | Technology         | 15m 20s  | Dense technical         | 1             | Transformer deep dive with mathematical formulas         |
| `dQw4w9WgXcQ` | Science            | 10m 12s  | Conceptual              | 1             | Quantum superposition, entanglement, decoherence         |
| `abc123math`  | Education          | 4m 00s   | Dense mathematical      | 1             | Calculus limits & epsilon-delta definitions (<5m)        |
| `hist987rome` | History            | 45m 50s  | Chronological narrative | 1             | Multi-hop causal reasoning across distant timestamps     |
| `biz456saas`  | Business           | 14m 00s  | Analytical numerical    | 1             | SaaS unit economics (LTV/CAC, NRR)                       |
| `py789async`  | Programming        | 22m 30s  | Code & syntax           | 1             | Python asyncio, event loops, OS selectors                |
| `news321chip` | News/commentary    | 12m 00s  | Journalistic dialogue   | 2             | Semiconductor trade regulations & quotes                 |
| `tut654git`   | Tutorials          | 3m 00s   | Procedural              | 1             | Git rebase vs merge commit graphs (<5m)                  |
| `int555ai`    | Interviews         | 35m 00s  | Conversational dialogue | 2             | AI safety, scalable oversight, multi-speaker attribution |
| `lec999mit`   | Long-form lectures | 68m 40s  | Academic lecture        | 1             | Linear algebra vector spaces & null space (>60m)         |

---

## Question Taxonomy

All benchmark queries are tagged with a question type:

1. `fact lookup`: Specific names, numbers, or facts directly stated in the transcript.
2. `definition`: Formal definitions or conceptual explanations of terms.
3. `why/explanation`: Cause-and-effect reasoning based on video content.
4. `comparison`: Contrasting two or more concepts mentioned in the video.
5. `multi-hop`: Synthesizing evidence across multiple distinct transcript segments.
6. `temporal`: Timestamp or chronological sequencing questions.
7. `speaker-related`: Speaker viewpoint attribution in multi-speaker videos.
8. `follow-up`: Conversational follow-ups requiring pronoun resolution.
9. `negative/no-evidence`: Out-of-scope or absent queries requiring clean abstention ("I couldn't find enough information in this video.").
10. `ambiguous`: Vague prompts testing system clarification or fallback handling.

---

## Execution Instructions

Run the automated evaluation runner:

```bash
cd apps/backend
uv run python -m evaluation.run
```

Run the deterministic CI regression suite:

```bash
cd apps/backend
uv run pytest tests/evaluation/ -v
```
