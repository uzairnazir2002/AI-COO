import { expect, test } from "./fixtures/auth";

test.describe("workforce activity failure/retry UI", () => {
  test("outbox failed event renders and retry action posts successfully", async ({ page, authenticatedPage }) => {
    await authenticatedPage;

    const eventId = "11111111-1111-4111-8111-111111111111";
    let retryCalls = 0;

    await page.route("**/api/v1/admin/outbox**", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: eventId,
                org_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                event_type: "email.send",
                payload: { workforce_announcement_delivery_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" },
                status: "FAILED",
                attempts: 2,
                max_attempts: 5,
                available_at: "2026-05-20T10:00:00Z",
                sent_at: null,
                next_attempt_at: null,
                last_error: "SMTP timeout",
                correlation_id: null,
                dedupe_key: null,
                created_at: "2026-05-20T10:00:00Z",
                updated_at: "2026-05-20T10:10:00Z",
              },
            ],
            total: 1,
            page: 1,
            page_size: 8,
            counts_by_status: { FAILED: 1 },
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.route("**/api/v1/admin/system-status**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          scheduler: [],
          system_jobs: [],
          system_job_total: 0,
          org_outbox_counts: { FAILED: 1 },
          failed_webhooks: 0,
          outbox_pending: 0,
          outbox_retrying: 1,
          outbox_failed: 1,
          total_jobs_active: 0,
          schedules_paused: 0,
        }),
      });
    });

    await page.route(`**/api/v1/admin/outbox/${eventId}/retry**`, async (route) => {
      retryCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, id: eventId, status: "PENDING" }),
      });
    });

    await page.goto("/app/admin-console?tab=outbox");
    await expect(page.getByRole("heading", { name: "Admin Console" })).toBeVisible();
    await expect(page.getByText("Outbox monitor")).toBeVisible();
    await expect(page.getByText("SMTP timeout")).toBeVisible();

    await page.getByRole("button", { name: "Retry delivery" }).click();
    await expect.poll(() => retryCalls).toBe(1);
    await expect(page.getByText(/Outbox event re-queued/i).first()).toBeVisible();
  });
});
