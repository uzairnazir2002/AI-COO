# Workforce — Phase 0 (Foundation audit + architecture)

**Goal:** Safely implement/complete Workforce as a first-class domain inside AI COO, using existing repo patterns (org scoping, RBAC, hooks, alert/report/job/outbox conventions).

This Phase 0 audit found that **most Workforce backend + frontend scaffolding already exists** (employees, attendance, leave, payroll tracking, announcements). The remaining “program” work is primarily: (a) verifying each phase end-to-end, (b) filling gaps against the required scope (HR admin workflows + intelligence integrations), and (c) polishing responsiveness/state handling where needed.

---

## 1) Backend module plan (where Workforce lives)

Workforce is already implemented as a dedicated API namespace:

- **Routes**: `backend/app/api/v1/workforce/*`
  - Mounted at `/api/v1/workforce` in `backend/app/api/v1/router.py`
- **Domain models**: `backend/app/domain/models/workforce_*.py`
- **Schemas**:
  - Core org structure + employee: `backend/app/domain/schemas/workforce.py`
  - Attendance: `backend/app/domain/schemas/workforce_attendance.py`
  - Leave: `backend/app/domain/schemas/workforce_leave.py`
  - Payroll: `backend/app/domain/schemas/workforce_payroll.py`
  - Announcements: `backend/app/domain/schemas/workforce_announcement.py`
- **Repos/services**:
  - `backend/app/domain/repos/workforce_*_repo.py`
  - `backend/app/domain/services/workforce_*_service.py`

**DB migrations already exist** for Workforce phases 1–5, e.g.:
- `backend/migrations/versions/0029_workforce_phase1_foundation.py`
- `backend/migrations/versions/0030_workforce_attendance_and_shifts.py`
- `backend/migrations/versions/0031_workforce_leave.py`
- `backend/migrations/versions/0032_workforce_payroll.py` (+ follow-ups)
- `backend/migrations/versions/0034..0036_workforce_announcements*.py`

### Phase 6–7 backend (implemented)

- **HR admin**: `backend/app/api/v1/workforce/hr_admin.py` (+ migrations for policies, documents, checklist items, acknowledgements).
- **Workforce intelligence**: `backend/app/api/v1/workforce/intelligence.py` — `GET .../intelligence/dashboard`, `GET .../intelligence/reports/summary`; service `backend/app/domain/services/workforce_intelligence_service.py`; schemas `backend/app/domain/schemas/workforce_intelligence.py`.
- **Org-wide workforce alerts** (Phase 7): `AlertsService.detect_and_create` includes `WORKFORCE_*` detectors when running org-wide recalc (see `backend/app/domain/services/alerts_service.py`).
- **AI / weekly report context**: `metrics["workforce"]` is attached in `backend/app/api/v1/ai.py` (summary + chat with DB), and in `backend/app/domain/services/report_service.py` when generating weekly report AI text so grounding matches the rest of the product.

---

## 2) Frontend route/folder plan

Workforce is already integrated in the Next.js App Router and feature folders:

- **Routes**:
  - `frontend/src/app/app/workforce/page.tsx` (landing)
  - `frontend/src/app/app/workforce/employees/*`
  - `frontend/src/app/app/workforce/attendance/page.tsx`
  - `frontend/src/app/app/workforce/leave/page.tsx`
  - `frontend/src/app/app/workforce/payroll/page.tsx`
  - `frontend/src/app/app/workforce/communications/*`
- **Feature module**:
  - `frontend/src/features/workforce/*` (hooks, containers, panels)
- **Navigation**:
  - Workforce is linked in `frontend/src/components/shell/app-shell.tsx`

### Phase 6–7 frontend (implemented)

- **HR admin hub**: `frontend/src/app/app/workforce/hr/page.tsx` (+ related HR routes under `workforce/hr/`).
- **Intelligence UX** (no separate `/workforce/insights` route): executive **dashboard** panel `frontend/src/features/dashboard/panels/workforce-intelligence-panel.tsx` (loads `GET /workforce/intelligence/dashboard`); **Reports** page block + JSON download for `GET /workforce/intelligence/reports/summary` (`#workforce-summary`). **Workforce landing** links to the dashboard snapshot and describes the reports export.

---

## 3) Entity/data model plan (canonical)

### Already present (Phases 1–5)

**Org structure & employees**
- `WorkforceDepartment`
- `WorkforceTitle`
- `WorkforceEmployee`
  - department/title/manager/location linkage
  - employment type/status
  - salary type and base salary / hourly rate (role-redacted for viewers)

**Attendance**
- `WorkforceShift`
- `WorkforceShiftAssignment`
- `WorkforceAttendanceRecord`
- `WorkforceAttendanceCorrection` (request/review)

**Leave**
- `WorkforceLeaveType`
- `WorkforceLeaveBalance`
- `WorkforceLeaveRequest` (approve/reject; impacts attendance)

**Payroll (tracking, not tax engine)**
- `WorkforcePayrollPeriod`
- `WorkforcePayrollEntry`
- `WorkforcePayrollAdjustment`
- Payslip preview + PDF endpoints

**Communications**
- `WorkforceAnnouncement`
- `WorkforceAnnouncementReceipt` (read/ack)
- `WorkforceAnnouncementTemplate`
- `WorkforceAnnouncementDelivery` (+ outbox integration)

### Phase 6 entity scope (HR admin)

Implemented per migrations and models under `workforce_*` (documents, policies, acknowledgements, checklist items, employee contract/probation fields as applicable). Use phase-6 Playwright + pytest coverage for HR flows.

### Phase 7 intelligence scope (no new event store)

Delivered as **deterministic SQL aggregates** over existing attendance / leave / payroll / employee / announcement tables:

- Dashboard snapshot (`as_of` date) and **range reports summary** (`from` / `to`).
- **Workforce-shaped org alerts** created during standard `detect_and_create` recalc.
- **Assistant / AI summary / weekly report** receive the same `workforce` JSON block for consistent grounding (`AISemanticGroundingValidator` extended for workforce terms and numeric fields).

---

## 4) RBAC / permission plan

Use existing org roles:
- **OWNER**: full access, including destructive actions and “mark paid”
- **EDITOR**: create/update most workforce operational data
- **VIEWER**: read-only; sensitive compensation amounts **redacted**

Current backend patterns already enforce:
- mutation role checks (`OWNER|EDITOR`)
- owner-only where required (e.g., employee delete/deactivate; leave type delete; payroll mark-paid)
- redaction for viewers (employee pay fields, payroll amounts, some exports)

### Manager relationships

Manager is **a data relationship** (`manager_employee_id`) and used for audience targeting; it does **not** create a new RBAC role.
Phase 6/7 can add optional “manager-scoped views” by filtering using manager-team relationships while still requiring org membership.

---

## 5) Phased implementation plan (files + verification strategy)

This program will proceed strictly in order, treating each phase incomplete until verified:

- **Phase 1 (Employees/Departments/Titles)**: verify CRUD + manager assignment + filters + RBAC + responsive.
- **Phase 2 (Attendance)**: verify clock in/out, manual entry, shifts, calendar, correction request+review, lateness/missing checkout.
- **Phase 3 (Leave)**: verify types, balances allocate, requests + decisions, calendar, attendance interaction.
- **Phase 4 (Payroll)**: verify periods, draft generation, adjustments, approve, owner mark-paid, export, payslip preview/pdf.
- **Phase 5 (Communications)**: verify announcements CRUD + publish/schedule/archive, audience targeting, receipts (read/ack), templates, deliveries.
- **Phase 6 (HR Admin)**: implement & verify docs/policies/ack + onboarding/offboarding checklists + contract/probation indicators.
- **Phase 7 (Workforce Intelligence Integration)**: implement dashboard cards + workforce alerts + workforce reports + assistant context.
- **Phase 8 (Responsive/UX/State completion)**: mobile/tablet/desktop checks across all workforce routes.
- **Phase 9 (Final verification)**: completion matrix + evidence + remaining risks.

Verification tools:
- Backend: `pytest` (new workforce tests added where gaps exist)
- Frontend: `npm run build`, targeted Playwright specs for workforce flows
- Runtime: `python scripts/verify_runtime.py` plus workforce-specific runtime checks

### Phase 8 verification (responsive + state)

For a fast “Phase 8 is done” check (requires backend reachable at `http://localhost:8000`):

```powershell
cd "c:\Project\AI COO\ai-coo\frontend"
npm run build

$env:E2E_USE_EXTERNAL_BASE_URL="1"
$env:E2E_BASE_URL="http://localhost:3000"
$env:E2E_API_URL="http://localhost:8000/api/v1"
$env:E2E_AUTH_MODE="bearer"

npm run e2e:workforce
```

If you run cookie auth, use `$env:E2E_AUTH_MODE="cookie"` and ensure `AUTH_COOKIE_MODE=true` on the backend.

### Workforce runtime smoke (Phase 7 intelligence)

To verify Workforce intelligence end-to-end (real auth + real org scoping):

- Script: `scripts/smoke_workforce_intelligence.py`
- Endpoints exercised: `GET /api/v1/workforce/intelligence/dashboard`, `GET /api/v1/workforce/intelligence/reports/summary`

Seeded (recommended; no disposable org/user created):

```powershell
cd "c:\Project\AI COO\ai-coo"
$env:SMOKE_USER_EMAIL="you@example.com"
$env:SMOKE_USER_PASSWORD="YourPassword123!"
$env:SMOKE_ORG_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
python scripts/smoke_workforce_intelligence.py --base-url http://127.0.0.1:8000/api/v1
```

Notes:
- Set `$env:SMOKE_AUTH_MODE="cookie"` if you run the API in cookie auth mode.
- You can pass `--seeded-email/--seeded-password/--seeded-org-id` args instead of env vars.

---

## 6) Prerequisite refactors / infra notes (before Phase 1 verification)

No major prerequisite refactor is required to start Phase 1, because:
- Workforce endpoints are already mounted at `/api/v1/workforce/*`
- Frontend routes already exist under `/app/workforce/*`
- Org scoping uses `get_org_context`
- RBAC checks are present on mutations

Expected follow-up (later phases / polish):
- **Phase 8+**: optional dedicated `/app/workforce/insights` hub if product wants intelligence isolated from finance dashboard.
- **Phase 6**: object storage hardening for sensitive HR documents (reuse MinIO/S3 patterns from announcements attachments).
- Deeper per-user announcement acknowledgement analytics (current Phase 7 dashboard uses a deliberate org-level heuristic).

