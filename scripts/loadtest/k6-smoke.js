import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = __ENV.ACCESS_TOKEN;
const orgId = __ENV.ORG_ID;
const fromDate = __ENV.FROM_DATE;
const toDate = __ENV.TO_DATE;

if (!accessToken || !orgId || !fromDate || !toDate) {
  throw new Error("Missing required env vars: ACCESS_TOKEN, ORG_ID, FROM_DATE, TO_DATE");
}

const headers = {
  Authorization: `Bearer ${accessToken}`,
  "Content-Type": "application/json",
};

export const options = {
  scenarios: {
    api_mix: {
      executor: "constant-vus",
      vus: 8,
      duration: "45s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:summary}": ["p(95)<2000"],
    "http_req_duration{endpoint:cashflow}": ["p(95)<2000"],
    "http_req_duration{endpoint:transactions}": ["p(95)<2000"],
    "http_req_duration{endpoint:ai}": ["p(95)<3000"],
  },
};

export default function () {
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

  const tx = http.get(
    `${baseUrl}/transactions?org_id=${orgId}&page=1&page_size=100&type=EXPENSE&q=seed-load`,
    { headers, tags: { endpoint: "transactions" } },
  );
  check(tx, { "transactions 200": (r) => r.status === 200 });

  const ai = http.post(
    `${baseUrl}/ai/summary`,
    JSON.stringify({ org_id: orgId, from: fromDate, to: toDate }),
    { headers, tags: { endpoint: "ai" } },
  );
  check(ai, { "ai 200": (r) => r.status === 200 });

  sleep(1);
}
