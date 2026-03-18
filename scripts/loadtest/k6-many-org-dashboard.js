import http from "k6/http";
import { check, sleep } from "k6";

import { commonHeaders, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const fromDate = requiredEnv("FROM_DATE");
const toDate = requiredEnv("TO_DATE");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);

export const options = {
  scenarios: {
    many_org_dashboard_reads: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 40),
      duration: __ENV.DURATION || "2m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    "http_req_duration{endpoint:summary}": ["p(95)<2200"],
    "http_req_duration{endpoint:cashflow}": ["p(95)<2200"],
    "http_req_duration{endpoint:runway}": ["p(95)<1800"],
    "http_req_duration{endpoint:alerts}": ["p(95)<1800"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);

  const summary = http.get(
    `${baseUrl}/analytics/summary?org_id=${orgId}&from=${fromDate}&to=${toDate}`,
    { headers, tags: { endpoint: "summary" } },
  );
  check(summary, { "summary 200": (r) => r.status === 200 });

  const cashflow = http.get(
    `${baseUrl}/analytics/cashflow?org_id=${orgId}&from=${fromDate}&to=${toDate}&granularity=month`,
    { headers, tags: { endpoint: "cashflow" } },
  );
  check(cashflow, { "cashflow 200": (r) => r.status === 200 });

  const runway = http.get(
    `${baseUrl}/runway?org_id=${orgId}&from=${fromDate}&to=${toDate}&lookback_months=6`,
    { headers, tags: { endpoint: "runway" } },
  );
  check(runway, { "runway 200": (r) => r.status === 200 });

  const alerts = http.get(`${baseUrl}/alerts?org_id=${orgId}&status=OPEN`, { headers, tags: { endpoint: "alerts" } });
  check(alerts, { "alerts 200": (r) => r.status === 200 });

  sleep(Number(__ENV.SLEEP_SECONDS || 1));
}
