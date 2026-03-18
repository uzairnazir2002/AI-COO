import http from "k6/http";
import { check, sleep } from "k6";
import { Gauge } from "k6/metrics";

import { commonHeaders, isoMondayOrToday, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);
const weekStart = isoMondayOrToday();

const queueDepthGauge = new Gauge("runtime_queue_depth");
const dbActiveGauge = new Gauge("runtime_db_active_connections");

const importMapping = JSON.stringify({
  date: "date",
  amount: "amount",
  type: "type",
  category: "category",
  vendor: "vendor",
  notes: "notes",
});

const csvPayload = [
  "date,amount,type,category,vendor,notes",
  "2026-02-01,125.00,EXPENSE,Software,ACME Cloud,write-heavy row 1",
  "2026-02-02,2800.00,REVENUE,Sales,,write-heavy row 2",
].join("\n");

export const options = {
  scenarios: {
    write_heavy: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 10),
      timeUnit: "1s",
      duration: __ENV.DURATION || "90s",
      preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 20),
      maxVUs: Number(__ENV.MAX_VUS || 120),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.04"],
    "http_req_duration{endpoint:recompute}": ["p(95)<2200"],
    "http_req_duration{endpoint:report_generate}": ["p(95)<2200"],
    "http_req_duration{endpoint:csv_preview}": ["p(95)<2600"],
    "http_req_duration{endpoint:runtime_metrics}": ["p(95)<1400"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);

  const recompute = http.post(`${baseUrl}/analytics/recompute?org_id=${orgId}`, null, {
    headers,
    tags: { endpoint: "recompute" },
  });
  check(recompute, { "recompute 200": (r) => r.status === 200 });

  const report = http.post(`${baseUrl}/reports/generate?org_id=${orgId}&week_start=${weekStart}`, null, {
    headers,
    tags: { endpoint: "report_generate" },
  });
  check(report, { "report generate 200": (r) => r.status === 200 });

  const csvPreview = http.post(
    `${baseUrl}/transactions/import/csv`,
    {
      org_id: orgId,
      commit: "false",
      mapping: importMapping,
      file: http.file(csvPayload, `write-heavy-import-${__VU}.csv`, "text/csv"),
    },
    { headers: { Authorization: headers.Authorization }, tags: { endpoint: "csv_preview" } },
  );
  check(csvPreview, { "csv preview 200": (r) => r.status === 200 });

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

  sleep(Number(__ENV.SLEEP_SECONDS || 0.4));
}
