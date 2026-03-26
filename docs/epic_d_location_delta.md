# Epic D Location Delta

## Scope completed
- Persisted location-aware alerts:
  - `alerts.location_id` added and indexed.
  - alert generation now runs global + per-active-location contexts.
  - `GET /api/v1/alerts` supports `location_id` filtering.
- CSV import location mapping:
  - CSV mapping now supports optional `location` column.
  - location values resolve by location `name` or `code` to `location_id`.
  - unknown/inactive locations fail import with row-specific validation error.
  - mapping profiles can store/reuse `location` column mapping.
- Cross-location benchmarking:
  - `GET /api/v1/analytics/location-benchmark?org_id=...&from=...&to=...`
  - dashboard panel added for comparative location revenue/expense/net/margin view.

## Key files
- Backend:
  - `backend/migrations/versions/0026_alerts_location_scope.py`
  - `backend/app/domain/models/alert.py`
  - `backend/app/domain/services/alerts_service.py`
  - `backend/app/domain/repos/alerts_repo.py`
  - `backend/app/api/v1/alerts.py`
  - `backend/app/utils/csv_import.py`
  - `backend/app/domain/services/transaction_service.py`
  - `backend/app/domain/repos/transaction_repo.py`
  - `backend/app/domain/repos/analytics_repo.py`
  - `backend/app/domain/services/analytics_service.py`
  - `backend/app/domain/schemas/analytics.py`
  - `backend/app/api/v1/analytics.py`
- Frontend:
  - `frontend/src/app/app/transactions/page.tsx`
  - `frontend/src/features/alerts/hooks.ts`
  - `frontend/src/features/dashboard/hooks.ts`
  - `frontend/src/features/dashboard/dashboard-page-client.tsx`
  - `frontend/src/lib/api/endpoints.ts`
  - `frontend/src/lib/api/schemas.ts`
  - `frontend/src/lib/query/keys.ts`

## Tests added/updated
- `backend/app/tests/test_alerts_location_filter.py`
- `backend/app/tests/test_alerts_location_scoping.py`
- `backend/app/tests/test_csv_import.py`
- `backend/app/tests/test_csv_import_duplicates.py`
- `backend/app/tests/test_import_profiles_endpoint.py`
- `backend/app/tests/test_analytics_location_benchmark_endpoint.py`
