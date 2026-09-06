"""Latency and streaming performance metrics: TTFT, duration, percentiles (p50, p95, p99) using pure Python stdlib."""

import math

from evaluation.models import ComponentLatencyBreakdown, LatencyPercentiles


def _percentile(sorted_data: list[float], percent: float) -> float:
    """Computes a percentile value from a pre-sorted list of floats using linear interpolation."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]

    k = (len(sorted_data) - 1) * (percent / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def compute_percentiles(measurements: list[float]) -> LatencyPercentiles:
    """Computes p50, p95, p99, and mean from a list of millisecond measurements."""
    if not measurements:
        return LatencyPercentiles(p50_ms=0.0, p95_ms=0.0, p99_ms=0.0, mean_ms=0.0)

    sorted_m = sorted(measurements)
    mean_val = sum(sorted_m) / len(sorted_m)

    return LatencyPercentiles(
        p50_ms=round(_percentile(sorted_m, 50.0), 2),
        p95_ms=round(_percentile(sorted_m, 95.0), 2),
        p99_ms=round(_percentile(sorted_m, 99.0), 2),
        mean_ms=round(mean_val, 2),
    )


def summarize_latency_breakdown(
    retrieval_times: list[float],
    llm_ttft_times: list[float],
    llm_total_times: list[float],
    citation_resolution_times: list[float],
    end_to_end_times: list[float],
) -> ComponentLatencyBreakdown:
    """Produces the structured ComponentLatencyBreakdown object."""
    return ComponentLatencyBreakdown(
        retrieval_ms=compute_percentiles(retrieval_times),
        llm_ttft_ms=compute_percentiles(llm_ttft_times),
        llm_total_ms=compute_percentiles(llm_total_times),
        citation_resolution_ms=compute_percentiles(citation_resolution_times),
        end_to_end_ms=compute_percentiles(end_to_end_times),
    )
