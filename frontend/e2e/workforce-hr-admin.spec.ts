import { e2eAuthenticatedGet, e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://127.0.0.1:8000/api/v1";
const csrfCookieName = process.env.E2E_CSRF_COOKIE_NAME || "ai_coo_csrf_token";
const csrfHeaderName = process.env.E2E_CSRF_HEADER_NAME || "X-CSRF-Token";

async function csrfHeaderIfPresent(page: any) {
  const origin = new URL(apiBase).origin;
  const cookies = await page.context().cookies([origin]);
  const token = cookies.find((c: any) => c.name === csrfCookieName)?.value;
  return token ? { [csrfHeaderName]: token } : {};
}

test.describe("Workforce Phase 6: HR admin workflows", () => {
  test.setTimeout(180_000);

  test("policies + acknowledgements + checklists + documents upload", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;

    const orgRole = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(orgRole === "VIEWER", "HR admin mutations require editor or owner.");

    const suffix = `${Date.now()}`;

    const empRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/employees`, {
      org_id: authSession.orgId,
      first_name: "Phase6",
      last_name: `Employee-${suffix}`,
      employment_status: "ACTIVE",
      salary_type: "SALARIED",
      base_salary: "5000.00",
    }, authSession);
    expect(empRes.ok(), await empRes.text()).toBeTruthy();
    const emp = (await empRes.json()) as { id: string };

    const policyRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/hr/policies`, {
      org_id: authSession.orgId,
      code: `SAFETY_${suffix}`.slice(0, 64),
      title: "Safety policy",
      body: "Wear protective equipment.",
      publish_now: false,
      requires_ack: true,
    }, authSession);
    expect(policyRes.ok(), await policyRes.text()).toBeTruthy();
    const policy = (await policyRes.json()) as { id: string; published_at: string | null };

    const pubRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/hr/policies/${policy.id}/publish`, { org_id: authSession.orgId }, authSession);
    expect(pubRes.ok(), await pubRes.text()).toBeTruthy();
    const published = (await pubRes.json()) as { published_at: string | null };
    expect(published.published_at).toBeTruthy();

    const ackRes = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/policies/${policy.id}/ack`,
      { org_id: authSession.orgId, employee_id: emp.id },
      authSession,
    );
    expect(ackRes.ok(), await ackRes.text()).toBeTruthy();

    const acksRes = await e2eAuthenticatedGet(page, `${apiBase}/workforce/hr/policies/${policy.id}/acks?org_id=${authSession.orgId}`, authSession);
    expect(acksRes.ok(), await acksRes.text()).toBeTruthy();
    const acks = (await acksRes.json()) as unknown[];
    expect(acks.length).toBeGreaterThan(0);

    const itemRes = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist`,
      { org_id: authSession.orgId, employee_id: emp.id, kind: "ONBOARDING", title: "Collect ID document", details: "Gov ID" },
      authSession,
    );
    expect(itemRes.ok(), await itemRes.text()).toBeTruthy();
    const item = (await itemRes.json()) as { id: string; is_done: boolean };
    expect(item.is_done).toBe(false);

    const doneRes = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist/${item.id}/done`,
      { org_id: authSession.orgId, is_done: true },
      authSession,
    );
    expect(doneRes.ok(), await doneRes.text()).toBeTruthy();

    // Document upload (bearer or cookie+csrf)
    const headers =
      authSession.authMode === "bearer"
        ? { Authorization: `Bearer ${authSession.accessToken}`, "X-Org-Id": authSession.orgId }
        : await csrfHeaderIfPresent(page);
    if (authSession.authMode !== "bearer") {
      headers["X-Org-Id"] = authSession.orgId;
    }

    const docRes = await page.request.post(
      `${apiBase}/workforce/hr/documents/upload?org_id=${authSession.orgId}&employee_id=${emp.id}`,
      {
        multipart: {
          file: {
            name: "note.txt",
            mimeType: "text/plain",
            buffer: Buffer.from("hello", "utf-8"),
          },
        },
        headers,
      },
    );
    expect(docRes.ok(), await docRes.text()).toBeTruthy();

    const docsRes = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/hr/documents?org_id=${authSession.orgId}&employee_id=${emp.id}`,
      authSession,
    );
    expect(docsRes.ok(), await docsRes.text()).toBeTruthy();
    const docs = (await docsRes.json()) as unknown[];
    expect(docs.length).toBeGreaterThan(0);
  });
});

