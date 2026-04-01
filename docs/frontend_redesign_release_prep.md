# Frontend Redesign Release Prep

Date: 2026-04-01

## Scope
Post-redesign hardening/release pass completed:
1. Selector cleanup wave with parity assertions added first.
2. Release preparation documentation (touched files + risk notes).
3. Staging verification lanes (cookie+CSRF, bearer/core, SSE fallback, Plaid/Stripe).

## Selector Cleanup
Legacy compatibility selectors removed after parity assertions were added and validated:
- Removed `data-testid="app-sidebar"` and `data-testid="app-main-scroll"` from shell layout.
- Removed alerts tri-pane testids:
  - `alerts-feed-panel`
  - `alerts-detail-panel`
  - `alerts-action-panel`
- Removed transaction detail compatibility testids:
  - `transaction-related-alerts`
  - `transaction-audit-snippet`

Parity assertions added before cleanup:
- `frontend/e2e/full-flow.spec.ts`
  - transaction detail parity (`Related alerts`, `Audit snippet`)
  - alerts tri-pane parity (`Alert feed`, `Action panel`) with empty-board fallback assertion.

## Verification Results
Baseline gates:
- `npm run lint` -> pass
- `npm run build` -> pass

Staging verification lanes:
- `npx playwright test e2e/cookie-csrf.spec.ts e2e/full-flow.spec.ts e2e/ops-flow.spec.ts e2e/sse-fallback.spec.ts e2e/plaid-integration.spec.ts e2e/stripe-integration.spec.ts --reporter=line` -> pass (`9 passed`, `3 skipped`)

Full regression:
- `npx playwright test --reporter=line` -> pass (`20 passed`, `9 skipped`)

## Exact Touched Files (Release Bundle)
From `git status --porcelain`:
- `frontend/e2e/fixtures/auth.ts`
- `frontend/e2e/full-flow.spec.ts`
- `frontend/e2e/inventory-alerts.spec.ts`
- `frontend/e2e/mfa-session.spec.ts`
- `frontend/e2e/ops-flow.spec.ts`
- `frontend/e2e/plaid-integration.spec.ts`
- `frontend/e2e/polish.spec.ts`
- `frontend/e2e/stripe-integration.spec.ts`
- `frontend/playwright.config.ts`
- `frontend/src/app/app/activity/page.tsx`
- `frontend/src/app/app/alerts/page.tsx`
- `frontend/src/app/app/assistant/page.tsx`
- `frontend/src/app/app/budgets/page.tsx`
- `frontend/src/app/app/forecast/page.tsx`
- `frontend/src/app/app/inventory/page.tsx`
- `frontend/src/app/app/onboarding/page.tsx`
- `frontend/src/app/app/orgs/page.tsx`
- `frontend/src/app/app/settings/page.tsx`
- `frontend/src/app/app/transactions/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/components/common/section-header.tsx`
- `frontend/src/components/kpi/kpi-card.tsx`
- `frontend/src/components/shell/app-shell.tsx`
- `frontend/src/components/shell/command-palette.tsx`
- `frontend/src/components/shell/date-range-control.tsx`
- `frontend/src/components/shell/onboarding-progress-rail.tsx`
- `frontend/src/features/dashboard/dashboard-page-client.tsx`
- `frontend/src/features/forecast/hooks.ts`
- `frontend/src/features/reports/reports-page-client.tsx`
- `frontend/src/store/appStore.ts`
- `docs/frontend_redesign_remaining_checklist.md`
- `frontend/src/components/data-surface/*`
- `frontend/src/components/drawers/*`
- `frontend/src/components/layout/*`
- `frontend/src/components/reports/*`
- `frontend/src/components/safety/*`
- `frontend/src/components/shell/profile-menu.tsx`
- `frontend/src/components/shell/quick-create-menu.tsx`
- `frontend/src/components/states/*`
- `frontend/src/features/activity/panels/*`
- `frontend/src/features/ai-chat/containers/*`
- `frontend/src/features/ai-chat/services/*`
- `frontend/src/features/alerts/containers/*`
- `frontend/src/features/alerts/panels/*`
- `frontend/src/features/alerts/services/*`
- `frontend/src/features/budgets/containers/*`
- `frontend/src/features/budgets/panels/*`
- `frontend/src/features/dashboard/panels/*`
- `frontend/src/features/forecast/containers/*`
- `frontend/src/features/forecast/panels/*`
- `frontend/src/features/inventory/containers/*`
- `frontend/src/features/inventory/panels/*`
- `frontend/src/features/onboarding/containers/*`
- `frontend/src/features/orgs/containers/*`
- `frontend/src/features/reports/containers/*`
- `frontend/src/features/settings/panels/*`
- `frontend/src/features/settings/services/*`
- `frontend/src/features/transactions/containers/*`
- `frontend/src/features/transactions/panels/*`
- `frontend/src/features/transactions/services/*`

## Risk Notes
1. E2E runtime cost is high because Playwright `webServer` rebuilds app per run.
   - Mitigation: keep controlled mode for release confidence; optimize later with prebuilt start mode for CI speed.
2. Selector cleanup can break external/private tests not in this repo.
   - Mitigation: parity assertions were added using semantic locators; staged rollout recommended if external suites exist.
3. Large frontend diff across many new files increases merge conflict risk.
   - Mitigation: release as dedicated branch/PR with freeze window and full Playwright lane required before merge.
4. Settings/Activity tab data dependencies can produce transient loading in slower envs.
   - Mitigation: explicit shared loading/retry states now wired; keep retries enabled in CI and staging smoke.
