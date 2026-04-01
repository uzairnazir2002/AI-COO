# Frontend Redesign Remaining Checklist (Strict)

This checklist tracks only the remaining gaps against the approved redesign spec.

## Completion Rules (Strict)
1. A checklist item is complete only when all acceptance criteria under it are true.
2. "Behavior preserving" is mandatory for every item: no backend contract/path/payload/header changes.
3. RBAC, org scoping, auth modes, SSE fallback, and alert refresh semantics must remain unchanged.
4. For UI changes, Playwright parity must be green before removing any legacy assertion/selectors.
5. Each completed item must list the exact touched files in the PR description.

## Wave R1 - Shared Contract Gaps (Component Inventory Parity)

- [x] R1.1 Add missing page/frame primitives required by spec.
  - Acceptance criteria:
    1. `PageContainer` exists and is used on all `/app/*` route pages.
    2. `PageActionBar` exists and is used where route header actions are present.
    3. `RightRail` exists and is used by at least Transactions, Alerts, Reports.
  - Target files:
    - `frontend/src/components/layout/page-container.tsx` (new)
    - `frontend/src/components/layout/page-action-bar.tsx` (new)
    - `frontend/src/components/layout/right-rail.tsx` (new)
    - `frontend/src/components/common/section-header.tsx`
    - `frontend/src/app/app/transactions/page.tsx`
    - `frontend/src/app/app/alerts/page.tsx`
    - `frontend/src/features/reports/reports-page-client.tsx`

- [x] R1.2 Add missing form/workflow primitives from spec.
  - Acceptance criteria:
    1. `WizardStepper` is implemented and used by CSV import flow.
    2. `FieldHelpCallout` is implemented and used in at least Settings and Forecast.
    3. `FormSection` is implemented and used in at least 3 settings panels.
  - Target files:
    - `frontend/src/components/safety/wizard-stepper.tsx` (new)
    - `frontend/src/components/safety/field-help-callout.tsx` (new)
    - `frontend/src/components/safety/form-section.tsx` (new)
    - `frontend/src/features/transactions/panels/transactions-import-dialog.tsx`
    - `frontend/src/features/settings/panels/security-panel.tsx`
    - `frontend/src/features/settings/panels/integrations-panel.tsx`
    - `frontend/src/features/forecast/containers/forecast-workspace-container.tsx`

- [x] R1.3 Fill table ecosystem gaps from spec.
  - Acceptance criteria:
    1. `SavedViewSelector` exists and persists views for Transactions filters.
    2. `ColumnVisibilityMenu` exists and controls grid column visibility.
    3. `RowActionMenu` exists and replaces duplicated inline row action buttons.
  - Target files:
    - `frontend/src/components/data-surface/saved-view-selector.tsx` (new)
    - `frontend/src/components/data-surface/column-visibility-menu.tsx` (new)
    - `frontend/src/components/data-surface/row-action-menu.tsx` (new)
    - `frontend/src/features/transactions/containers/transactions-workspace-container.tsx`
    - `frontend/src/app/app/transactions/page.tsx`

## Wave R2 - Dashboard Remaining Gaps

- [x] R2.1 Add KPI/chart drill-through behavior to downstream filters.
  - Acceptance criteria:
    1. Clicking KPI cards updates route/query state or in-page filters.
    2. Clicking chart points applies date/category scoping to relevant panels.
    3. Behavior does not break current dashboard specs.
  - Target files:
    - `frontend/src/features/dashboard/dashboard-page-client.tsx`
    - `frontend/src/features/dashboard/panels/kpi-grid.tsx`
    - `frontend/src/features/dashboard/panels/cashflow-chart-panel.tsx`
    - `frontend/src/features/dashboard/panels/revenue-expense-chart-panel.tsx`

- [x] R2.2 Add explicit metric explainability affordances beyond drawer open.
  - Acceptance criteria:
    1. KPI cards visibly indicate drillability (icon/text cue).
    2. `CalculationDrawer` includes source labels for each input.
  - Target files:
    - `frontend/src/components/kpi/kpi-card.tsx`
    - `frontend/src/components/drawers/calculation-drawer.tsx`
    - `frontend/src/features/dashboard/panels/kpi-grid.tsx`

## Wave R3 - Transactions Premium Workflow Completion

- [x] R3.1 Implement saved views and view recall in Transactions utility row.
  - Acceptance criteria:
    1. User can create, rename, delete saved views for filter state.
    2. Selected saved view is reflected in UI and reload-safe.
    3. Existing filter behavior remains unchanged when no view is selected.
  - Target files:
    - `frontend/src/features/transactions/services/saved-views.ts` (new)
    - `frontend/src/features/transactions/containers/transactions-workspace-container.tsx`
    - `frontend/src/app/app/transactions/page.tsx`

- [x] R3.2 Upgrade CSV import to strict guided stepper contract.
  - Acceptance criteria:
    1. Import UI displays explicit Step 1/2/3/4 navigation state.
    2. Step-specific validation messages are isolated and persistent.
    3. Step transitions do not alter existing backend preview/commit requests.
  - Target files:
    - `frontend/src/features/transactions/panels/transactions-import-dialog.tsx`
    - `frontend/src/features/transactions/services/csv.ts`
    - `frontend/src/components/safety/wizard-stepper.tsx`

- [x] R3.3 Add contextual right-rail detail enrichment.
  - Acceptance criteria:
    1. Selected transaction panel includes related alerts block.
    2. Selected transaction panel includes audit snippet block.
    3. Panel remains selector-compatible for existing tests.
  - Target files:
    - `frontend/src/features/transactions/panels/selected-transaction-panel.tsx`
    - `frontend/src/features/transactions/containers/transactions-workspace-container.tsx`

## Wave R4 - Alerts and Reports Remaining Premium Gaps

- [x] R4.1 Convert Alerts to full tri-pane layout contract.
  - Acceptance criteria:
    1. Feed, detail, and action areas are visibly distinct in one workspace.
    2. Related metrics and related transactions sections render in detail area.
    3. Assignment timeline is human-readable (relative + absolute time).
  - Target files:
    - `frontend/src/features/alerts/containers/alerts-workspace-container.tsx`
    - `frontend/src/features/alerts/panels/alert-detail-panel.tsx`
    - `frontend/src/features/alerts/panels/alert-action-panel.tsx` (new)
    - `frontend/src/features/alerts/panels/alert-feed-panel.tsx` (new)

- [x] R4.2 Add recommended-next-action affordances for alerts.
  - Acceptance criteria:
    1. Alert detail includes at least one context-driven recommended action.
    2. Recommended action triggers existing API-safe mutation paths only.
  - Target files:
    - `frontend/src/features/alerts/panels/alert-detail-panel.tsx`
    - `frontend/src/features/alerts/services/recommendations.ts` (new)

- [x] R4.3 Complete Reports studio experience.
  - Acceptance criteria:
    1. `ScheduleReportCard` exists with clear scheduling UX state.
    2. Report metadata/share area exists in right panel.
    3. Existing reuse behavior remains unchanged and visible.
  - Target files:
    - `frontend/src/components/reports/schedule-report-card.tsx` (new)
    - `frontend/src/features/reports/containers/reports-workspace-container.tsx`
    - `frontend/src/features/reports/reports-page-client.tsx`

## Wave R5 - Remaining Route Depth (Budgets, Forecast, Inventory, Assistant, Onboarding, Orgs)

- [x] R5.1 Budgets: version comparison and planned-vs-actual chart completion.
  - Acceptance criteria:
    1. "Compare versions" UI exists and renders two selected versions.
    2. Planned vs actual trend chart renders for current period.
    3. No change to budget CRUD/version API behavior.
  - Target files:
    - `frontend/src/features/budgets/containers/budgets-workspace-container.tsx`
    - `frontend/src/app/app/budgets/page.tsx`
    - `frontend/src/features/budgets/panels/version-compare-panel.tsx` (new)
    - `frontend/src/features/budgets/panels/planned-vs-actual-chart-panel.tsx` (new)

- [x] R5.2 Forecast: assumptions lab and sensitivity/risk completion.
  - Acceptance criteria:
    1. Horizon selector supports 3/6/12 months.
    2. Assumptions panel includes planned hire/purchase/revenue lift/expense delta controls.
    3. Separate sensitivity and risk cards are present.
  - Target files:
    - `frontend/src/app/app/forecast/page.tsx`
    - `frontend/src/features/forecast/containers/forecast-workspace-container.tsx`
    - `frontend/src/features/forecast/panels/assumptions-panel.tsx` (new)
    - `frontend/src/features/forecast/panels/sensitivity-panel.tsx` (new)
    - `frontend/src/features/forecast/panels/risk-panel.tsx` (new)

- [x] R5.3 Inventory: detail drawer parity with spec.
  - Acceptance criteria:
    1. Selected item/PO drawer exists and opens from list rows.
    2. Drawer surfaces COGS exposure and related alert context.
  - Target files:
    - `frontend/src/features/inventory/containers/inventory-workspace-container.tsx`
    - `frontend/src/features/inventory/panels/inventory-detail-drawer.tsx` (new)

- [x] R5.4 Assistant: suggested prompts and richer grounding rail.
  - Acceptance criteria:
    1. Suggested prompts section exists and is context-aware.
    2. Grounding rail includes cited metrics/surfaces links.
    3. Grounded/fallback indicator remains visible per assistant message.
  - Target files:
    - `frontend/src/features/ai-chat/containers/assistant-workspace-container.tsx`
    - `frontend/src/features/ai-chat/services/suggested-prompts.ts` (new)

- [x] R5.5 Onboarding: persistent guidance contract completion.
  - Acceptance criteria:
    1. Checklist remains persistent until baseline completion.
    2. Milestone cards include explicit next action CTA.
  - Target files:
    - `frontend/src/components/shell/onboarding-progress-rail.tsx`
    - `frontend/src/features/onboarding/containers/onboarding-workspace-container.tsx`
    - `frontend/src/app/app/onboarding/page.tsx`

- [x] R5.6 Orgs: align with page frame contract and admin polish.
  - Acceptance criteria:
    1. Organizations and Create tabs both use standardized status/error/success states.
    2. Create path shows explicit org-scoping explanation.
  - Target files:
    - `frontend/src/features/orgs/containers/orgs-workspace-container.tsx`
    - `frontend/src/app/app/orgs/page.tsx`

## Wave R6 - Global State and Accessibility/Animation Hardening

- [x] R6.1 Enforce full state handling contract per major panel.
  - Acceptance criteria:
    1. Each major route has loading, empty, inline error, retry, success, RBAC-disabled states.
    2. Shared state components are used instead of ad-hoc text blocks.
  - Target files:
    - `frontend/src/components/states/skeleton-panel.tsx`
    - `frontend/src/components/states/inline-error-banner.tsx`
    - `frontend/src/components/states/retry-card.tsx`
    - `frontend/src/components/states/success-state-card.tsx`
    - `frontend/src/app/app/*/page.tsx` (all relevant routes)

- [x] R6.2 Accessibility pass for tabs, drawers, dialogs, and data grids.
  - Acceptance criteria:
    1. Keyboard navigation works for all TabNav usages.
    2. Drawers/dialogs have focus trap and return-focus behavior.
    3. Table controls are reachable and labeled for screen readers.
  - Target files:
    - `frontend/src/components/layout/tab-nav.tsx`
    - `frontend/src/components/drawers/detail-drawer.tsx`
    - `frontend/src/components/ui/dialog.tsx`
    - `frontend/src/features/transactions/containers/transactions-workspace-container.tsx`

- [x] R6.3 Motion discipline pass.
  - Acceptance criteria:
    1. Route transitions, drawers, KPI reveal, and success micro-animations only.
    2. No decorative table/list animation that affects workflow speed.
  - Target files:
    - `frontend/src/components/shell/app-shell.tsx`
    - `frontend/src/features/dashboard/dashboard-page-client.tsx`
    - `frontend/src/components/drawers/detail-drawer.tsx`

## Wave R7 - Tests and Selector Policy Completion

- [x] R7.1 Add parity assertions for newly introduced contracts.
  - Acceptance criteria:
    1. Playwright asserts new components where behavior changed but semantics did not.
    2. Existing critical behavior assertions remain green.
  - Target files:
    - `frontend/e2e/full-flow.spec.ts`
    - `frontend/e2e/ops-flow.spec.ts`
    - `frontend/e2e/polish.spec.ts`
    - `frontend/e2e/inventory-alerts.spec.ts`

- [x] R7.2 Full regression lane sign-off.
  - Acceptance criteria:
    1. `npm run lint` passes.
    2. `npm run build` passes.
    3. `npx playwright test --reporter=line` passes in controlled server mode.
  - Target files:
    - `frontend/playwright.config.ts`
    - `frontend/e2e/fixtures/auth.ts`

## Final Sign-off Checklist

- [x] Backend/API behavior unchanged (manual contract spot-check against `frontend/src/lib/api/endpoints.ts`).
- [x] RBAC behavior unchanged for Owner/Editor/Viewer critical flows.
- [x] Cookie + bearer auth mode compatibility verified.
- [x] SSE live/fallback visibility preserved in notification center.
- [x] Alert refresh metadata still surfaced after write mutations.
- [x] Plaid/Stripe integration paths remain functional.
- [x] All relevant Playwright lanes green after final refactor.
