from fastapi import APIRouter

from app.api.v1.workforce import (
    announcements,
    attendance,
    corrections,
    departments,
    employees,
    hr_admin,
    intelligence,
    leave,
    payroll,
    shifts,
    titles,
)

router = APIRouter()
router.include_router(employees.router, prefix="/employees", tags=["workforce"])
router.include_router(departments.router, prefix="/departments", tags=["workforce"])
router.include_router(titles.router, prefix="/titles", tags=["workforce"])
router.include_router(shifts.router, prefix="/shifts", tags=["workforce"])
router.include_router(attendance.router, prefix="/attendance", tags=["workforce"])
router.include_router(corrections.router, prefix="/corrections", tags=["workforce"])
router.include_router(leave.router, prefix="/leave", tags=["workforce"])
router.include_router(payroll.router, prefix="/payroll", tags=["workforce"])
router.include_router(announcements.router, prefix="/announcements", tags=["workforce"])
router.include_router(hr_admin.router, prefix="/hr", tags=["workforce"])
router.include_router(intelligence.router, prefix="/intelligence", tags=["workforce"])

