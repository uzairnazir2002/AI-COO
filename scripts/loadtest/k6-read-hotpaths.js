import http from "k6/http";
import { check, sleep } from "k6";
import { Gauge } from "k6/metrics";

import { commonHeaders, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const fromDate = requiredEnv("FROM_DATE");
const toDate = requiredEnv("TO_DATE");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);
const runtimeMetricsEnabled = String(__ENV.RUNTIME_METRICS_ENABLED || "false").toLowerCase() !== "false";
const runtimeMetricsEveryN = Math.max(1, Number(__ENV.RUNTIME_METRICS_EVERY_N || 1));

const queueDepthGauge = new Gauge("runtime_queue_depth");
const dbActiveGauge = new Gauge("runtime_db_active_connections");

export const options = {
  scenarios: {
    read_hotpaths: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 13),
      timeUnit: "1s",
      duration: __ENV.DURATION || "90s",
      preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 30),
      maxVUs: Number(__ENV.MAX_VUS || 120),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    "http_req_duration{endpoint:summary}": ["p(95)<2200"],
    "http_req_duration{endpoint:cashflow}": ["p(95)<2200"],
    "http_req_duration{endpoint:transactions}": ["p(95)<2200"],
    "http_req_duration{endpoint:alerts}": ["p(95)<2000"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);

  const summary = http.get(`${baseUrl}/analytics/summary?org_id=${orgId}&from=${fromDate}&to=${toDate}`, {
    headers,
    tags: { endpoint: "summary" },
  });
  check(summary, { "summary 200": (r) => r.status === 200 });

  const cashflow = http.get(`${baseUrl}/analytics/cashflow?org_id=${orgId}&from=${fromDate}&to=${toDate}&granularity=month`, {
    headers,
    tags: { endpoint: "cashflow" },
  });
  check(cashflow, { "cashflow 200": (r) => r.status === 200 });

  const tx = http.get(
    `${baseUrl}/transactions?org_id=${orgId}&from=${fromDate}&to=${toDate}&page=1&page_size=50&q=seed-load`,
    { headers, tags: { endpoint: "transactions" } },
  );
  check(tx, { "transactions 200": (r) => r.status === 200 });

  const alerts = http.get(`${baseUrl}/alerts?org_id=${orgId}&status=OPEN`, {
    headers,
    tags: { endpoint: "alerts" },
  });
  check(alerts, { "alerts 200": (r) => r.status === 200 });

  const shouldSampleRuntimeMetrics = runtimeMetricsEnabled && (__ITER % runtimeMetricsEveryN === 0);
  if (shouldSampleRuntimeMetrics) {
    const runtime = http.get(`${baseUrl}/admin/runtime-metrics?org_id=${orgId}`, {
      headers,
      tags: { endpoint: "runtime_metrics" },
    });
    check(runtime, { "runtime metrics 200": (r) => r.status === 200 });
    if (runtime.status === 200) {
      const payload = runtime.json();
      queueDepthGauge.add(Number(payload.queue_depth_active || 0));
      dbActiveGauge.add(Number(payload.db_active_connections || 0));
    }
  }

  sleep(Number(__ENV.SLEEP_SECONDS || 0.3));
}
