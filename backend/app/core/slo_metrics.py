from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True)
class RequestSample:
    ts: float
    method: str
    path: str
    status_code: int
    latency_ms: float


_MAX_SAMPLES = 50_000
_samples: deque[RequestSample] = deque(maxlen=_MAX_SAMPLES)
_lock = Lock()


def record_runtime_sample(*, method: str, path: str, status_code: int, latency_ms: float) -> None:
    sample = RequestSample(
        ts=time(),
        method=method.upper(),
        path=path,
        status_code=int(status_code),
        latency_ms=max(0.0, float(latency_ms)),
    )
    with _lock:
        _samples.append(sample)


def runtime_slo_snapshot(
    *,
    window_seconds: int = 300,
    p95_threshold_ms: float = 2000.0,
    error_rate_threshold_pct: float = 1.0,
    top_n: int = 20,
) -> dict:
    cutoff = time() - max(1, int(window_seconds))
    with _lock:
        in_window = [s for s in _samples if s.ts >= cutoff]

    grouped: dict[str, list[RequestSample]] = defaultdict(list)
    for sample in in_window:
        grouped[f"{sample.method} {sample.path}"].append(sample)

    endpoint_rows = []
    for endpoint, rows in grouped.items():
        count = len(rows)
        if count == 0:
            continue
        latencies = sorted(s.latency_ms for s in rows)
        p95_index = max(0, min(count - 1, math.ceil(count * 0.95) - 1))
        p95_ms = latencies[p95_index]
        errors = sum(1 for s in rows if s.status_code >= 500)
        error_rate_pct = (errors / count) * 100.0
        breach = p95_ms > p95_threshold_ms or error_rate_pct > error_rate_threshold_pct
        endpoint_rows.append(
            {
                "endpoint": endpoint,
                "requests": count,
                "p95_ms": round(p95_ms, 2),
                "error_rate_pct": round(error_rate_pct, 2),
                "breach": breach,
            }
        )

    endpoint_rows.sort(key=lambda row: (row["breach"], row["requests"], row["p95_ms"]), reverse=True)
    trimmed = endpoint_rows[: max(1, int(top_n))]
    return {
        "window_seconds": int(window_seconds),
        "p95_threshold_ms": float(p95_threshold_ms),
        "error_rate_threshold_pct": float(error_rate_threshold_pct),
        "total_requests": len(in_window),
        "endpoints": trimmed,
    }
