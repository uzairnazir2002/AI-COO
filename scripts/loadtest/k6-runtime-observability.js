import http from "k6/http";
import { check, sleep } from "k6";
import { Gauge } from "k6/metrics";

import { commonHeaders, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);

const queueDepthGauge = new Gauge("runtime_queue_depth");
const dbActiveGauge = new Gauge("runtime_db_active_connections");

export const options = {
  scenarios: {
    runtime_observability: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 2),
      timeUnit: "1s",
      duration: __ENV.DURATION || "90s",
      preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 5),
      maxVUs: Number(__ENV.MAX_VUS || 20),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    "http_req_duration{endpoint:runtime_metrics}": ["p(95)<1200"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);
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

  sleep(Number(__ENV.SLEEP_SECONDS || 0.5));
}
