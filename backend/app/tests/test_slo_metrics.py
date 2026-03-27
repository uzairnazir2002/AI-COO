from app.core import slo_metrics


def test_runtime_slo_snapshot_calculates_p95_and_error_rate():
    original_samples = list(slo_metrics._samples)
    slo_metrics._samples.clear()
    try:
        for _ in range(8):
            slo_metrics.record_runtime_sample(
                method="GET",
                path="/api/v1/analytics/summary",
                status_code=200,
                latency_ms=100,
            )
        slo_metrics.record_runtime_sample(
            method="GET",
            path="/api/v1/analytics/summary",
            status_code=500,
            latency_ms=3000,
        )
        snapshot = slo_metrics.runtime_slo_snapshot(
            window_seconds=600,
            p95_threshold_ms=500,
            error_rate_threshold_pct=1.0,
            top_n=5,
        )
    finally:
        slo_metrics._samples.clear()
        for sample in original_samples:
            slo_metrics._samples.append(sample)

    assert snapshot["total_requests"] == 9
    assert len(snapshot["endpoints"]) == 1
    endpoint = snapshot["endpoints"][0]
    assert endpoint["endpoint"] == "GET /api/v1/analytics/summary"
    assert endpoint["requests"] == 9
    assert endpoint["p95_ms"] >= 3000
    assert endpoint["error_rate_pct"] > 10
    assert endpoint["breach"] is True
