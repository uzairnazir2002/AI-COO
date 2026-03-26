import crypto from "node:crypto";

import { expect, test } from "./fixtures/auth";

const liveStripe = process.env.E2E_STRIPE_LIVE === "1";
const stripeSecretKey = process.env.E2E_STRIPE_SECRET_KEY || "";
const stripeWebhookSecret = process.env.E2E_STRIPE_WEBHOOK_SECRET || "";
const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

async function stripeRequest(path: string, body?: URLSearchParams) {
  const response = await fetch(`https://api.stripe.com${path}`, {
    method: body ? "POST" : "GET",
    headers: {
      Authorization: `Bearer ${stripeSecretKey}`,
      ...(body ? { "Content-Type": "application/x-www-form-urlencoded" } : {}),
    },
    body: body ? body.toString() : undefined,
  });
  if (!response.ok) {
    throw new Error(`Stripe API ${path} failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

function signStripePayload(payload: string, secret: string): string {
  const timestamp = Math.floor(Date.now() / 1000);
  const signedPayload = `${timestamp}.${payload}`;
  const signature = crypto.createHmac("sha256", secret).update(signedPayload, "utf8").digest("hex");
  return `t=${timestamp},v1=${signature}`;
}

async function createLiveCharge(orgId: string) {
  const params = new URLSearchParams();
  params.set("amount", "1575");
  params.set("currency", "usd");
  params.set("source", "tok_visa");
  params.set("description", "AI COO E2E Stripe webhook charge");
  params.set("metadata[org_id]", orgId);
  return stripeRequest("/v1/charges", params);
}

async function waitForChargeSucceededEvent(chargeId: string) {
  const timeoutAt = Date.now() + 45_000;
  while (Date.now() < timeoutAt) {
    const events = await stripeRequest("/v1/events?type=charge.succeeded&limit=20");
    const found = (events?.data || []).find((item: any) => item?.data?.object?.id === chargeId);
    if (found) return found;
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error(`Timed out waiting for Stripe charge.succeeded event for charge ${chargeId}`);
}

test.describe("Stripe integration flow", () => {
  test.skip(!liveStripe || !stripeSecretKey || !stripeWebhookSecret, "Set E2E_STRIPE_LIVE=1 + E2E_STRIPE_SECRET_KEY + E2E_STRIPE_WEBHOOK_SECRET");

  test("connects Stripe and processes live signed webhook into reconciliation", async ({ page, authSession, authenticatedPage }) => {
    void authenticatedPage;

    await page.goto("/app/settings");
    await expect(page.getByRole("heading", { name: "Payment integrations (Stripe)" })).toBeVisible();

    const label = `E2E Stripe ${authSession.namespace}`;
    await page.getByPlaceholder("Account label (optional)").fill(label);
    await page.getByTestId("stripe-connect-submit").click();
    await expect(page.getByText("Stripe connection saved")).toBeVisible();

    const charge = await createLiveCharge(authSession.orgId);
    expect(charge?.id).toBeTruthy();
    const event = await waitForChargeSucceededEvent(charge.id as string);
    const payload = JSON.stringify(event);
    const signature = signStripePayload(payload, stripeWebhookSecret);

    const webhook = await page.request.post(`${apiBase}/integrations/payments/stripe/webhook`, {
      data: payload,
      headers: {
        "Content-Type": "application/json",
        "Stripe-Signature": signature,
      },
    });
    expect(webhook.ok(), await webhook.text()).toBeTruthy();
    const webhookJson = await webhook.json();
    expect(webhookJson.ok).toBeTruthy();
    expect(["PROCESSED", "DUPLICATE"]).toContain(webhookJson.status);

    const dateTo = new Date().toISOString().slice(0, 10);
    const dateFrom = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const reconciliation = await page.request.get(
      `${apiBase}/integrations/payments/reconciliation?org_id=${authSession.orgId}&provider=STRIPE&date_from=${dateFrom}&date_to=${dateTo}`,
      {
        headers: authSession.accessToken ? { Authorization: `Bearer ${authSession.accessToken}` } : undefined,
      },
    );
    expect(reconciliation.ok(), await reconciliation.text()).toBeTruthy();
    const reconJson = await reconciliation.json();
    expect(Number(reconJson.processor.entry_count)).toBeGreaterThan(0);

    await page.getByTestId("stripe-reconciliation-card").getByRole("button", { name: "Refresh" }).click();
    await expect(page.getByTestId("stripe-reconciliation-card")).toContainText("Processor Net");
  });
});
