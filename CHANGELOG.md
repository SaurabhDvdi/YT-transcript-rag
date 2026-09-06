# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-09-06

### Added

- **Core Architecture (Phases 1–3)**:
  - Python 3.13 FastAPI backend running on Cloudflare Workers (Pyodide WebAssembly runtime).
  - WXT-based browser extension supporting Chromium (Chrome, Brave, Edge, Opera, Vivaldi) and Firefox.
  - Multi-strategy YouTube transcript extraction (InnerTube API, watch-page scraping, normalized segments).
  - Sliding-window semantic chunking preserving precise millisecond timestamp intervals.

- **Storage & Persistence (Phases 4–8)**:
  - Cloudflare D1 SQL persistent vector store with 384-dimensional dense vector embeddings.
  - Sequential D1 migrations (`0001` to `0006`) covering conversations, messages, jobs, usage events, and user accounts.
  - Multi-tier caching with Cloudflare KV and single-flight stampede protection.
  - Sliding-window distributed rate limiting and concurrent stream tracking.
  - Durable background video processing jobs with bounded retry and stale job recovery.

- **Security & Reliability (Phases 9–10)**:
  - Constant-time HMAC-SHA256 password hashing with PBKDF2 and cryptographically secure salt generation.
  - Refresh token rotation with family revocation on token replay detection.
  - Role-based authorization matrix ensuring cross-user and cross-video data isolation.
  - CircuitBreaker failover protecting LLM inference routes against external upstream failures.
  - Strict Content Security Policy (CSP) and zero client-side secrets.

- **Product Experience & UX (Phase 11)**:
  - Complete theme engine supporting System default, Light, and Dark modes with semantic design tokens.
  - Interactive timestamp citations (`[MM:SS]`) that dispatch video seek messages to the active YouTube video player.
  - Grounded one-click quick action prompts ("Summarize", "Key Points", "Explain Simply").
  - XSS-safe Markdown rendering with streaming cursor indicators and copy-to-clipboard evidence formatting.
  - Slide-over conversation drawer with client-side title search, in-place title editing, and deletion confirmation dialogs.

- **Machine Learning Evaluation & CI (Phase 12)**:
  - Curated gold benchmark datasets (`evaluation/datasets/`) spanning 10 video categories and 4 duration tiers.
  - Comprehensive metric evaluation engine measuring Recall@K, MRR, Temporal IoU, Grounded Answer Rate, Hallucination Rate, and Citation Validity.
  - 12-category hierarchical error taxonomy and failure diagnoser.
  - 22 deterministic CI regression tests guarding against quality degradation in `apps/backend/tests/evaluation/`.
