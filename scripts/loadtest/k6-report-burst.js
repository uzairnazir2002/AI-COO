import http from "k6/http";
import { check, sleep } from "k6";

import { commonHeaders, isoMondayOrToday, readOrgIds, requiredEnv, selectOrg } from "./_shared.js";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const accessToken = requiredEnv("ACCESS_TOKEN");
const orgIds = readOrgIds();
const headers = commonHeaders(accessToken);
const weekStart = isoMondayOrToday();

export const options = {
  scenarios: {
    report_generation_burst: {
      executor: "ramping-vus",
      stages: [
        { duration: "20s", target: Number(__ENV.BURST_TARGET_VUS || 30) },
        { duration: "60s", target: Number(__ENV.BURST_TARGET_VUS || 30) },
        { duration: "20s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.03"],
    "http_req_duration{endpoint:report_generate}": ["p(95)<2000"],
    "http_req_duration{endpoint:jobs_list}": ["p(95)<1800"],
  },
};

export default function () {
  const orgId = selectOrg(orgIds);

  const generate = http.post(`${baseUrl}/reports/generate?org_id=${orgId}&week_start=${weekStart}`, null, {
    headers,
    tags: { endpoint: "report_generate" },
  });
  check(generate, {
    "report generate 200": (r) => r.status === 200,
    "job metadata returned": (r) => {
      if (r.status !== 200) return false;
      try {
        const body = r.json();
        return !!body.job_id && !!body.status;
      } catch {
        return false;
      }
    },
  });

  const jobs = http.get(`${baseUrl}/jobs?org_id=${orgId}&task_name=generate_weekly_report&page=1&page_size=5`, {
    headers,
    tags: { endpoint: "jobs_list" },
  });
  check(jobs, { "jobs list 200": (r) => r.status === 200 });

  sleep(Number(__ENV.SLEEP_SECONDS || 0.5));
}
