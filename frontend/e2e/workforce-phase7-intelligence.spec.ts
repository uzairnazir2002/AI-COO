import { e2eAuthenticatedGet, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://127.0.0.1:8000/api/v1";

test.describe("Workforce Phase 7: intelligence APIs", () => {
  test.setTimeout(120_000);

  test("dashboard + reports summary return JSON for current org", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;
    const orgId = authSession.orgId;
    const today = new Date().toISOString().slice(0, 10);
    const from = new Date();
    from.setUTCDate(from.getUTCDate() - 30);
    const fromStr = from.toISOString().slice(0, 10);

    const dash = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/intelligence/dashboard?org_id=${orgId}&as_of=${today}`,
      authSession,
    );
    expect(dash.ok(), await dash.text()).toBeTruthy();
    const dashBody = (await dash.json()) as { org_id: string; as_of: string; top_risks: string[] };
    expect(dashBody.org_id).toBe(orgId);
    expect(dashBody.as_of).toBe(today);
    expect(Array.isArray(dashBody.top_risks)).toBeTruthy();

    const rep = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/intelligence/reports/summary?org_id=${orgId}&from=${fromStr}&to=${today}`,
      authSession,
    );
    expect(rep.ok(), await rep.text()).toBeTruthy();
    const repBody = (await rep.json()) as { org_id: string; summary_lines: string[]; attendance: { total_records: number } };
    expect(repBody.org_id).toBe(orgId);
    expect(repBody.summary_lines.length).toBeGreaterThan(0);
    expect(typeof repBody.attendance.total_records).toBe("number");
  });
});
