from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metric_value(summary: dict[str, Any], metric_key: str, stat_key: str, default: float = 0.0) -> float:
    metric = summary.get("metrics", {}).get(metric_key, {})
    values = metric.get("values", {})
    value = values.get(stat_key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_metrics(summary: dict[str, Any], endpoints: dict[str, int]) -> dict[str, float]:
    out: dict[str, float] = {}
    for endpoint in endpoints:
        key = f"http_req_duration{{endpoint:{endpoint}}}"
        out[f"{endpoint}_p95_ms"] = _metric_value(summary, key, "p(95)")
    out["failure_rate"] = _metric_value(summary, "http_req_failed", "rate")
    out["dropped_iterations"] = _metric_value(summary, "dropped_iterations", "count")
    return out


def _is_breach(metrics: dict[str, float], failure_rate_max: float, p95_thresholds: dict[str, int]) -> bool:
    if metrics["failure_rate"] > failure_rate_max:
        return True
    for endpoint, limit_ms in p95_thresholds.items():
        if metrics.get(f"{endpoint}_p95_ms", 0.0) > float(limit_ms):
            return True
    return False


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Perf Gate Summary",
        "",
        "## Guardrails",
        f"- Read `RATE`: {payload['guardrails']['read_hotpaths']['rate']}",
        f"- Runtime observability `RATE`: {payload['guardrails']['runtime_observability']['rate']}",
        "",
        "## Read Hotpaths",
        "",
        "| Pass | Summary p95 (ms) | Cashflow p95 (ms) | Transactions p95 (ms) | Alerts p95 (ms) | Failure rate | Dropped iterations | Breach |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for name in ("read_pass_1", "read_pass_2"):
        row = payload[name]
        lines.append(
            f"| {name} | {row['summary_p95_ms']:.2f} | {row['cashflow_p95_ms']:.2f} | "
            f"{row['transactions_p95_ms']:.2f} | {row['alerts_p95_ms']:.2f} | "
            f"{row['failure_rate']:.4f} | {int(row['dropped_iterations'])} | {row['breach']} |"
        )

    obs = payload["runtime_observability"]
    lines.extend(
        [
            "",
            "## Runtime Observability",
            "",
            "| Runtime metrics p95 (ms) | Failure rate | Dropped iterations | Breach |",
            "|---:|---:|---:|---:|",
            f"| {obs['runtime_metrics_p95_ms']:.2f} | {obs['failure_rate']:.4f} | {int(obs['dropped_iterations'])} | {obs['breach']} |",
            "",
            "## Gate Result",
            f"- `{payload['gate_result']}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate split perf gate summaries.")
    parser.add_argument("--slo", required=True, type=Path)
    parser.add_argument("--read-pass-1", required=True, type=Path)
    parser.add_argument("--read-pass-2", required=True, type=Path)
    parser.add_argument("--runtime-observability", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args()

    guardrails = _load_json(args.slo)
    read_slo = guardrails["read_hotpaths"]
    runtime_slo = guardrails["runtime_observability"]

    read1 = _read_metrics(_load_json(args.read_pass_1), read_slo["p95_ms"])
    read2 = _read_metrics(_load_json(args.read_pass_2), read_slo["p95_ms"])
    obs = _read_metrics(_load_json(args.runtime_observability), runtime_slo["p95_ms"])

    read1_breach = _is_breach(read1, float(read_slo["failure_rate_max"]), read_slo["p95_ms"])
    read2_breach = _is_breach(read2, float(read_slo["failure_rate_max"]), read_slo["p95_ms"])
    obs_breach = _is_breach(obs, float(runtime_slo["failure_rate_max"]), runtime_slo["p95_ms"])

    gate_fail = (read1_breach and read2_breach) or obs_breach
    payload = {
        "guardrails": guardrails,
        "read_pass_1": {**read1, "breach": read1_breach},
        "read_pass_2": {**read2, "breach": read2_breach},
        "runtime_observability": {**obs, "breach": obs_breach},
        "gate_result": "FAIL" if gate_fail else "PASS",
    }

    args.out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_markdown(args.out_md, payload)

    if gate_fail:
        print("Perf gate failed: read regressed in two consecutive passes or runtime observability breached SLO.")
        return 1
    print("Perf gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
