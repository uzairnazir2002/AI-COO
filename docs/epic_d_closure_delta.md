# Epic D Closure Delta (Multi-Location Analytics)

## Scope
Epic D is closed for the planned location-native foundation:
- persisted location-aware alerts and filtering,
- CSV import location mapping with profile compatibility,
- cross-location benchmarking API and dashboard surface.

## API Evidence
- Location CRUD module:
  - `GET/POST/PUT/DELETE /api/v1/locations`
  - `backend/app/api/v1/locations.py`
- Location-aware alerts filter:
  - `GET /api/v1/alerts?org_id=...&location_id=...`
  - `backend/app/api/v1/alerts.py`
- Cross-location benchmark:
  - `GET /api/v1/analytics/location-benchmark?org_id=...&from=...&to=...`
  - `backend/app/api/v1/analytics.py`

## Domain/Storage Evidence
- Location dimension:
  - `backend/migrations/versions/0025_locations_dimension.py`
  - `backend/app/domain/models/location.py`
  - `backend/app/domain/repos/location_repo.py`
  - `backend/app/domain/services/location_service.py`
- Persisted alert location scope:
  - `backend/migrations/versions/0026_alerts_location_scope.py`
  - `backend/app/domain/models/alert.py`
  - `backend/app/domain/repos/alerts_repo.py`
  - `backend/app/domain/services/alerts_service.py`
- CSV import location resolution:
  - `backend/app/utils/csv_import.py`
  - `backend/app/domain/services/transaction_service.py`

## Frontend Evidence
- Location management in settings:
  - `frontend/src/app/app/settings/page.tsx`
  - `frontend/src/features/locations/hooks.ts`
- Location scope selector and propagation:
  - `frontend/src/components/shell/app-shell.tsx`
  - `frontend/src/store/appStore.ts`
- Dashboard cross-location panel:
  - `frontend/src/features/dashboard/dashboard-page-client.tsx`
  - `frontend/src/features/dashboard/hooks.ts`
- Transactions/import location mapping UI:
  - `frontend/src/app/app/transactions/page.tsx`

## Test Evidence
- Location endpoints/service:
  - `backend/app/tests/test_locations_endpoint.py`
  - `backend/app/tests/test_location_service.py`
- Alert location behavior:
  - `backend/app/tests/test_alerts_location_filter.py`
  - `backend/app/tests/test_alerts_location_scoping.py`
- Benchmark endpoint:
  - `backend/app/tests/test_analytics_location_benchmark_endpoint.py`
- Import compatibility:
  - `backend/app/tests/test_csv_import.py`
  - `backend/app/tests/test_csv_import_duplicates.py`
  - `backend/app/tests/test_import_profiles_endpoint.py`

## Closure Status
- Epic D status: **COMPLETE**
- Residual risk: comparative benchmark quality still depends on transaction location tagging coverage.
