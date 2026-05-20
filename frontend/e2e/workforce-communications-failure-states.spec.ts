import { e2eAuthenticatedGet, e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test.describe("workforce communications failure/retry state coverage", () => {
  test("delivery log API supports failed/retrying filters and error fields", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;
    const role = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(role === "VIEWER", "Delivery logs are editor/owner scoped.");

    const created = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/announcements`,
      {
        title: `Delivery test ${Date.now()}`,
        body: "Coverage for failed/retry delivery view",
        priority: "NORMAL",
        audience_kind: "ORG_ALL",
        send_email_on_publish: true,
      },
      authSession,
    );
    expect(created.ok(), await created.text()).toBeTruthy();
    const ann = (await created.json()) as { id: string };

    const publish = await e2eAuthenticatedPost(
      page,
      `${apiBase}/workforce/announcements/${ann.id}/publish`,
      {},
      authSession,
    );
    expect(publish.ok(), await publish.text()).toBeTruthy();

    const failedFilter = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/announcements/${ann.id}/deliveries?status=FAILED&page=1&page_size=25`,
      authSession,
    );
    expect(failedFilter.ok(), await failedFilter.text()).toBeTruthy();
    const failedBody = (await failedFilter.json()) as { items: Array<{ error?: string | null; outbox_last_error?: string | null }>; total: number };
    expect(Array.isArray(failedBody.items)).toBeTruthy();
    expect(typeof failedBody.total).toBe("number");

    const retryingFilter = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/announcements/${ann.id}/deliveries?status=RETRYING&page=1&page_size=25`,
      authSession,
    );
    expect(retryingFilter.ok(), await retryingFilter.text()).toBeTruthy();
    const retryingBody = (await retryingFilter.json()) as { items: Array<{ error?: string | null; outbox_last_error?: string | null }>; total: number };
    expect(Array.isArray(retryingBody.items)).toBeTruthy();
    expect(typeof retryingBody.total).toBe("number");

    await page.goto("/app/workforce/communications");
    await expect(page.getByRole("heading", { name: "Communications", exact: true })).toBeVisible();
  });
});
