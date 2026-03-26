# Epic E Closure Delta (Inventory Forecasting)

## Scope Added In This Slice
- Inventory data foundation (schema + domain model):
  - `inventory_items`
  - `inventory_stock_levels`
  - `inventory_stock_events`
  - `inventory_purchase_orders`
  - `inventory_sales_velocity`
- Inventory API foundation:
  - `GET /api/v1/inventory/items`
  - `POST /api/v1/inventory/items`
  - `POST /api/v1/inventory/stock-events`
  - `POST /api/v1/inventory/purchase-orders`
  - `GET /api/v1/inventory/forecast`
- Forecast logic:
  - velocity from historical outbound stock events,
  - inbound open PO quantity considered for coverage,
  - risk level classification and stockout projection.
- Persisted inventory risk alerts:
  - alert engine now creates `INVENTORY_STOCKOUT` alerts from forecast high-risk rows.
  - inventory mutations enqueue `recalc_alerts` job with standard queue metadata/notification trail.
- Frontend inventory UX:
  - new `/app/inventory` page for items, stock events, purchase orders, and forecast risk table.
  - sidebar + command palette navigation wired for inventory.
- E2E coverage:
  - new flow `frontend/e2e/inventory-alerts.spec.ts` validating inventory mutation -> queue signal -> persisted alerts visibility.

## Evidence
- Migration:
  - `backend/migrations/versions/0027_inventory_forecasting_foundation.py`
- Models:
  - `backend/app/domain/models/inventory_item.py`
  - `backend/app/domain/models/inventory_stock_level.py`
  - `backend/app/domain/models/inventory_stock_event.py`
  - `backend/app/domain/models/inventory_purchase_order.py`
  - `backend/app/domain/models/inventory_sales_velocity.py`
- Repo/service:
  - `backend/app/domain/repos/inventory_repo.py`
  - `backend/app/domain/services/inventory_service.py`
  - `backend/app/domain/services/alerts_service.py`
- API/schema wiring:
  - `backend/app/api/v1/inventory.py`
  - `backend/app/api/v1/router.py`
  - `backend/app/domain/schemas/inventory.py`
- Frontend:
  - `frontend/src/app/app/inventory/page.tsx`
  - `frontend/src/features/inventory/hooks.ts`
  - `frontend/src/components/shell/app-shell.tsx`
  - `frontend/src/components/shell/command-palette.tsx`

## Tests
- `backend/app/tests/test_inventory_service.py`
- `backend/app/tests/test_inventory_endpoint.py`
- `backend/app/tests/test_alerts_inventory_stockout.py`
- `backend/app/tests/test_alerts_location_scoping.py`
- `frontend/e2e/inventory-alerts.spec.ts`

## Verification
- Command:
  - `.venv\\Scripts\\python.exe -m pytest backend/app/tests/test_alerts_budget_threshold.py backend/app/tests/test_alerts_inventory_stockout.py backend/app/tests/test_alerts_location_filter.py backend/app/tests/test_alerts_location_scoping.py backend/app/tests/test_inventory_service.py backend/app/tests/test_inventory_endpoint.py`
- Result:
  - `11 passed`
- Command:
  - `npm run build` (frontend)
- Result:
  - success (`Next.js 15.5.12`)
- Command:
  - `E2E_BASE_URL=http://localhost:3001 E2E_API_URL=http://localhost:8000/api/v1 E2E_USE_SEEDED=0 npx playwright test e2e/inventory-alerts.spec.ts`
- Result:
  - `1 passed`
- Command:
  - `k6 run scripts/loadtest/k6-inventory-churn.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN=<bootstrap token> -e ORG_IDS_JSON='[\"<org_id>\"]' -e RATE=2 -e DURATION=12s`
- Result:
  - `http_req_failed=0.00%`, all inventory profile thresholds passed.

## Perf Gate Closure
- Added inventory churn load profile:
  - `scripts/loadtest/k6-inventory-churn.js`
- Added CI perf gate execution and artifact export:
  - `.github/workflows/perf.yml` (`inventory_churn_summary.json`)
- Added performance runbook coverage:
  - `docs/performance.md`

## Status
- Epic E status: **COMPLETE**
- Residual risk: inventory churn thresholds are validated in CI at `RATE=6`; production-scale tuning can increase load envelope as usage grows.
