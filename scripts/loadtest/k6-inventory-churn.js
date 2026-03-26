import http from "k6/http";
import { check, sleep } from "k6";

import { commonHeaders, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);

export const options = {
  scenarios: {
    inventory_churn: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 6),
      timeUnit: "1s",
      duration: __ENV.DURATION || "90s",
      preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 12),
      maxVUs: Number(__ENV.MAX_VUS || 80),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.04"],
    "http_req_duration{endpoint:inventory_create}": ["p(95)<2200"],
    "http_req_duration{endpoint:inventory_stock_event}": ["p(95)<2200"],
    "http_req_duration{endpoint:inventory_forecast}": ["p(95)<2400"],
    "http_req_duration{endpoint:alerts_open}": ["p(95)<1800"],
  },
};

function nowIso() {
  return new Date().toISOString();
}

export default function () {
  const orgId = selectOrg(orgIds);
  const sku = `K6-INV-${__VU}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;

  const createItem = http.post(
    `${baseUrl}/inventory/items`,
    JSON.stringify({
      org_id: orgId,
      sku,
      name: `Load Item ${sku}`,
      unit_cost: "4.25",
      reorder_point: "10.000",
      is_active: true,
    }),
    { headers, tags: { endpoint: "inventory_create" } },
  );
  check(createItem, { "inventory item create 200": (r) => r.status === 200 });

  if (createItem.status !== 200) {
    sleep(Number(__ENV.SLEEP_SECONDS || 0.2));
    return;
  }

  const itemId = createItem.json("id");
  const stockEvent = http.post(
    `${baseUrl}/inventory/stock-events`,
    JSON.stringify({
      org_id: orgId,
      item_id: itemId,
      event_type: "OUTBOUND",
      quantity: "25.000",
      occurred_at: nowIso(),
      notes: "k6 inventory churn outbound",
    }),
    { headers, tags: { endpoint: "inventory_stock_event" } },
  );
  check(stockEvent, { "inventory stock event 200": (r) => r.status === 200 });

  const forecast = http.get(`${baseUrl}/inventory/forecast?org_id=${orgId}&lookback_days=30&horizon_days=30`, {
    headers,
    tags: { endpoint: "inventory_forecast" },
  });
  check(forecast, { "inventory forecast 200": (r) => r.status === 200 });

  const alerts = http.get(`${baseUrl}/alerts?org_id=${orgId}&status=OPEN`, {
    headers,
    tags: { endpoint: "alerts_open" },
  });
  check(alerts, { "alerts open 200": (r) => r.status === 200 });

  sleep(Number(__ENV.SLEEP_SECONDS || 0.35));
}
