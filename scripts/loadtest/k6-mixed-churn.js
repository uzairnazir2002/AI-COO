import http from "k6/http";
import { check, sleep } from "k6";

import { commonHeaders, isoMondayOrToday, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const fromDate = requiredEnv("FROM_DATE");
const toDate = requiredEnv("TO_DATE");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);
const weekStart = isoMondayOrToday();

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
  "2026-02-01,150.00,EXPENSE,Software,ACME Cloud,churn import row 1",
  "2026-02-02,4500.00,REVENUE,Sales,,churn import row 2",
].join("\n");

export const options = {
  scenarios: {
    mixed_churn: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 15),
      timeUnit: "1s",
      duration: __ENV.DURATION || "90s",
      preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 25),
      maxVUs: Number(__ENV.MAX_VUS || 80),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.04"],
    "http_req_duration{endpoint:transactions}": ["p(95)<2200"],
    "http_req_duration{endpoint:alerts}": ["p(95)<2000"],
    "http_req_duration{endpoint:recompute}": ["p(95)<2200"],
    "http_req_duration{endpoint:report_generate}": ["p(95)<2200"],
    "http_req_duration{endpoint:csv_preview}": ["p(95)<2600"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);

  const tx = http.get(
    `${baseUrl}/transactions?org_id=${orgId}&from=${fromDate}&to=${toDate}&page=1&page_size=50&q=seed-load`,
    { headers, tags: { endpoint: "transactions" } },
  );
  check(tx, { "transactions 200": (r) => r.status === 200 });

  const alerts = http.get(`${baseUrl}/alerts?org_id=${orgId}&status=OPEN`, { headers, tags: { endpoint: "alerts" } });
  check(alerts, { "alerts 200": (r) => r.status === 200 });

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
      file: http.file(csvPayload, `mini-import-${__VU}.csv`, "text/csv"),
    },
    { headers: { Authorization: headers.Authorization }, tags: { endpoint: "csv_preview" } },
  );
  check(csvPreview, { "csv preview 200": (r) => r.status === 200 });

  sleep(Number(__ENV.SLEEP_SECONDS || 0.5));
}
