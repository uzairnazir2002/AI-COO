import { e2eAuthenticatedGet, e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test.describe("workforce onboarding/offboarding journeys", () => {
  test("create and complete onboarding/offboarding checklist flows", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;
    const orgRole = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(orgRole === "VIEWER", "Checklist mutations require editor/owner.");

    const suffix = `${Date.now()}`;
    const empRes = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/employees`,
      {
        first_name: "Journey",
        last_name: `Employee-${suffix}`,
        employment_status: "ACTIVE",
        salary_type: "SALARIED",
        base_salary: "4200.00",
      },
      authSession,
    );
    expect(empRes.ok(), await empRes.text()).toBeTruthy();
    const emp = (await empRes.json()) as { id: string };

    const onboarding = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist`,
      { employee_id: emp.id, kind: "ONBOARDING", title: "Issue laptop", details: "Device setup" },
      authSession,
    );
    expect(onboarding.ok(), await onboarding.text()).toBeTruthy();
    const onboardingItem = (await onboarding.json()) as { id: string; is_done: boolean };
    expect(onboardingItem.is_done).toBe(false);

    const offboarding = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist`,
      { employee_id: emp.id, kind: "OFFBOARDING", title: "Recover assets", details: "Badge, laptop" },
      authSession,
    );
    expect(offboarding.ok(), await offboarding.text()).toBeTruthy();
    const offboardingItem = (await offboarding.json()) as { id: string; is_done: boolean };
    expect(offboardingItem.is_done).toBe(false);

    const doneOnboarding = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist/${onboardingItem.id}/done`,
      { is_done: true },
      authSession,
    );
    expect(doneOnboarding.ok(), await doneOnboarding.text()).toBeTruthy();

    const doneOffboarding = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/hr/checklist/${offboardingItem.id}/done`,
      { is_done: true },
      authSession,
    );
    expect(doneOffboarding.ok(), await doneOffboarding.text()).toBeTruthy();

    const listOnboarding = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/hr/checklist?employee_id=${emp.id}&kind=ONBOARDING&include_done=true`,
      authSession,
    );
    expect(listOnboarding.ok(), await listOnboarding.text()).toBeTruthy();
    const onboardingRows = (await listOnboarding.json()) as Array<{ id: string; is_done: boolean }>;
    expect(onboardingRows.some((x) => x.id === onboardingItem.id && x.is_done)).toBeTruthy();

    const listOffboarding = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/hr/checklist?employee_id=${emp.id}&kind=OFFBOARDING&include_done=true`,
      authSession,
    );
    expect(listOffboarding.ok(), await listOffboarding.text()).toBeTruthy();
    const offboardingRows = (await listOffboarding.json()) as Array<{ id: string; is_done: boolean }>;
    expect(offboardingRows.some((x) => x.id === offboardingItem.id && x.is_done)).toBeTruthy();
  });
});

